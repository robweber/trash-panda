"""
Main class to start the program. Will kick off Flask based web application
for the web interfaceand start the timer for the host checks. Must run as root.
To run use:

sudo python3 trash-panda.py

For a list of arguments use:

sudo python3 trash-panda.py -h
"""


import asyncio
import configargparse
import contextlib
import datetime
import logging
import signal
import sys
import threading
import time
import os
import os.path
import modules.utils as utils
import uvicorn
from modules.monitor import HostMonitor
from modules.history import HostHistory
from modules.notifications import NotificationGroup
from modules.http.dashboard import flask_app
from modules.http.api import api_app
from starlette.applications import Starlette
from starlette.middleware.wsgi import WSGIMiddleware
from starlette.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from starlette.routing import Mount, Route
from typing import Generator


class Server(uvicorn.Server):
    @contextlib.contextmanager
    def run_in_thread(self) -> Generator:
        thread = threading.Thread(target=self.run)
        thread.start()
        try:
            while not self.started:
                time.sleep(0.001)
            yield
        finally:
            self.should_exit = True
            thread.join()


# function to handle when the is killed and exit gracefully
def signal_handler(signum, frame):
    logging.debug('Exiting Program')
    sys.exit(0)


async def homepage_redirect(request):
    return RedirectResponse(url="/dashboard/", status_code=307)  # 307 Temp Redirect


async def check_notifications(notify, old_host, new_host):
    """check if any service statuses have changed and send notifications
    this method will be called asynchronously through asynio
    """
    # make sure old host has values
    if(len(old_host) > 0):
        # check if the host is up at all
        if(new_host['alive'] != old_host['alive']):
            notify.notify_host(new_host, new_host['alive'])
        else:
            # if service list isn't the same just skip checking for now
            if(len(new_host['services']) == len(old_host['services'])):
                for i in range(0, len(new_host['services'])):
                    # # check the service statuses - make sure it's confirmed before notifying
                    if((new_host['services'][i]['return_code'] != old_host['services'][i]['return_code'] and
                        new_host['services'][i]['state'] == utils.CONFIRMED_STATE) or
                       (old_host['services'][i]['state'] == utils.UNCONFIRMED_STATE and
                       new_host['services'][i]['state'] == utils.CONFIRMED_STATE)):
                        # something has changed in this service's status
                        notify.notify_service(new_host, new_host['services'][i])

# parse the CLI args
parser = configargparse.ArgumentParser(description='Trash Panda')
parser.add_argument('-c', '--config', is_config_file=True,
                    help='Path to custom config file')
parser.add_argument('-f', '--file', default='conf/monitor.yaml',
                    help="Path to the config file for the host data, %(default)s by default")
parser.add_argument('-p', '--port', default=5000, type=int,
                    help="Port number to run the web server on, %(default)d by default")
parser.add_argument('-d', '--database', default="127.0.0.1",
                    help="IP or hostname of Redis database, %(default)s by default")
parser.add_argument('-D', '--debug', action='store_true',
                    help='If the program should run in debug mode')

args = parser.parse_args()

# add hooks for interrupt signal
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# setup the logger
logLevel = 'INFO' if not args.debug else 'DEBUG'
logHandlers = [logging.StreamHandler(sys.stdout)]
logging.basicConfig(datefmt='%m/%d %H:%M:%S',
                    format="%(levelname)s %(asctime)s: %(message)s",
                    level=getattr(logging, logLevel),
                    handlers=logHandlers)
logging.getLogger('asyncio').setLevel(logging.WARNING)  # only show warning or above from this module

# connect to redis DB
history = HostHistory(args.database)

# load the config file
yaml_check = utils.load_config_file(args.file)

if(yaml_check['valid']):
    yaml_file = yaml_check['yaml']
else:
    logging.error("Error reading configuration file")
    logging.error(yaml_check['errors'])
    sys.exit(2)

# create the notifier, if needed
notify = None
if('notifications' in yaml_file['config']):
    notify = NotificationGroup(yaml_file['config']['notifications']['primary'],
                               yaml_file['config']['notifications']['types'],
                               yaml_file['secrets'])

logging.info('Starting monitoring check daemon')
monitor = HostMonitor(history, yaml_file)

# start the web app
logging.info('Starting Trash Panda Web Service')
web_app = flask_app(args.file, yaml_file, history, notify is not None, args.debug, logHandlers)
api = api_app(args.file, yaml_file, history)
starlette_app = Starlette(
    debug=args.debug,
    routes=[
        Route('/', homepage_redirect),
        Mount('/static', StaticFiles(directory=os.path.join(utils.DIR_PATH, 'web', 'static'))),
        Mount('/dashboard', app=WSGIMiddleware(web_app)),
        Mount('/api', app=api)
    ]
)

# load uvicorn server, start in new thread
web_config = uvicorn.Config(app=starlette_app, host="0.0.0.0", port=args.port, log_level=logLevel.lower(), log_config=None)
web_server = Server(config=web_config)

with web_server.run_in_thread():
    while 1:
        logging.debug("Running host check")
        status = monitor.check_hosts()

        for host in status:
            # send notifications, if there are any
            if(notify is not None):
                if(not host['silenced']):
                    asyncio.run(check_notifications(notify, history.get_host(host['id']), host))
                else:
                    logging.info(f"{ host['name'] } is in silent mode, skipping notifications")

            # save the updated host
            history.save_host(host['id'], host)

        logging.debug("Host check complete")
        # record the last time this loop ran
        history.save_last_check()
        time.sleep(60 - datetime.datetime.now().second)  # sleep until the top of the next minute
