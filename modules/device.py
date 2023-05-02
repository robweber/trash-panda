import modules.utils as utils
from datetime import datetime
from slugify import slugify
from modules.exceptions import ConfigValueMissingError


class Device:
    """
    Represents a specific host device as defined by the user in the yaml config file
    This merges in all parent items from the device type, including service checks
    """
    type = None
    name = None
    address = None
    management_page = None
    config = {}
    info = ""
    icon = "devices"
    interval = 5
    check_attempts = 3
    services = []
    silenced = False

    def __init__(self, host_def):
        self.type = host_def['type']
        self.id = slugify(host_def['name'])
        self.name = host_def['name']
        self.address = host_def['address']
        self.management_page = None if 'management_page' not in host_def else host_def['management_page']
        self.info = host_def['info']
        self.icon = host_def['icon']
        self.interval = host_def['interval']
        self.check_attempts = host_def['service_check_attempts']
        self.config = host_def['config']
        self.services = host_def['services']
        self.last_check = 0
        self.next_check = 0
        self.silenced = datetime.now().strftime(utils.TIME_FORMAT)

        # set the address as part of the config
        self.config['address'] = self.address

    def serialize(self):
        """takes the current host configuration and returns it as a dictionary object, which
        can be serialized for JSON output"""
        result = {'type': self.type, 'id': self.id, 'name': self.name, 'address': self.address,
                  'icon': self.icon, 'info': self.info, 'interval': self.interval, 'service_check_attempts': self.check_attempts,
                  'last_check': self.last_check, 'config': self.config, 'silenced': self.is_silenced()}

        if(self.management_page is not None):
            result['management_page'] = self.management_page

        return result

    def get_services(self):
        """
        Returns and array of all services this device will check
        """
        return self.services

    def is_silenced(self):
        """
        Returns true/false if the host should currently be in silent mode.
        This is true if the silenced timestamp is greater than the current time
        """
        silence_off = datetime.strptime(self.silenced, utils.TIME_FORMAT)

        return silence_off > datetime.now()


class HostType:
    """Represents a specific HostType definition as defined by the user in the yaml config file
    A host type defines services for a specific type of device, as well as any required configuration
    options needed for service checks to work.
    """
    type = None
    name = None
    info = ""
    icon = 'devices'
    interval = 5
    check_attempts = 3
    config = {}
    services = []

    def __init__(self, type_name, type_def, default_interval, default_attempts):
        self.type = type_name
        self.name = type_def['name']
        self.interval = default_interval if 'interval' not in type_def else type_def['interval']
        self.check_attempts = default_attempts if 'service_check_attempts' not in type_def else type_def['service_check_attempts']

        if('info' in type_def):
            self.info = type_def['info']

        if('icon' in type_def):
            self.icon = type_def['icon']

        if('config' in type_def):
            self.config = type_def['config']

        if('services' in type_def):
            self.services = type_def['services']

    def __check_defaults(self, device_name, device_config):

        for v in self.config:
            if(self.config[v]['required'] and v not in device_config):
                # this value is required but missing
                raise ConfigValueMissingError(device_name, v, self.type)
            elif(not self.config[v]['required'] and v not in device_config and 'default' in self.config[v]):
                # set default if no value exists
                device_config[v] = self.config[v]['default']

        return device_config

    def create_device(self, device_def):
        result = None

        # marry the device definition with the type definition
        if('info' not in device_def):
            device_def['info'] = self.info

        if('icon' not in device_def):
            device_def['icon'] = self.icon

        if('interval' not in device_def):
            device_def['interval'] = self.interval

        if('service_check_attempts' not in device_def):
            device_def['service_check_attempts'] = self.check_attempts

        if('config' not in device_def):
            device_def['config'] = {}

        # add the services
        if('services' in device_def):
            device_def['services'] = self.services + device_def['services']
        else:
            device_def['services'] = self.services

        device_def['config'] = self.__check_defaults(device_def['name'], device_def['config'])

        result = Device(device_def)

        return result
