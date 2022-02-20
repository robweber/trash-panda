import datetime
import importlib
import logging
import yaml
import modules.utils as utils
from functools import reduce
from slugify import slugify

DEVICE_TYPES = {"generic": {"package": "modules.devices.generic_device", "class": "GenericDevice"},
                "esxi": {"package": "modules.devices.esxi_device", "class": "ESXiDevice"},
                "switch": {"package": "modules.devices.switch_device", "class": "SwitchDevice"}}


def create_device(host):
    """
    Helper method to return a concrete DRDevice class from the given device information,
    typically loaded from a JSON file
    """
    result = None

    if(host['type'] in DEVICE_TYPES):
        mod = importlib.import_module(DEVICE_TYPES[host['type']]['package'])
        classObj = getattr(mod, DEVICE_TYPES[host['type']]['class'])

        if('config' in host):
            result = classObj(host['name'], host['ip'], host['config'])
        else:
            result = classObj(host['name'], host['ip'], {})

    return result


class HostMonitor:
    """
    Reads in a list of host information from a given JSON file. Will run defined checks on all hosts
    and return the results. Checks are run based on the loaded DRDevice class.
    """

    hosts = None
    time_format = "%m-%d-%Y %I:%M%p"

    def __init__(self, file, default_interval):
        yaml.add_constructor('!include', utils.custom_yaml_loader, Loader=yaml.SafeLoader)
        yaml_file = utils.read_yaml(file)
        self.hosts = yaml_file['hosts']

        # get host description by type
        fake_time = (datetime.datetime.now() - datetime.timedelta(weeks=1)).strftime(self.time_format)
        for i in range(0, len(self.hosts)):
            device = create_device(self.hosts[i])

            # set the icon to either the class default or user custom
            self.hosts[i]['icon'] = device.icon if 'icon' not in self.hosts[i] else self.hosts[i]['icon']
            # interval is either the default or whatever custom interval the user has set
            self.hosts[i]['interval'] = default_interval if 'interval' not in self.hosts[i] else self.hosts[i]['interval']
            self.hosts[i]['info'] = device.info

            # set the last check to way back to trigger an update
            self.hosts[i]['last_check'] = fake_time
            logging.info(f"Loading device {device.name} with check interval every {self.hosts[i]['interval']} min")

    def check_hosts(self):
        now = datetime.datetime.now()

        for i in range(0, len(self.hosts)):
            aHost = self.hosts[i]

            # check if we need to check this host
            last_check = datetime.datetime.strptime(aHost['last_check'], self.time_format)
            if(last_check < now - datetime.timedelta(minutes=aHost['interval'])):
                logging.debug(f"Checking {aHost['name']}")

                checker = create_device(aHost)

                # based on above "checker" should always have a value
                services = checker.check_host()

                # figure out the overall worst status
                overall_status = reduce(lambda x, y: x if x['return_code'] > y['return_code'] else y, services)
                aHost['overall_status'] = overall_status['return_code']

                # figure out if the host is alive at all
                host_alive = list(filter(lambda x: x['id'] == 'alive', services))
                aHost['alive'] = host_alive[0]['return_code']

                # set services, sorted by name
                aHost['services'] = sorted(services, key=lambda s: s['name'])

                # create a slug to act as the id for lookups
                if('id' not in aHost):
                    aHost['id'] = slugify(aHost['name'])

                # save the last check date
                aHost['last_check'] = now.strftime(self.time_format)
                self.hosts[i] = aHost

        return sorted(self.hosts, key=lambda o: o['name'])

    def get_host(self, id):
        result = None  # return none if not found

        for aHost in self.hosts:
            if('id' in aHost and aHost['id'] == id):
                result = aHost

        return result
