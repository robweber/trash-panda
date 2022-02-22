import datetime
import importlib
import logging
import yaml
import modules.utils as utils
from functools import reduce
from slugify import slugify
from modules.device import HostType


class HostMonitor:
    """
    Reads in a list of host information from a given JSON file. Will run defined checks on all hosts
    and return the results. Checks are run based on the loaded DRDevice class.
    """

    types = None
    services = None
    hosts = None
    host_results = None
    time_format = "%m-%d-%Y %I:%M%p"

    def __init__(self, file, default_interval):
        yaml.add_constructor('!include', utils.custom_yaml_loader, Loader=yaml.SafeLoader)
        yaml_file = utils.read_yaml(file)

        # create the host type and services definitions
        self.types = self.__create_types(yaml_file['types'], default_interval)
        self.services = yaml_file['services']
        self.hosts = []
        self.host_results = {}

        # get host description by type
        fake_time = (datetime.datetime.now() - datetime.timedelta(weeks=1)).strftime(self.time_format)
        for i in range(0, len(yaml_file['hosts'])):
            device = self.__create_device(yaml_file['hosts'][i])

            # set the last check to way back to trigger an update
            device.last_check = fake_time
            self.hosts.append(device)
            logging.info(f"Loading device {device.name} with check interval every {device.interval} min")

    def __create_types(self, types_def, default_interval):
        result = {}

        # create a host type for each defined type
        for t in types_def:
            logging.info(f"Loading host type {t}")
            result[t] = HostType(t, types_def[t], default_interval)

        return result

    def __create_device(self, device_def):
        result = None

        if(device_def['type'] in self.types):
            result = self.types[device_def['type']].create_device(device_def)
        else:
            logging.error(f"Device type {device_def['type']} is not defined")
        return result  # TODO - throw an error if it doesn't exist

    def check_hosts(self):
        now = datetime.datetime.now()

        for i in range(0, len(self.hosts)):
            aHost = self.hosts[i]

            # check if we need to check this host
            last_check = datetime.datetime.strptime(aHost.last_check, self.time_format)
            if(last_check < now - datetime.timedelta(minutes=aHost.interval)):
                logging.debug(f"Checking {aHost.name}")

                host_check = aHost.check_host(self.services)

                # figure out the overall worst status
                overall_status = reduce(lambda x, y: x if x['return_code'] > y['return_code'] else y, host_check['services'])
                host_check['overall_status'] = overall_status['return_code']

                # figure out if the host is alive at all
                host_alive = list(filter(lambda x: x['id'] == 'alive', host_check['services']))
                host_check['alive'] = host_alive[0]['return_code']

                # create a slug to act as the id for lookups
                host_check['id'] = slugify(aHost.name)

                # save the last check date
                aHost.last_check = now.strftime(self.time_format)
                host_check['last_check'] = aHost.last_check

                self.hosts[i] = aHost
                self.host_results[aHost.name] = host_check

        return sorted(self.host_results.values(), key=lambda o: o['name'])

    def get_host(self, id):
        result = None  # return none if not found

        for aHost in self.hosts:
            if('id' in aHost and aHost['id'] == id):
                result = aHost

        return result
