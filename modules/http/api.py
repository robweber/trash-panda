import datetime
import os
import os.path
import time
from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from natsort import natsorted
from pydantic import BaseModel
from .. import utils as utils

class FilePath(BaseModel):
    path: str
    reset: bool = False


def api_app(config_file, config_yaml, history, notifier_configured, debugMode=False, logHandlers=[]):

    app = FastAPI()

    @app.get('/health')
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

        return status

    @app.get('/list/hosts')
    def list_hosts():
        return history.list_hosts()

    @app.get('/list/tags')
    def list_tags():
        return config_yaml['tags']

    @app.get('/status/hosts')
    def status():
        # get a list of hosts
        hosts = history.get_hosts()

        return sorted(hosts, key=lambda o: o['name'])

    @app.get('/status/summary')
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

        return {"total_hosts": len(hosts), "hosts_with_errors": error_count, "services_with_errors": len(services),
                        "overall_status": overall_status, "overall_status_description": utils.SERVICE_STATUSES[overall_status],
                        "services": services}

    @app.get('/status/host/{host_id}')
    def get_host(host_id):
        host = history.get_host(host_id)

        return host

    @app.get('/status/services')
    def get_services_by_query(return_codes = "0|1|2|3", service_filter=".*"):
        """ by default lookup all return codes and list all services """

        return_codes = return_codes.split("|")

        services = history.get_services(return_codes, service_filter)

        # sort by return code, then name
        services = sorted(services, key=lambda o: (o['return_code'] * -1, o['host']['name']))

        return {"return_codes": return_codes, "service_filter": service_filter, "services": services}

    @app.get('/status/tag/{tag_id}')
    def get_tag(tag_id):
        tag = history.get_tag(tag_id)

        # convert services to an array
        tag['services'] = sorted(tag['services'], key=lambda o: o['host']['name'])

        return tag

    @app.get('/time/{id}')
    @app.get('/time/{id}/{start}/{end}')
    def get_ts(id, start: int = None, end: int = None):
        # if end is blank, set to now
        if(end is None):
            end = int(time.time())

        # if start is blank, set to 1 hr
        if(start is None):
            start = end - 3600

        tag = history.get_ts_data(id, start, end)

        return tag

    @app.post('/editor/browse_files')
    def list_directory(path: FilePath):
        if(path.reset):
            path.path = utils.DIR_PATH

        if(not path.path.startswith('/')):
            path.path = f"/{path.path}"

        # if path is a file, get directory
        if(os.path.isfile(path.path)):
            path.path = os.path.dirname(path.path)

        # get a list of all the directories
        dirs = sorted([name for name in os.listdir(path.path) if os.path.isdir(os.path.join(path.path, name))])

        # get a list of all the files, filter on valid yaml
        files = natsorted(filter(lambda f: f.endswith(utils.ALLOWED_EDITOR_TYPES), os.listdir(path.path)))

        return {'success': True, 'dirs': dirs, 'files': files, 'path': path.path}

    @app.post('/editor/load_file', response_class=PlainTextResponse)
    def load_file(file_path: FilePath):

        file_contents = ''
        if(file_path.path.endswith(utils.ALLOWED_EDITOR_TYPES) and os.path.isfile(file_path.path)):
            with open(file_path.path) as f:
                file_contents = f.readlines()

        return ''.join(file_contents)

    return app
