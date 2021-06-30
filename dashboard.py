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
from flask import Flask, render_template, jsonify, request

db = redis.Redis('localhost', decode_responses=True)

# function to handle when the is killed and exit gracefully
def signal_handler(signum, frame):
    logging.debug('Exiting Program')
    sys.exit(0)


def webapp_thread(port_number, debugMode=False, logHandlers=[]):
    app = Flask(import_name="dr-dashboard", static_folder=os.path.join(utils.DIR_PATH, 'web', 'static'),
                template_folder=os.path.join(utils.DIR_PATH, 'web', 'templates'))

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

    @app.route('/', methods=["GET"])
    def index():
        return render_template("index.html")

    @app.route('/commands', methods=["GET"])
    def commands():
        return render_template("commands.html")

    @app.route('/status/<id>')
    def host_status(id):

        # get the host status from the db
        hosts = utils.read_db(db, utils.HOST_STATUS)

        # find the one we're looking for
        result = None
        for aHost in hosts:
            if('id' in aHost and aHost['id'] == id):
                result = aHost

        return render_template("host_status.html", host=result)

    @app.route('/api/status', methods=['GET'])
    def status():
        # get the status of all the hosts
        status = utils.read_db(db, utils.HOST_STATUS)

        return jsonify(status)


    # run the web app
    app.run(debug=debugMode, host='0.0.0.0', port=port_number, use_reloader=False)


# parse the CLI args
parser = configargparse.ArgumentParser(description='DR Dashboard Settings')
parser.add_argument('-c', '--config', is_config_file=True,
                    help='Path to custom config file')
parser.add_argument('-f', '--file', default='conf/hosts.json',
                    help="Path to the config file for the host data, %(default)s by default")
parser.add_argument('-p', '--port', default=5000,
                    help="Port number to run the web server on, %(default)d by default")
parser.add_argument('-i', '--interval', default=3,
                    help="The monitoring system check interval, %(default)d by default")
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
webAppThread = threading.Thread(name='Web App', target=webapp_thread, args=(5000, True, logHandlers))
webAppThread.setDaemon(True)
webAppThread.start()

logging.info('Starting monitoring check daemon')
monitor = HostMonitor(args.file)

while 1:
    logging.debug("Running host check")
    status = monitor.check_hosts()
    utils.write_db(db, utils.HOST_STATUS, status)

    time.sleep(60 * args.interval)
