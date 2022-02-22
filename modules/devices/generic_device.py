import jinja2
import os
import os.path
import modules.utils as utils
import modules.jinja_custom as jinja_custom
from .. device import DRDevice


class GenericDevice(DRDevice):
    """
    Represents a generic network device, only alive status supported by default but services can be defined
    """
    _services = []
    _services_def = {}
    _jinja = None

    def __init__(self, name, address, config):
        super().__init__(name, address, "generic")

        # load the services definitions
        self._services_def = utils.read_yaml(os.path.join(utils.DIR_PATH, 'conf', 'services.yaml'))

        # load jinja environment
        self._jinja = jinja2.Environment()
        self._jinja.globals['default'] = jinja_custom.load_default
        self._jinja.globals['path'] = os.path.join

    def __render_template(self, t_string, jinja_vars):
        template = self._jinja.from_string(t_string)

        return template.render(jinja_vars).strip()

    def __create_service_call(self, service):
        result = None

        if(service['type'] in self._services_def):
            serviceObj = self._services_def[service['type']]
            jinja_vars = {"NAGIOS_PATH": utils.NAGIOS_PATH, "SCRIPTS_PATH": os.path.join(utils.DIR_PATH, 'check_scripts'), 'service': service}

            # set the command first and then slot the arg values
            result = self.__render_template(serviceObj['command'], jinja_vars).split(' ')

            # load the arg values
            args = []
            for arg in serviceObj['args']:
                args.append(self.__render_template(arg, jinja_vars))

            # return everything as one array
            result = result + args

        return result

    def _custom_checks(self):
        result = []

        for s in self._services:
            output = self._run_process(self.__create_service_call(s), [])
            result.append(self._make_service(s['name'], output.returncode, output.stdout))

        return result

    def _get_services(self):
        # get the names defined in the custom service list
        return [s['name'] for s in self._services]
