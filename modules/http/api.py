import datetime
import logging
import os
import os.path
import time
from .. import utils as utils
from fastapi import FastAPI, Body, Path, Query
from fastapi.responses import PlainTextResponse
from natsort import natsorted
from pydantic import BaseModel, Field
from pathlib import Path as LoadPath
from typing import Annotated


class FilePath(BaseModel):
    path: str = Field(description="a valid file system directory of file path")
    reset: bool = False


class FileContents(BaseModel):
    path: str = Field(description="full system path to the file to write")
    contents: str = Field(description="string contents of the file to write")


def api_app(config_file, config_yaml, history):

    app = FastAPI(
        title="Trash Panda API",
        version="1.0.0",
        summary="Backend API for interacting with the Trash Panda monitoring service"
    )

    @app.get('/health', tags=['Health'], description=LoadPath('api_docs/get_health.md').read_text())
    def health():

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

    @app.get('/list/hosts', tags=['Informational'], description=LoadPath('api_docs/get_list_hosts.md').read_text())
    def list_hosts():

        return history.list_hosts()

    @app.get('/list/groups', tags=['Informational'], description=LoadPath('api_docs/get_list_groups.md').read_text())
    def list_groups():

        return sorted(history.list_groups())

    @app.get('/list/tags', tags=['Informational'], description=LoadPath('api_docs/get_list_tags.md').read_text())
    def list_tags():

        return config_yaml['tags']

    @app.get('/status/summary', tags=['Status'], description=LoadPath('api_docs/get_status_summary.md').read_text())
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
                "overall_status": overall_status,
                "overall_status_description": utils.SERVICE_STATUSES[overall_status],
                "services": services}

    @app.get('/status/hosts', tags=['Status'], description=LoadPath('api_docs/get_status_hosts.md').read_text())
    def status():
        # get a list of hosts
        hosts = history.get_hosts()

        return sorted(hosts, key=lambda o: o['name'])

    @app.get('/status/group/{group_name}', tags=['Status'], description=LoadPath('api_docs/get_status_group.md').read_text())
    def get_group(group_name: str = Path(description="a valid group name")):

        group = history.get_group(group_name)

        # sort by host name
        result = sorted(group, key=lambda o: o['name'])

        return result

    @app.get('/status/host/{host_id}', tags=['Status'], description=LoadPath('api_docs/get_status_hosts_id.md').read_text())
    def get_host(host_id: str = Path(description="A valid host id")):

        host = history.get_host(host_id)

        return host

    @app.get('/status/services', tags=['Status'], description=LoadPath('api_docs/get_status_services.md').read_text())
    def get_services_by_query(return_codes: Annotated[str, Query(description="Return codes to filter on, separate multiple with pipe")] = "0|1|2|3",
                              service_filter: Annotated[str, Query(description="Service filter, regex that filters on service id")] = ".*"):

        return_codes = return_codes.split("|")

        services = history.get_services(return_codes, service_filter)

        # sort by return code, then name
        services = sorted(services, key=lambda o: (o['return_code'] * -1, o['host']['name']))

        return {"return_codes": return_codes, "service_filter": service_filter, "services": services}

    @app.get('/status/tag/{type}/{tag_id}', tags=['Status'], description=LoadPath('api_docs/get_status_tag.md').read_text())
    def get_tag(type: str = Path(description="tag type, either host or service"), tag_id: str = Path(description="a valid tag id")):

        if(type == 'host'):
            tag = history.get_host_tag(tag_id)

            # sort the members
            tag['members'] = sorted(tag['members'], key=lambda o: o['name'])
        else:
            tag = history.get_service_tag(tag_id)

            # sort the members
            tag['members'] = sorted(tag['members'], key=lambda o: o['host']['name'])

        return tag

    @app.get('/time/{id}/{start}/{end}', tags=['Performance Data'], description=LoadPath('api_docs/get_perf_data_time.md').read_text())
    def get_ts(id: Annotated[str, Path(description="a valid performance id (host-service ids)")],
               start: Annotated[int, Path(description="UNIX timestamp representing the start interval")],
               end: Annotated[int, Path(description="UNIX timestamp representing the end interval, must be greater than start")]):
        # if end is blank, set to now
        if(end is None):
            end = int(time.time())

        # if start is blank, set to 1 hr
        if(start is None):
            start = end - 3600

        tag = history.get_ts_data(id, start, end)

        return tag

    @app.post('/editor/browse_files', tags=['Editor'])
    def list_directory(path: Annotated[FilePath, Body(embed=True)]):
        """
        Used by the UI file editor to browse the file system for available configuration files
        """
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

    @app.post('/editor/load_file', response_class=PlainTextResponse, tags=['Editor'])
    def load_file(file_path: Annotated[FilePath, Body(embed=True)]):
        """
        Used by the UI file editor
        Loads a file, in plaintext, given the path
        """
        file_contents = ''
        if(file_path.path.endswith(utils.ALLOWED_EDITOR_TYPES) and os.path.isfile(file_path.path)):
            with open(file_path.path) as f:
                file_contents = f.readlines()

        return ''.join(file_contents)

    @app.post('/editor/save_file', tags=['Editor'])
    def save_file(save_file: Annotated[FileContents, Body(embed=True)]):
        """
        Used by the UI file editor to save a file with the given contents
        """

        with open(save_file.path, 'w') as f:
            f.write(save_file.contents)

        return {'success': True, 'message': f"Saved {save_file.path}"}

    @app.get('/check_config', tags=['Health'], description=LoadPath('api_docs/get_check_config.md').read_text())
    def check_config():
        """

        """
        result = {'success': True, 'message': 'Config is valid'}

        # check the config and see if it validates
        yaml_check = utils.load_config_file(config_file)

        if(not yaml_check['valid']):
            result['success'] = False
            result['message'] = 'Configuration file is not valid'
            result['errors'] = yaml_check['errors']

        return result

    @app.post('/command/check_now/{id}', tags=['Command'], description=LoadPath('api_docs/post_command_check_now.md').read_text())
    def check_host_now(id: str = Path(description="A valid host id")):
        result = history.check_host_now(id)

        return result

    @app.post('/command/silence_host/{id}/{minutes}', tags=['Command'], description=LoadPath('api_docs/post_command_silence_host.md').read_text())
    def silence_host(id: str = Path(description="a valid host id"),
                     minutes: int = Path(description="the number of minutes to silence this host")):
        result = history.silence_host(id, minutes)

        logging.debug(f"Silencing {id} until {result['until']}")

        return result

    return app
