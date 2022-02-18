import importlib
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
            result = classObj(host['name'], host['ip'])

    return result


class HostMonitor:
    """
    Reads in a list of host information from a given JSON file. Will run defined checks on all hosts
    and return the results. Checks are run based on the loaded DRDevice class.
    """

    hosts = None
    types = {"esxi", "switch", "generic"}

    def __init__(self, file):
        yaml_file = utils.read_yaml(file)
        self.hosts = yaml_file['hosts']

        # get host description by type
        for i in range(0, len(self.hosts)):
            device = create_device(self.hosts[i])

            # set the icon to either the class default or user custom
            self.hosts[i]['icon'] = device.icon if 'icon' not in self.hosts[i] else self.hosts[i]['icon']
            self.hosts[i]['info'] = device.info

    def check_hosts(self):
        result = []

        for aHost in self.hosts:
            services = []

            # if the host is a valid type, run service checks
            if(aHost['type'] in self.types):
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

            result.append(aHost)

        return sorted(result, key=lambda o: o['name'])

    def get_host(self, id):
        result = None  # return none if not found

        for aHost in self.hosts:
            if('id' in aHost and aHost['id'] == id):
                result = aHost

        return result
