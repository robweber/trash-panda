import logging
import os
import os.path
from .. import utils as utils
from collections import defaultdict
from datetime import timedelta
from flask import Flask, session, flash, render_template, redirect, request, url_for
from flask_session import Session
from slugify import slugify


def flask_app(config_file, config_yaml, history, notifier_configured, debugMode=False, logHandlers=[]):
    app = Flask(import_name="trash-panda", static_folder=os.path.join(utils.DIR_PATH, 'web', 'static'),
                template_folder=os.path.join(utils.DIR_PATH, 'web', 'templates'))
    # add use of slugify for templates
    app.jinja_env.globals.update(slugify=slugify)

    # generate random number for session secret key
    app.secret_key = os.urandom(24)
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=1)

    # add handlers for this app
    for h in logHandlers:
        app.logger.addHandler(h)

    # set log level
    logLevel = 'INFO' if not debugMode else 'DEBUG'
    app.logger.setLevel(getattr(logging, logLevel))
    app.debug = debugMode

    @app.route('/', methods=["GET"])
    def index():
        return render_template("hosts.html", url="/api/status/hosts", message=config_yaml['config']['web']['landing_page_text'])

    @app.route('/status/host/<id>')
    def host_status(id):
        result = history.get_host(id)

        if(result):
            # set if a notifier is configured to toggle silent mode controls
            doc_file = os.path.join(config_yaml['config']['docs_dir'], f"{id}.md")

            vault_entries = []
            if(config_yaml['config']['vault']['enabled'] and 'vault_key' in session):
                vault_entries = utils.search_vault_file(config_yaml['config']['vault']['keepass_file'], session['vault_key'], id)

            return render_template("host_status.html", host=result, page_title='Host Status', has_notifier=notifier_configured,
                                   docs=utils.load_documentation(doc_file), doc_file=doc_file, vault_entries=vault_entries, tags=config_yaml['tags'])
        else:
            flash('Host page not found', 'warning')
            return redirect('/')

    @app.route('/status/issues')
    def list_issues():
        return render_template("services.html", url="/api/status/services?return_codes=1|2", page_title="Issues")

    @app.route('/status/tag/<type>/<tag_id>')
    def tags(type, tag_id):
        if(type == 'host'):
            tag = history.get_host_tag(tag_id)
        else:
            tag = history.get_service_tag(tag_id)

        tag['name'] = config_yaml['tags'][tag_id]['name']

        return render_template(f"{type}s.html", url=f"/api/status/tag/{type}/{tag_id}", tag_id=tag_id, page_title=f"{tag['name']}")

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

    @app.route('/vault', methods=['GET'])
    def vault():
        redirect_url = ""

        entries = []
        # check if vault key is currently set
        if(config_yaml['config']['vault']['enabled'] and 'vault_key' in session):
            # list all the current entries
            entries = utils.search_vault_file(config_yaml['config']['vault']['keepass_file'], session['vault_key'])
        else:
            # check if there is a redirect
            redirect_url = request.args.get('redirect') if request.args.get('redirect') != None else ""

        return render_template('vault.html', vault_entries=entries, redirect=redirect_url, page_title="Vault")

    @app.route('/vault', methods=['POST'])
    def unlock_vault():
        vault_pass = request.form.get('vault_password')
        redirect_url = url_for('vault')  # default redirect back to vault unlock page

        # try to unlock the vault file
        unlocked = utils.unlock_vault_file(config_yaml['config']['vault']['keepass_file'], vault_pass)

        if(unlocked['success']):
            # everything is OK
            session['vault_key'] = vault_pass

            # if we came from another page
            if(request.form.get('redirect_url') != ""):
                redirect_url = url_for('host_status', id=request.form.get('redirect_url'))

        else:
            flash(unlocked['message'], 'danger')

        return redirect(redirect_url)

    @app.route('/lock_vault', methods=['GET'])
    def lock_vault():
        # just destroy the session
        session.clear()

        flash('Vault Locked', 'success')
        return redirect(url_for('vault'))

    @app.route('/tags/<type>', methods=['GET'])
    def view_tags(type):
        # filter tags on those used by this type
        filter_list = history.get_tags(type)

        tags = {k: v for k, v in config_yaml['tags'].items() if k in filter_list}

        # sort
        tags = dict(sorted(tags.items()))

        return render_template("view_tags.html", tags=tags, tag_type=type, page_title=f"{type.capitalize()} Tags")

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

    """ Start of custom processors """

    @app.context_processor
    def vault_enabled():
        # returns disabled, enabled, or unlocked depending on vault status
        def get_vault_status():
            result = "disabled"

            if(config_yaml['config']['vault']['enabled'] and 'vault_key' in session):
                result = "unlocked"
            elif(config_yaml['config']['vault']['enabled']):
                result = "enabled"

            return result
        return dict(vault_status=get_vault_status)

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
                return config_yaml['config']['web']['top_nav']['style']['color']
            else:
                return 'link'

        return dict(get_nav_style=get_style)

    @app.context_processor
    def list_hostgroups():
        def list_hosts():

            # get a list of hosts
            hosts = history.get_hosts()

            # group them by primary tag
            grouped = defaultdict(list)
            for h in hosts:
                h_sub = {"name": h['name'], "id": h['id'], "icon": h['icon']}

                if('tags' in h and len(h['tags']) != 0):
                    # primary tag is the first one
                    grouped[h['tags'][0]].append(h_sub)
                else:
                    grouped['ungrouped'].append(h_sub)

            # return list of groups, each containing the members
            result = [
                {"group": group, "members": sorted(members, key=lambda o: o['name'])}
                for group, members in grouped.items()
            ]

            # sort by group name
            return sorted(result, key=lambda o: o['group'])

        return dict(list_hostgroups=list_hosts)

    @app.context_processor
    def link_title():
        def get_title():
            # get the dropdown title for any custom links - if set
            return config_yaml['config']['web']['top_nav']['links_title']
        return dict(custom_link_title=get_title)

    Session(app)
    return app
