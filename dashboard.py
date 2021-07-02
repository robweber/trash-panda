"""
Main class to start the program. Will kick off Flask based web application
for the web interface and start the timer for the host checks. Must run as root.
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
from modules.monitor import create_device, HostMonitor
from modules.commands import async_command
from celery.result import AsyncResult
from flask import Flask, flash, render_template, jsonify, request, redirect

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
        hosts = utils.read_db(db, utils.HOST_STATUS)

        # find the one we're looking for
        result = list(filter(lambda h: 'id' in h and h['id'] == id, hosts))

        if(len(result) == 1):
            return result[0]
        else:
            return None

    @app.route('/', methods=["GET"])
    def index():
        return render_template("index.html")

    @app.route('/commands', methods=["GET"])
    def commands():
        result = []  # list of host commands

        # get a list of the hosts from the db
        hosts = utils.read_db(db, utils.HOST_STATUS)

        return render_template("commands.html", hosts=hosts)

    @app.route('/status/<id>')
    def host_status(id):

        result = _get_host(id)

        if(result is not None):
            return render_template("host_status.html", host=result)
        else:
            flash('Host page not found', 'warning')
            return redirect('/')

    @app.route('/run_command/<host>/<command>', methods=['GET'])
    def run_host_command(host, command):
        # get the host information from the DB
        host_obj = _get_host(host)

        if(host_obj is not None):
            # run the celery command, send the device class
            task = async_command.delay(host_obj, command)

            # save the task id
            utils.write_db(db, utils.COMMAND_TASK_ID, {"id": task.id})

            flash(f"Command started on host {host_obj['name']}", 'success')
        else:
            flash(f"Command failed. {host} is not a valid host id", 'critical')

        return redirect('/commands')

    @app.route('/api/status', methods=['GET'])
    def status():
        # get the status of all the hosts
        status = utils.read_db(db, utils.HOST_STATUS)

        return jsonify(status)

    @app.route('/api/command/status', methods=['GET'])
    def command_status():
        result = {"task":"", "progress": 100, "status": "No Command Running"}

        # check if there is a running command
        task = utils.read_db(db, utils.COMMAND_TASK_ID)

        if('id' in task):
            # get the task info from the celery broker
            result['task'] = task['id']
            task_status = async_command.AsyncResult(task['id'])

            if(task_status.state == "RUNNING"):
                result['status'] =  task_status.info.get('message', '')
                result['progress'] = task_status.info.get('progress', 0)

        return jsonify(result)


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
