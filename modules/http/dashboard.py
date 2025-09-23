import datetime
import logging
import os
import os.path
from .. import utils as utils
from flask import Flask, flash, render_template, jsonify, redirect, request, Response
from slugify import slugify

def flask_app(config_file, config_yaml, history, notifier_configured, debugMode=False, logHandlers=[]):
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

    @app.post('/command/check_now/{id}')
    def check_host_now(id):
        result = monitor.check_now(id)

        if(result['success']):
            # update the next check time in the DB as well
            aHost = history.get_host(id)
            aHost['next_check'] = result['next_check']
            history.save_host(id, aHost, update_perf_data=False)

        return result

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
