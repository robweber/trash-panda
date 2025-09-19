import datetime
import logging
import os
import os.path
from .. import utils as utils
from flask import Flask, flash, render_template, jsonify, redirect, request, Response
from slugify import slugify

def webapp_thread(config_file, config_yaml, history, notifier_configured, debugMode=False, logHandlers=[]):
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

    # re-map the tag colors
    for tag in config_yaml['tags'].keys():
        config_yaml['tags'][tag]['color'] = utils.COLOR_MAPPING[config_yaml['tags'][tag]['color']]

    # turn of web server logging if not in debug mode
    if(not debugMode):
        werkzeug = logging.getLogger('werkzeug')
        werkzeug.disabled = True

    @app.route('/', methods=["GET"])
    def index():
        return render_template("index.html", message=config_yaml['config']['web']['landing_page_text'])

    @app.route('/status/host/<id>')
    def host_status(id):
        result = history.get_host(id)

        if(result is not None):
            # set if a notifier is configured to toggle silent mode controls
            doc_file = os.path.join(config_yaml['config']['docs_dir'], f"{id}.md")
            return render_template("host_status.html", host=result, page_title='Host Status', has_notifier=notifier_configured,
                                   docs=utils.load_documentation(doc_file), doc_file=doc_file, tags=config_yaml['tags'])
        else:
            flash('Host page not found', 'warning')
            return redirect('/')

    @app.route('/status/issues')
    def list_issues():
        return render_template("services.html", url="/api/status/services?return_codes=1|2", page_title="Issues")

    @app.route('/status/tag/<tag_id>')
    def tags(tag_id):
        tag = history.get_tag(tag_id)
        tag['name'] = config_yaml['tags'][tag_id]['name']

        return render_template("services.html", url=f"/api/status/tag/{tag_id}", page_title=f"{tag['name']}")

    @app.route('/status/services/<service_filter>')
    def list_services(service_filter):
        return render_template("services.html", url=f"/api/status/services?service_filter={service_filter}", page_title="Services")

    @app.route('/perf_data/<service_id>')
    def get_perf_data(service_id):

        minutes = 60
        if(request.args.get('minutes') is not None):
            minutes = int(request.args.get('minutes'))

        service = history.get_service(service_id)
        return render_template('performance_data.html', service=service, minutes=minutes,
                               page_title=f"{service['host']['name']} {service['name']}")

    @app.route('/editor', methods=['GET'])
    def editor():

        # file path can be passed in with ?path=/path
        file_path = config_file
        if(request.args.get('path') is not None):
            file_path = request.args.get('path')

        return render_template("editor.html", config_file=file_path, editor_config=config_yaml['config']['web']['editor'],
                               page_title='Config Editor')

    @app.route('/tags', methods=['GET'])
    def view_tags():
        tags = dict(sorted(config_yaml['tags'].items()))  # sort by id

        return render_template("view_tags.html", tags=tags, page_title="Tags")

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

    @app.route('/api/list/hosts', methods=['GET'])
    def list_hosts():
        return jsonify(history.list_hosts())

    @app.route('/api/list/tags', methods=['GET'])
    def list_tags():
        return jsonify(config_yaml['tags'])

    @app.route('/api/status/hosts', methods=['GET'])
    def status():
        # get a list of hosts
        hosts = history.get_hosts()

        return jsonify(sorted(hosts, key=lambda o: o['name']))

    @app.route('/api/status/summary', methods=['GET'])
    def overall_status():
        overall_status = 0  # 0 is the target, means all is good
        error_count = 0

        # pull in all the hosts and get their overall status
        hosts = history.get_hosts()
        services = []
        for host in hosts:
            # catch for rare cases where host status hasn't been calculated yet
            if('overall_status' in host):
                # set the higher of the two values
                overall_status = host['overall_status'] if host['overall_status'] > overall_status else overall_status

                if(host['overall_status'] > 0):
                    error_count = error_count + 1

        # get services in error
        services = history.get_services([1, 2])

        return jsonify({"total_hosts": len(hosts), "hosts_with_errors": error_count, "services_with_errors": len(services),
                        "overall_status": overall_status, "overall_status_description": utils.SERVICE_STATUSES[overall_status],
                        "services": services})

    @app.route('/api/status/host/<host_id>', methods=['GET'])
    def get_host(host_id):
        host = history.get_host(host_id)

        return jsonify(host)

    @app.route('/api/status/services')
    def get_services_by_query():
        return_codes = [0, 1, 2, 3]  # by default return all codes
        service_filter = ".*"  # by default list all services

        if(request.args.get('return_codes') is not None):
            return_codes = request.args.get('return_codes').split("|")

        if(request.args.get('service_filter') is not None):
            service_filter = request.args.get('service_filter')

        services = history.get_services(return_codes, service_filter)

        # sort by return code, then name
        services = sorted(services, key=lambda o: (o['return_code'] * -1, o['host']['name']))

        return jsonify({"return_codes": return_codes, "service_filter": service_filter, "services": services})

    @app.route('/api/status/tag/<tag_id>', methods=['GET'])
    def get_tag(tag_id):
        tag = history.get_tag(tag_id)

        # convert services to an array
        tag['services'] = sorted(tag['services'], key=lambda o: o['host']['name'])

        return jsonify(tag)

    @app.route('/api/time/<id>', methods=['GET'], defaults={'start': None, 'end': None})
    @app.route('/api/time/<id>/<int:start>/<int:end>', methods=['GET'])
    def get_ts(id, start, end):
        # if end is blank, set to now
        if(end is None):
            end = int(time.time())

        # if start is blank, set to 1 hr
        if(start is None):
            start = end - 3600

        tag = history.get_ts_data(id, start, end)

        return jsonify(tag)

    @app.route('/api/command/check_now/<id>', methods=['POST'])
    def check_host_now(id):
        result = monitor.check_now(id)

        if(result['success']):
            # update the next check time in the DB as well
            aHost = history.get_host(id)
            aHost['next_check'] = result['next_check']
            history.save_host(id, aHost, update_perf_data=False)

        return jsonify(result)

    @app.route('/api/command/silence_host/<id>/<minutes>', methods=['POST'])
    def silence_host(id, minutes):
        until = datetime.datetime.now() + datetime.timedelta(minutes=int(minutes))
        result = monitor.silence_host(id, until)

        if(result['success']):
            # update the host in the history DB as well
            aHost = history.get_host(id)
            aHost['silenced'] = result['is_silenced']
            history.save_host(id, aHost, update_perf_data=False)

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

            if(style == 'button'):
                return utils.COLOR_MAPPING[config_yaml['config']['web']['top_nav']['style']['color']]
            else:
                return 'link'

        return dict(get_nav_style=get_style)

    return app
