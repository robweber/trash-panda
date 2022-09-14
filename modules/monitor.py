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
from modules.history import HostHistory
from modules.exceptions import DeviceNotFoundError, ServiceNotFoundError


class HostMonitor:
    """
    Reads in a list of host information from a given JSON file. Will run defined checks on all hosts
    and return the results. Checks are run based on the loaded Device class.
    """

    types = None
    services = None
    hosts = None
    history = None
    custom_jinja_constants = {}
    _jinja = None

    def __init__(self, yaml_file):
        # create the host type and services definitions, load history
        self.types = self.__create_types(yaml_file['types'], yaml_file['config']['default_interval'], yaml_file['config']['service_check_attempts'])
        self.services = yaml_file['services']
        self.hosts = {}
        self.history = HostHistory()

        # load jinja environment
        self._jinja = jinja2.Environment()
        self._jinja.globals['default'] = jinja_custom.load_default
        self._jinja.globals['path'] = os.path.join

        # if any global paths were set for the jinja environment
        if('jinja_constants' in yaml_file['config']):
            self.custom_jinja_constants = yaml_file['config']['jinja_constants']

        if(yaml_file['config']['check_on_startup']):
            # set to 1 hour day if we are forcing a check on startup
            logging.info("Forcing host check on startup")

        # get host description by type
        now = datetime.datetime.now()
        for i in range(0, len(yaml_file['hosts'])):
            device = self.__create_device(yaml_file['hosts'][i])

            from_history = self.history.get_host(device.id)
            if(from_history and not yaml_file['config']['check_on_startup']):
                # use the saved next check time
                device.next_check = from_history['next_check']
            else:
                # set the next check time to now
                next_check_now = now + datetime.timedelta(minutes=-1)
                device.next_check = next_check_now.strftime(utils.TIME_FORMAT)

            self.hosts[device.id] = device
            logging.info(f"Loading device {device.name} with check interval every {device.interval} min")

        # save a list of all valid host names
        self.history.set_hosts(self.get_hosts())

    def __create_types(self, types_def, default_interval, default_attempts):
        """Create devices type definitions based on defined YAML"""
        result = {}

        # create a host type for each defined type
        for t in types_def:
            logging.info(f"Loading host type {t}")
            result[t] = HostType(t, types_def[t], default_interval, default_attempts)

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
            jinja_vars = {"NAGIOS_PATH": utils.NAGIOS_PATH, "SCRIPTS_PATH": os.path.join(os.path.dirname(utils.DIR_PATH), 'trash-panda-scripts'),
                          'service': service_args, 'host': host_config}

            jinja_vars.update(self.custom_jinja_constants)  # add any custom constants

            # set the command first and then slot the arg values
            result = self.__render_template(serviceObj['command'], jinja_vars).split(' ')

            # load the arg values
            args = []
            if('args' in serviceObj):
                args = [self.__render_template(arg, jinja_vars) for arg in serviceObj['args']]

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
            service_results = self.__custom_checks(services, host)

            service_results.append(self.__make_service_output(host, "Alive", 0, "Ping successfull!"))
        else:
            logging.debug(f"{host.name}: Is Not Alive")

            # the host is not alive, set "unknown" for all other services
            for service in services:
                service_results.append(self.__make_service_output(host, service['name'], 3, "Not attempted", service['service_url']))

            service_results.append(self.__make_service_output(host, "Alive", 2, "Ping failed"))

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

    def __make_service_output(self, host, name, return_code, text, url=""):
        """Helper method to take the name, return_code, and output and wrap
        it in a Dict.
        """
        service_id = slugify(name)
        now = datetime.datetime.now()
        result = {"name": name, "return_code": return_code, "text": text, "id": service_id,
                  "check_attempt": 1, "state": utils.CONFIRMED_STATE, "last_state_change": now.strftime(utils.TIME_FORMAT)}

        if(url.strip() != ""):
            result['service_url'] = url

        # determine check attempts and service state (skip OK and Unknown states)
        old_service = self.history.get_service(host.id, service_id)
        if(old_service):
            # check if return code has changed to non-OK state - if max_check is = 1 skip unconfirmed states
            if(old_service['return_code'] != return_code and return_code in [1, 2] and host.check_attempts > 1):
                # we're in an unconfirmed state
                result['state'] = utils.UNCONFIRMED_STATE
            # if already in unconfirmed state
            elif(old_service['state'] == utils.UNCONFIRMED_STATE):
                # decide if we should keep checking
                if(old_service['check_attempt'] + 1 < host.check_attempts):
                    result['state'] = utils.UNCONFIRMED_STATE
                    result['check_attempt'] = old_service['check_attempt'] + 1

            # if the state hasn't changed or hasn't been confirmed
            if((old_service['return_code'] == return_code and old_service['state'] == result['state']) or result['state'] == utils.UNCONFIRMED_STATE):
                result['last_state_change'] = old_service['last_state_change']

        return result

    def __custom_checks(self, services, host):
        """run defined custom service checks from a host given the current host configuration"""
        result = []

        for s in services:
            output = self.__run_process(self.__create_service_call(s, host.config), [])
            result.append(self.__make_service_output(host, s['name'], output.returncode, output.stdout, s['service_url']))
            time.sleep(1)

        return result

    def check_hosts(self):
        """runs host checks on any host currently outside of their check interval
        the the updated hosts are returned as an array"""
        result = []
        now = datetime.datetime.now()

        for id, aHost in self.hosts.items():
            # check if we need to check this host,
            next_check = datetime.datetime.strptime(aHost.next_check, utils.TIME_FORMAT)
            if(next_check < now):
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

                # save the last and caclulate next check date
                aHost.last_check = now.strftime(utils.TIME_FORMAT)
                host_check['last_check'] = aHost.last_check

                #  add or subtract a bit from each check interval to help with system load
                next_check = now + datetime.timedelta(minutes=(aHost.interval), seconds=randint(-60, 60))
                aHost.next_check = next_check.strftime(utils.TIME_FORMAT)
                host_check['next_check'] = aHost.next_check

                self.hosts[id] = aHost
                result.append(host_check)

        return sorted(result, key=lambda o: o['name'])

    def get_hosts(self):
        return sorted([h.id for h in self.hosts.values()])

    def get_host(self, id):
        return self.hosts[id] if id in self.hosts else None

    def check_now(self, id):
        result = {"success": False}

        aHost = self.get_host(id)

        if(aHost is not None):
            # reset the next check time and update the host
            aHost.next_check = datetime.datetime.now().strftime(utils.TIME_FORMAT)
            self.hosts[id] = aHost

            result['next_check'] = aHost.next_check
            result['success'] = True

        return result
