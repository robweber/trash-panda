from slugify import slugify
from modules.exceptions import ConfigValueMissingError


class Device:
    """
    Represents a specific host device as defined by the user in the yaml config file
    This merges in all parent items from the device type, including service checks
    """
    __jinja = None

    type = None
    name = None
    address = None
    management_page = None
    config = {}
    info = ""
    icon = "devices"
    interval = 5
    services = []

    def __init__(self, host_def):
        self.type = host_def['type']
        self.id = slugify(host_def['name'])
        self.name = host_def['name']
        self.address = host_def['address']
        self.management_page = None if 'management_page' not in host_def else host_def['management_page']
        self.info = host_def['info']
        self.icon = host_def['icon']
        self.interval = host_def['interval']
        self.config = host_def['config']
        self.services = host_def['services']
        self.last_check = 0

        # set the address as part of the config
        self.config['address'] = self.address

    def serialize(self):
        """takes the current host configuration and returns it as a dictionary object, which
        can be serialized for JSON output"""
        result = {'type': self.type, 'id': self.id, 'name': self.name, 'address': self.address,
                  'icon': self.icon, 'info': self.info, 'interval': self.interval, 'last_check': self.last_check}

        if(self.management_page is not None):
            result['management_page'] = self.management_page

        return result

    def get_services(self):
        """
        Returns and array of all services this device will check
        """
        return self.services


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
    config = {}
    services = []

    def __init__(self, type_name, type_def, default_interval):
        self.type = type_name
        self.name = type_def['name']
        self.interval = default_interval if 'interval' not in type_def else type_def['interval']

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
            # TODO if not required but missing set the default value

    def create_device(self, device_def):
        result = None

        # marry the device definition with the type definition
        if('info' not in device_def):
            device_def['info'] = self.info

        if('icon' not in device_def):
            device_def['icon'] = self.icon

        if('interval' not in device_def):
            device_def['interval'] = self.interval

        if('config' not in device_def):
            device_def['config'] = {}

        # add the services
        if('services' in device_def):
            device_def['services'] = self.services + device_def['services']
        else:
            device_def['services'] = self.services

        self.__check_defaults(device_def['name'], device_def['config'])

        result = Device(device_def)

        return result
