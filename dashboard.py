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
import datetime
import logging
import signal
import sys
import threading
import time
import os
import os.path
import modules.utils as utils
from natsort import natsorted
from modules.monitor import HostMonitor
from modules.history import HostHistory
from modules.notifications import NotificationGroup
from flask import Flask, flash, render_template, jsonify, redirect, request, Response
from slugify import slugify

history = HostHistory()


# function to handle when the is killed and exit gracefully
def signal_handler(signum, frame):
    logging.debug('Exiting Program')
    sys.exit(0)


def webapp_thread(port_number, config_file, config_yaml, notifier_configured, debugMode=False, logHandlers=[]):
    app = Flask(import_name="trash-panda", static_folder=os.path.join(utils.DIR_PATH, 'web', 'static'),
                template_folder=os.path.join(utils.DIR_PATH, 'web', 'templates'))
    # add use of slugify for templates
    app.jinja_env.globals.update(slugify=slugify)

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
        return render_template("index.html", message=config_yaml['config']['web']['landing_page_text'])

    @app.route('/status/host/<id>')
    def host_status(id):
        result = _get_host(id)

        if(result is not None):
            # set if a notifier is configured to toggle silent mode controls
            doc_file = os.path.join(config_yaml['config']['docs_dir'], f"{id}.md")
            return render_template("host_status.html", host=result, page_title='Host Status', has_notifier=notifier_configured,
                                   docs=utils.load_documentation(doc_file), doc_file=doc_file)
        else:
            flash('Host page not found', 'warning')
            return redirect('/')

    @app.route('/status/tag/<tag_id>')
    def tags(tag_id):
        tag = history.get_tag(tag_id)

        services = sorted(tag['services'], key=lambda o: o['host']['name'])
        return render_template("tags.html", services=services, tag_id=tag_id, page_title=f"{tag['name']}")

    @app.route('/editor', methods=['GET'])
    def editor():

        # file path can be passed in with ?path=/path
        file_path = config_file
        if(request.args.get('path') is not None):
            file_path = request.args.get('path')

        return render_template("editor.html", config_file=file_path, editor_config=config_yaml['config']['web']['editor'],
                               page_title='Config Editor')

    @app.route('/docs/<file>', methods=['GET'])
    def load_doc(file):
        # return doc information, if any exists
        return render_template('docs.html', page_title=file.replace('-', ' ').title(), file=file,
                               docs=utils.load_documentation(os.path.join(config_yaml['config']['docs_dir'], f"{file}.md")))

    @app.route('/guide', methods=['GET'])
    def guide():
        # load the README as an internal documentation guide
        return render_template('docs.html', page_title='Guide', file='README',
                               docs=utils.load_documentation(os.path.join(utils.DIR_PATH, "README.md")))

    """ Start of API """
    @app.route('/api/health', methods=['GET'])
    def health():
        """calculate the monitoring system health by making sure the main program
        loop is running properly"""
        last_check = history.get_last_check()
        status = {"text": "Online", "return_code": 0,
                  'last_check_time': last_check.strftime(utils.TIME_FORMAT)}

        # check if the main program loop is running
        now = datetime.datetime.now()
        if(now > last_check + datetime.timedelta(minutes=2)):
            # program is offline if it hasn't run in 2 minutes (grace time for checks)
            status['text'] = 'Offline'
            status['return_code'] = 2  # Critical status

        return jsonify(status)


    @app.route('/api/list/tags', methods=['GET'])
    def get_tags():
        tags = history.list_tags()

        return jsonify(tags)

    @app.route('/api/status/all', methods=['GET'])
    def status():
        # get a list of hosts
        hosts = history.get_hosts()

        return jsonify(sorted(hosts, key=lambda o: o['name']))

    @app.route('/api/status/summary', methods=['GET'])
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

        return jsonify({"total_hosts": len(hosts), "hosts_with_errors": error_count, "services_with_errors": len(services),
                        "overall_status": overall_status, "overall_status_description": utils.SERVICE_STATUSES[overall_status],
                        "services": services})

    @app.route('/api/status/tag/<tag_id>', methods=['GET'])
    def get_tag(tag_id):
        tag = history.get_tag(tag_id)

        # convert services to an array
        tag['services'] = sorted(tag['services'], key=lambda o: o['host']['name'])

        return jsonify(tag)

    @app.route('/api/command/check_now/<id>', methods=['POST'])
    def check_host_now(id):
        result = monitor.check_now(id)

        if(result['success']):
            # update the next check time in the DB as well
            aHost = history.get_host(id)
            aHost['next_check'] = result['next_check']
            history.save_host(id, aHost)

        return jsonify(result)

    @app.route('/api/command/silence_host/<id>/<minutes>', methods=['POST'])
    def silence_host(id, minutes):
        until = datetime.datetime.now() + datetime.timedelta(minutes=int(minutes))
        result = monitor.silence_host(id, until)

        if(result['success']):
            # update the host in the history DB as well
            aHost = history.get_host(id)
            aHost['silenced'] = result['is_silenced']
            history.save_host(id, aHost)

        return jsonify(result)

    @app.route('/api/editor/browse_files/', methods=['GET'], defaults={'browse_path': utils.DIR_PATH})
    @app.route('/api/editor/browse_files/<path:browse_path>', methods=['GET'])
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

    @app.route('/api/editor/load_file', methods=['POST'])
    def load_file():
        file_path = request.form['file_path']

        file_contents = ''
        if(file_path.endswith(utils.ALLOWED_EDITOR_TYPES) and os.path.isfile(file_path)):
            with open(file_path) as f:
                file_contents = f.readlines()

        return Response(file_contents, mimetype='text/plain')

    @app.route('/api/editor/save_file', methods=["POST"])
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

    """ Start of custom processors """
    @app.context_processor
    def nav_links():
        def create_links():
            # return any custom nav components
            return config_yaml['config']['web']['top_nav']['links']
        return dict(create_nav_links=create_links)

    @app.context_processor
    def nav_style():
        def get_style():
            style = config_yaml['config']['web']['top_nav']['style']['type']
            # map bootstrap names to color names
            colors = {"black": "dark", "blue": "primary", "gray": "secondary", "green": "success",
                      "light_blue": "info", "red": "danger", "yellow": "warning"}

            if(style == 'button'):
                return colors[config_yaml['config']['web']['top_nav']['style']['color']]
            else:
                return 'link'

        return dict(get_nav_style=get_style)

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
logging.basicConfig(datefmt='%m/%d %H:%M:%S',
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
if('notifications' in yaml_file['config']):
    notify = NotificationGroup(yaml_file['config']['notifications']['primary'],
                               yaml_file['config']['notifications']['types'])

logging.info('Starting monitoring check daemon')
monitor = HostMonitor(yaml_file)

# start the web app
logging.info('Starting Trash Panda Web Service')
webAppThread = threading.Thread(name='Web App', target=webapp_thread,
                                args=(args.port, args.file, yaml_file, notify is not None, True, logHandlers))
webAppThread.setDaemon(True)
webAppThread.start()

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
    time.sleep(60-datetime.datetime.now().second)  # sleep until the top of the next minute
