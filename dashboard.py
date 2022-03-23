"""
Main class to start the program. Will kick off Flask based web application
for the web interfaceand start the timer for the host checks. Must run as root.
To run use:

sudo python3 dashboard.py

For a list of arguments use:

sudo python3 dashboard.py -h
"""


import configargparse
import logging
import os
import redis
import signal
import sys
import threading
import time
import modules.utils as utils
from modules.monitor import HostMonitor
from modules.commands import async_command
from flask import Flask, flash, render_template, jsonify, redirect

db = redis.Redis('localhost', decode_responses=True)


# function to handle when the is killed and exit gracefully
def signal_handler(signum, frame):
    logging.debug('Exiting Program')
    sys.exit(0)


def webapp_thread(port_number, debugMode=False, logHandlers=[]):
    app = Flask(import_name="dr-dashboard", static_folder=os.path.join(utils.DIR_PATH, 'web', 'static'),
                template_folder=os.path.join(utils.DIR_PATH, 'web', 'templates'))

    # generate random number for session secret key
    app.secret_key = os.urandom(24)

    # setup broker URLs
    app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
    app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

    # add handlers for this app
    for h in logHandlers:
        app.logger.addHandler(h)

    # set log level
    logLevel = 'INFO' if not debugMode else 'DEBUG'
    app.logger.setLevel(getattr(logging, logLevel))

    # turn of web server logging if not in debug mode
    if(not debugMode):
        werkzeug = logging.getLogger('werkzeug')
        werkzeug.disabled = True

    def _get_host(id):
        result = None

        # get the host status from the db
        host = utils.read_db(db, f"{utils.HOST_STATUS}.{id}")

        if(len(host) > 0):
            result = host

        return result

    @app.route('/', methods=["GET"])
    def index():
        return render_template("index.html")

    @app.route('/status/<id>')
    def host_status(id):

        result = _get_host(id)

        if(result is not None):
            return render_template("host_status.html", host=result)
        else:
            flash('Host page not found', 'warning')
            return redirect('/')

    @app.route('/api/status', methods=['GET'])
    def status():
        # get a list of hosts
        hosts = utils.read_db(db, utils.VALID_HOSTS)

        # get the status of all the hosts
        status = [utils.read_db(db, f"{utils.HOST_STATUS}.{h}") for h in hosts]

        return jsonify(status)

    @app.route('/api/overall_status', methods=['GET'])
    def overall_status():
        overall_status = 0  # 0 is the target, means all is good
        error_count = 0

        # pull in all the hosts and get their overall status
        hosts = utils.read_db(db, utils.VALID_HOSTS)
        for name in hosts:
            host = utils.read_db(db, f"{utils.HOST_STATUS}.{name}")

            # catch for rare cases where host status hasn't been calculated yet
            if('overall_status' in host):
                # set the higher of the two values
                overall_status = host['overall_status'] if host['overall_status'] > overall_status else overall_status

                if(host['overall_status'] > 0):
                    error_count = error_count + 1

        return jsonify({"total_hosts": len(hosts), "hosts_with_errors": error_count, "overall_status": overall_status,
                        "overall_status_description": utils.SERVICE_STATUSES[overall_status]})

    @app.route('/api/command/status', methods=['GET'])
    def command_status():
        result = {"task": "", "progress": 100, "status": "No Command Running"}

        # check if there is a running command
        task = utils.read_db(db, utils.COMMAND_TASK_ID)

        if('id' in task):
            # get the task info from the celery broker
            result['task'] = task['id']
            task_status = async_command.AsyncResult(task['id'])

            if(task_status.state == "RUNNING"):
                result['status'] = task_status.info.get('message', '')
                result['progress'] = task_status.info.get('progress', 0)

        return jsonify(result)

    # run the web app
    app.run(debug=debugMode, host='0.0.0.0', port=port_number, use_reloader=False)


# parse the CLI args
parser = configargparse.ArgumentParser(description='Simple Monitoring')
parser.add_argument('-c', '--config', is_config_file=True,
                    help='Path to custom config file')
parser.add_argument('-f', '--file', default='conf/monitor.yaml',
                    help="Path to the config file for the host data, %(default)s by default")
parser.add_argument('-p', '--port', default=5000,
                    help="Port number to run the web server on, %(default)d by default")
parser.add_argument('-D', '--debug', action='store_true',
                    help='If the program should run in debug mode')

args = parser.parse_args()

# add hooks for interrupt signal
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# setup the logger
logLevel = 'INFO' if not args.debug else 'DEBUG'
logHandlers = [logging.StreamHandler(sys.stdout)]
logging.basicConfig(datefmt='%m/%d %H:%M',
                    format="%(levelname)s %(asctime)s: %(message)s",
                    level=getattr(logging, logLevel),
                    handlers=logHandlers)

# set host list (blank)
utils.write_db(db, utils.HOST_STATUS, [])

# start the web app
logging.info('Starting DR Dashboard Web Service')
webAppThread = threading.Thread(name='Web App', target=webapp_thread, args=(args.port, True, logHandlers))
webAppThread.setDaemon(True)
webAppThread.start()

logging.info('Starting monitoring check daemon')
monitor = HostMonitor(args.file)

# save a list of all valid host names
utils.write_db(db, utils.VALID_HOSTS, monitor.get_hosts())

while 1:
    logging.debug("Running host check")
    status = monitor.check_hosts()

    for host in status:
        utils.write_db(db, f"{utils.HOST_STATUS}.{host['id']}", host)

    time.sleep(60)
