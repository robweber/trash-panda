import modules.utils as utils
from functools import reduce
from slugify import slugify
from modules.devices.esxi_device import ESXiDevice
from modules.devices.switch_device import SwitchDevice


def create_device(host):
    """
    Helper method to return a concrete DRDevice class from the given device information,
    typically loaded from a JSON file
    """
    result = None

    if(host['type'] == 'esxi'):
        result = ESXiDevice(host['name'], host['ip'], host['config'])
    elif(host['type'] == 'switch'):
        result = SwitchDevice(host['name'], host['ip'], host['config'])

    return result


class HostMonitor:
    """
    Reads in a list of host information from a given JSON file. Will run defined checks on all hosts
    and return the results. Checks are run based on the loaded DRDevice class.
    """

    hosts = None
    types = {"esxi", "switch"}

    def __init__(self, file):
        self.hosts = utils.read_json(file)

        # get host description by type
        for i in range(0, len(self.hosts)):
            device = create_device(self.hosts[i])

            self.hosts[i]['info'] = device.info
            self.hosts[i]['icon'] = device.icon

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
