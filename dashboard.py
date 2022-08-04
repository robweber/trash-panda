"""
Main class to start the program. Will kick off Flask based web application
for the web interfaceand start the timer for the host checks. Must run as root.
To run use:

sudo python3 dashboard.py

For a list of arguments use:

sudo python3 dashboard.py -h
"""


import asyncio
import configargparse
import logging
import signal
import sys
import threading
import time
import os
import os.path
import modules.utils as utils
import modules.notifications as notifier
from natsort import natsorted
from modules.monitor import HostMonitor
from modules.history import HostHistory
from flask import Flask, flash, render_template, jsonify, redirect, request, Response

history = HostHistory()


# function to handle when the is killed and exit gracefully
def signal_handler(signum, frame):
    logging.debug('Exiting Program')
    sys.exit(0)


def webapp_thread(port_number, config_file, debugMode=False, logHandlers=[]):
    app = Flask(import_name="trash-panda", static_folder=os.path.join(utils.DIR_PATH, 'web', 'static'),
                template_folder=os.path.join(utils.DIR_PATH, 'web', 'templates'))

    # generate random number for session secret key
    app.secret_key = os.urandom(24)

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
        host = history.get_host(id)

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
            return render_template("host_status.html", host=result, page_title='Host Status')
        else:
            flash('Host page not found', 'warning')
            return redirect('/')

    @app.route('/api/status', methods=['GET'])
    def status():
        # get a list of hosts
        hosts = history.list_hosts()

        # get the status of all the hosts
        status = [history.get_host(h) for h in hosts]

        return jsonify(status)

    @app.route('/api/overall_status', methods=['GET'])
    def overall_status():
        overall_status = 0  # 0 is the target, means all is good
        error_count = 0

        # pull in all the hosts and get their overall status
        hosts = history.list_hosts()
        services = []
        for name in hosts:
            host = history.get_host(name)

            # catch for rare cases where host status hasn't been calculated yet
            if('overall_status' in host):
                # set the higher of the two values
                overall_status = host['overall_status'] if host['overall_status'] > overall_status else overall_status

                if(host['overall_status'] > 0):
                    error_count = error_count + 1

                    # find services in error
                    for s in host['services']:
                        if(s['return_code'] > 0):
                            # add host name to dict
                            s['host'] = host['name']
                            services.append(s)

        return jsonify({"total_hosts": len(hosts), "hosts_with_errors": error_count, "overall_status": overall_status,
                        "overall_status_description": utils.SERVICE_STATUSES[overall_status], "services": services})

    @app.route('/editor', methods=['GET'])
    def editor():
        return render_template("editor.html", config_file=config_file, page_title='Config Editor')

    @app.route('/api/browse_files/', methods=['GET'], defaults={'browse_path': utils.DIR_PATH})
    @app.route('/api/browse_files/<path:browse_path>', methods=['GET'])
    def list_directory(browse_path):
        if(not browse_path.startswith('/')):
            browse_path = f"/{browse_path}"

        # if path is a file, get directory
        if(os.path.isfile(browse_path)):
            browse_path = os.path.dirname(browse_path)

        # get a list of all the directories
        dirs = sorted([name for name in os.listdir(browse_path) if os.path.isdir(os.path.join(browse_path, name))])

        # get a list of all the files, filter on valid yaml
        files = natsorted(filter(lambda f: f.endswith(utils.ALLOWED_EDITOR_TYPES), os.listdir(browse_path)))

        return jsonify({'success': True, 'dirs': dirs, 'files': files, 'path': browse_path})

    @app.route('/api/load_file', methods=['POST'])
    def load_file():
        file_path = request.form['file_path']

        file_contents = ''
        if(file_path.endswith(utils.ALLOWED_EDITOR_TYPES) and os.path.isfile(file_path)):
            with open(file_path) as f:
                file_contents = f.readlines()

        return Response(file_contents, mimetype='text/plain')

    @app.route('/api/save_file', methods=["POST"])
    def save_file():
        file_path = request.form['file_path']

        with open(file_path, 'w') as f:
            f.write(request.form['file_contents'])

        return jsonify({'success': True, 'message': f"Saved {file_path}"})

    @app.route('/api/check_config', methods=['GET'])
    def check_config():
        result = {'success': True, 'message': 'Config is valid'}

        # check the config and see if it validates
        yaml_check = utils.load_config_file(config_file)

        if(not yaml_check['valid']):
            result['success'] = False
            result['message'] = 'Configuration file is not valid'
            result['errors'] = yaml_check['errors']

        return jsonify(result)

    # run the web app
    app.run(debug=debugMode, host='0.0.0.0', port=port_number, use_reloader=False)


async def check_notifications(notify, old_host, new_host):
    """check if any service statuses have changed and send notifications
    this method will be called asynchronously through asynio
    """
    # make sure old host has values
    if(len(old_host) > 0):
        # check if the host is up at all
        if(new_host['alive'] != old_host['alive']):
            notify.notify_host(new_host['name'], new_host['alive'])
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
                        notify.notify_service(new_host['name'], new_host['services'][i])

# parse the CLI args
parser = configargparse.ArgumentParser(description='Trash Panda')
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
logging.getLogger('asyncio').setLevel(logging.WARNING)  # only show warning or above from this module

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
if('notifier' in yaml_file['config']):
    notify = notifier.create_notifier(yaml_file['config']['notifier'])

# start the web app
logging.info('Starting Trash Panda Web Service')
webAppThread = threading.Thread(name='Web App', target=webapp_thread, args=(args.port, args.file, True, logHandlers))
webAppThread.setDaemon(True)
webAppThread.start()

logging.info('Starting monitoring check daemon')
monitor = HostMonitor(yaml_file)

while 1:
    logging.debug("Running host check")
    status = monitor.check_hosts()

    for host in status:
        # send notifications, if there are any
        if(notify is not None):
            asyncio.run(check_notifications(notify, history.get_host(host['id']), host))

        # save the updated host
        history.save_host(host['id'], host)

    time.sleep(60)
