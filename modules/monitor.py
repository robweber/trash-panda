import datetime
import jinja2
import logging
import os.path
import subprocess
import time
import modules.jinja_custom as jinja_custom
import modules.utils as utils
from random import randint
from slugify import slugify
from functools import reduce
from modules.device import HostType
from pythonping import ping
from modules.exceptions import DeviceNotFoundError, ServiceNotFoundError


class HostMonitor:
    """
    Reads in a list of host information from a given JSON file. Will run defined checks on all hosts
    and return the results. Checks are run based on the loaded Device class.
    """

    types = None
    services = None
    hosts = None
    time_format = "%m-%d-%Y %I:%M%p"
    __jinja = None

    def __init__(self, yaml_file):
        # create the host type and services definitions
        self.types = self.__create_types(yaml_file['types'], yaml_file['config']['default_interval'])
        self.services = yaml_file['services']
        self.hosts = []

        # load jinja environment
        self._jinja = jinja2.Environment()
        self._jinja.globals['default'] = jinja_custom.load_default
        self._jinja.globals['path'] = os.path.join

        # if we should force a check on startup
        fake_time = datetime.datetime.now().strftime(self.time_format)
        if(yaml_file['config']['check_on_startup']):
            logging.info("Forcing host check on startup")
            fake_time = (datetime.datetime.now() - datetime.timedelta(weeks=1)).strftime(self.time_format)

        # get host description by type
        for i in range(0, len(yaml_file['hosts'])):
            device = self.__create_device(yaml_file['hosts'][i])

            # set the last check to way back to trigger an update
            device.last_check = fake_time
            self.hosts.append(device)
            logging.info(f"Loading device {device.name} with check interval every {device.interval} min")

    def __create_types(self, types_def, default_interval):
        """Create devices type definitions based on defined YAML"""
        result = {}

        # create a host type for each defined type
        for t in types_def:
            logging.info(f"Loading host type {t}")
            result[t] = HostType(t, types_def[t], default_interval)

        return result

    def __create_device(self, device_def):
        """Create a host device type based on defined YAML"""
        result = None

        if(device_def['type'] in self.types):
            result = self.types[device_def['type']].create_device(device_def)
        else:
            raise DeviceNotFoundError(device_def['name'], device_def['type'])

        return result

    def __render_template(self, t_string, jinja_vars):
        """renders template string using Jinja environment and returns the result"""
        template = self._jinja.from_string(t_string)

        return template.render(jinja_vars).strip()

    def __create_service_call(self, service, host_config):
        """creates the service call based on the defined service definition and supplied arguments
        function will run all arguments through Jinja templates to fully expand and then return an array
        that can be sent to the __run_process function
        """
        result = None

        if(service['type'] in self.services):
            serviceObj = self.services[service['type']]
            service_args = service['args'] if 'args' in service else {}
            jinja_vars = {"NAGIOS_PATH": utils.NAGIOS_PATH, "SCRIPTS_PATH": os.path.join(utils.DIR_PATH, 'check_scripts'),
                          'service': service_args, 'host': host_config}

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

    # executes a subprocess (python script) and returns the results
    def __run_process(self, program, args):
        """
        Kicks off a subprocess to run the defined program
        with the given arguments. Returns subprocess output.
        """
        command = program + args
        logging.debug(command)
        # run process, pipe all output
        output = subprocess.run(command, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return output

    def __check_host(self, host):
        """
        Called to run the checks on a specific host. If the ping check fails all subsequent checks are skipped
        and a result listing them as Not Attempted (return code of 3) is used.
        """
        result = host.serialize()

        services = host.get_services()
        service_results = []
        if(self._ping(host.address)):
            logging.debug(f"{host.name}: Is Alive")

            # the host is alive, continue checks
            service_results = self.__custom_checks(services, host.config)

            service_results.append(self.__make_service_output("Alive", 0, "Ping successfull!"))
        else:
            logging.debug(f"{host.name}: Is Not Alive")

            # the host is not alive, set "unknown" for all other services
            for service in services:
                service_results.append(self.__make_service_output(service['name'], 3, "Not attempted"))

            service_results.append(self.__make_service_output("Alive", 2, "Ping failed"))

        result['services'] = sorted(service_results, key=lambda s: s['name'])

        return result

    def _ping(self, address):
        """
        Will attempt to ping the IP address via ICMP and return True or False
        True will only return if 50% or more pings are responded to
        """
        responses = ping(address, verbose=False, count=5)

        # get total of "success" responses
        total = list(filter(lambda x: x.success is True, responses))

        # if over 50% responded return True
        return True if (len(total)/len(responses) > .5) else False

    def __make_service_output(self, name, return_code, text, url=None):
        """Helper method to take the name, return_code, and output and wrap
        it in a Dict.
        """
        result = {"name": name, "return_code": return_code, "text": text, "id": slugify(name)}

        if(url is not None):
            result['service_url'] = url

        return result

    def __custom_checks(self, services, host_config):
        """run defined custom service checks from a host given the current host configuration"""
        result = []

        for s in services:
            output = self.__run_process(self.__create_service_call(s, host_config), [])
            result.append(self.__make_service_output(s['name'], output.returncode, output.stdout, s['service_url'] if 'service_url' in s else None))
            time.sleep(1)

        return result

    def check_hosts(self):
        """runs host checks on any host currently outside of their check interval
        the the updated hosts are returned as an array"""
        result = []
        now = datetime.datetime.now()

        for i in range(0, len(self.hosts)):
            aHost = self.hosts[i]

            # check if we need to check this host, add or subtract a bit from each check interval to help with system load
            last_check = datetime.datetime.strptime(aHost.last_check, self.time_format)
            if(last_check < now - datetime.timedelta(minutes=(aHost.interval), seconds=randint(-60, 60))):
                logging.debug(f"Checking {aHost.name}")

                host_check = self.__check_host(aHost)

                # figure out the overall worst status
                overall_status = reduce(lambda x, y: x if x['return_code'] > y['return_code'] else y, host_check['services'])
                host_check['overall_status'] = overall_status['return_code']

                # figure out if the host is alive at all
                host_alive = list(filter(lambda x: x['id'] == 'alive', host_check['services']))
                host_check['alive'] = host_alive[0]['return_code']

                # create a slug to act as the id for lookups
                host_check['id'] = aHost.id

                # save the last check date
                aHost.last_check = now.strftime(self.time_format)
                host_check['last_check'] = aHost.last_check

                self.hosts[i] = aHost
                result.append(host_check)

        return sorted(result, key=lambda o: o['name'])

    def get_hosts(self):
        return sorted([h.id for h in self.hosts])

    def get_host(self, id):
        result = None  # return none if not found

        for aHost in self.hosts:
            if('id' in aHost and aHost['id'] == id):
                result = aHost

        return result
