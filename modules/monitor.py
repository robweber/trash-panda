import logging
import time
import modules.utils as utils
from functools import reduce
from slugify import slugify
from modules.devices.esxi_device import ESXiDevice
from modules.devices.switch_device import SwitchDevice

def create_device(host):
    result = None

    if(host['type'] == 'esxi'):
        result = ESXiDevice(host['name'], host['ip'], host['config'])
    elif(host['type'] == 'switch'):
        result = SwitchDevice(host['name'], host['ip'], host['config'])

    return result

class HostMonitor:
    hosts = None
    types = {"esxi", "switch"}

    def __init__(self, file):
        self.hosts = utils.read_json(file)

    def check_hosts(self):
        result = []

        for aHost in self.hosts['hosts']:
            services = []

            # if the host is a valid type, run service checks
            if(aHost['type'] in self.types):
                checker = create_device(aHost)

                # based on above "checker" should always have a value
                services = checker.check_host()

            # figure out the overall worse status
            overall_status = reduce(lambda x, y: x if x['return_code'] > y['return_code'] else y, services)
            aHost['overall_status'] = overall_status['return_code']

            # set services, sorted by name
            aHost['services'] = sorted(services, key = lambda s: s['name'])

            # create a slug to act as the id for lookups
            if('id' not in aHost):
                aHost['id'] = slugify(aHost['name'])

            result.append(aHost)

        return sorted(result, key = lambda o: o['name'])

    def get_host(self, id):
        result = None  # return none if not found

        for aHost in self.hosts['hosts']:
            if('id' in aHost and aHost['id'] == id):
                result = aHost

        return result
