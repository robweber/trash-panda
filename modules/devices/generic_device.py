import os
import modules.utils as utils
from .. device import DRDevice

"""
list of service types and their commands and arguments
arguments are set via an array with placeholders the arg_slots definition
defines which config named values go in which argument slots, if a named config
value doesn't exist the placeholder value is used
"""
SERVICES = {"http": {"command": os.path.join(utils.NAGIOS_PATH, "check_http"),
                     "args": ['-H', "", '-p', "80", "-u", "/"],
                     "arg_slots": {1: "hostname", 3: "port", 5: "path"}},
            "https": {"command": os.path.join(utils.NAGIOS_PATH, "check_http"),
                      "args": ['-H', "", '-p', "443", "-u", "/", "-S"],
                      "arg_slots": {1: "hostname", 3: "port", 5: "path"}}}


class GenericDevice(DRDevice):
    """
    Represents a generic network device, only alive status supported by default but services can be defined
    """
    services = []

    def __init__(self, name, address, config):
        super().__init__(name, address, "generic")

        self.info = ("This is a generic IP network device that by default checks up/down status only. " +
                     "Services can be configured but are custom per device type.")

        if('services' in config):
            self.services = config['services']

    def __create_service_call(self, service):
        result = None

        if(service['type'] in SERVICES):
            serviceObj = SERVICES[service['type']]

            # set the command first and then slot the arg values
            result = [serviceObj['command']]
            args = serviceObj['args'].copy()

            # slot the values
            for slot in serviceObj['arg_slots'].keys():
                # make sure the key exists
                if(serviceObj['arg_slots'][slot] in service):
                    args[slot] = str(service[serviceObj['arg_slots'][slot]])

            # return everything as one array
            result = result + args

        return result

    def _custom_checks(self):
        result = []

        for s in self.services:
            output = self._run_process(self.__create_service_call(s), [])
            result.append(self._make_service(s['name'], output.returncode, output.stdout))

        return result

    def _get_services(self):
        # get the names defined in the custom service list
        return [s['name'] for s in self.services]
