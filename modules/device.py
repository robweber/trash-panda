import jinja2
import logging
import os.path
import subprocess
import time
import modules.jinja_custom as jinja_custom
import modules.utils as utils
from slugify import slugify
from pythonping import ping
from modules.exceptions import ConfigValueMissingError, ServiceNotFoundError


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

        # load jinja environment
        self._jinja = jinja2.Environment()
        self._jinja.globals['default'] = jinja_custom.load_default
        self._jinja.globals['path'] = os.path.join

    def __render_template(self, t_string, jinja_vars):
        template = self._jinja.from_string(t_string)

        return template.render(jinja_vars).strip()

    def __create_service_call(self, service, services_def):
        result = None

        if(service['type'] in services_def):
            serviceObj = services_def[service['type']]
            jinja_vars = {"NAGIOS_PATH": utils.NAGIOS_PATH, "SCRIPTS_PATH": os.path.join(utils.DIR_PATH, 'check_scripts'),
                          'service': service, 'host': self.config}

            # set the command first and then slot the arg values
            result = self.__render_template(serviceObj['command'], jinja_vars).split(' ')

            # load the arg values
            args = []
            for arg in serviceObj['args']:
                args.append(self.__render_template(arg, jinja_vars))

            # return everything as one array
            result = result + args
        else:
            raise ServiceNotFoundError(service['type'])

        return result

    def __serialize(self):
        result = {'type': self.type, 'name': self.name, 'address': self.address, 'icon': self.icon,
                  'info': self.info, 'interval': self.interval, 'last_check': self.last_check}

        if(self.management_page is not None):
            result['management_page'] = self.management_page

        return result

    def _ping(self):
        """
        Will attempt to ping the IP address via ICMP and return True or False
        True will only return if 50% or more pings are responded to
        """
        responses = ping(self.address, verbose=False, count=5)

        # get total of "success" responses
        total = list(filter(lambda x: x.success is True, responses))

        # if over 50% responded return True
        return True if (len(total)/len(responses) > .5) else False

    # executes a subprocess (python script) and returns the results
    def _run_process(self, program, args):
        """
        Kicks off a subprocess to run the defined program
        with the given arguments. Returns subprocess output.
        """
        command = program + args
        logging.debug(command)
        # run process, pipe all output
        output = subprocess.run(command, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return output

    def _run_python(self, script, args):
        """
        Helper method to run python programs specifically
        """
        return self._run_process(["python3", script], args)

    def _make_service(self, name, return_code, text):
        """
        Helper method to take the name, return_code, and output and wrap
        it in a Dict.
        """
        return {"name": name, "return_code": return_code, "text": text, "id": slugify(name)}

    def _custom_checks(self, services_def):
        result = []

        for s in self.services:
            output = self._run_process(self.__create_service_call(s, services_def), [])
            result.append(self._make_service(s['name'], output.returncode, output.stdout))
            time.sleep(2)

        return result

    def _get_services(self):
        # get the names defined in the custom service list
        return [s['name'] for s in self.services]

    def check_host(self, services_def):
        """
        Called to run the checks on this host. If the ping check fails all subsequent checks are skipped
        and a result listing them as Not Attempted (return code of 3) is used.
        """
        result = self.__serialize()

        service_results = []
        if(self._ping()):
            logging.debug(f"{self.name}: Is Alive")

            # the host is alive, continue checks
            service_results = self._custom_checks(services_def)

            service_results.append(self._make_service("Alive", 0, "Ping successfull!"))
        else:
            logging.debug(f"{self.name}: Is Not Alive")

            # the host is not alive, set "unknown" for all other services
            for service in self._get_services():
                service_results.append(self._make_service(service, 3, "Not attempted"))

            service_results.append(self._make_service("Alive", 2, "Ping failed"))

        result['services'] = sorted(service_results, key=lambda s: s['name'])

        return result

    def get_services(self):
        """
        Returns and array of all services this device will check
        """
        return ["Alive"] + self._get_services()


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
