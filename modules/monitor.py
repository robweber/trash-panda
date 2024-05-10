import datetime
import jinja2
import json
import logging
import os.path
import subprocess
import time
import re
import modules.jinja_custom as jinja_custom
import modules.utils as utils
from random import randint
from slugify import slugify
from threading import Lock
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
    lock = Lock()  # lock for host updating functions

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

        # save a list of all valid hosts
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

    def __parse_perf_data(self, service_id, service_output):
        """ parses the perf data according to the Nagios format:
        https://nagios-plugins.org/doc/guidelines.html#AEN200
        """
        result = []
        perf_order = ["value", "warning", "critical", "min", "max"]

        # determine if there is any perf data
        perf_string = service_output.strip().split("|")
        if(len(perf_string) > 1):
            # this should get each perf data value sequence
            # this regex allows for quotes within a perf sequence
            for p in re.finditer("(\"[^\"]*\"|'[^']*'|[\\S]+)+", perf_string[1].strip()):

                # find all the numeric values
                values = []
                for t in re.finditer("(=|;)[+-]?((\\d+(\\.\\d+)?)|(\\.\\d+))|;", p.group()):
                    values.append(t.group()[1:])

                # map the values to the appropriate keys, filter out blank values
                mapping = {perf_order[i]: values[i] for i in range(0, len(values)) if values[i].strip() != ''}

                # get the label and unit of measure
                first_key = p.group().strip().split(";")[0].split("=")
                unit_of_measure = first_key[1][len(mapping["value"]):]

                # convert values to decimals
                mapping = {k: float(v) for k, v in mapping.items()}

                # add in the label and unit of measure
                p_id = slugify(first_key[0]) if slugify(first_key[0].strip()) != '' else 'root'
                mapping['id'] = f"{service_id}-{p_id}"
                mapping['label'] = first_key[0].replace("'", "")

                # only add if it exists
                if(unit_of_measure != ""):
                    mapping['uom'] = unit_of_measure

                result.append(mapping)

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
        Called to run the checks on a specific host. If the ping command fails all subsequent checks are skipped
        and a result listing them as Not Attempted (return code of 3) is used.
        """
        result = host.serialize()

        services = host.get_services()
        service_results = []

        # run the default ping command or a custom one to determine if host is alive
        is_alive = False

        if(host.ping_command is None):
            is_alive = self._ping(host.address)
        else:
            output = self.__run_process(self.__create_service_call(host.ping_command, host.config), [])
            is_alive = {"success": True if output.returncode == 0 else False, "performance_data": ""}

        if(is_alive['success']):
            logging.debug(f"{host.name}: Is Alive")

            # the host is alive, continue checks
            service_results = self.__custom_checks(services, host)

            service_results.append(self.__make_service_output(host, {'name': "Alive"}, 0, f"Ping successfull!|{is_alive['performance_data']}"))
        else:
            logging.debug(f"{host.name}: Is Not Alive")

            # the host is not alive, set "unknown" for all other services
            for service in services:
                service_results.append(self.__make_service_output(host, service, 3, "Not attempted"))

            service_results.append(self.__make_service_output(host, {'name': "Alive"}, 2, f"Ping failed|{is_alive['performance_data']}"))

        result['services'] = sorted(service_results, key=lambda s: s['name'])

        return result

    def _ping(self, address):
        """
        Will attempt to ping the IP address via ICMP and return True or False
        True will only return if 50% or more pings are responded to

        :returns: a dict containing a key for succcess (true/false) and the performance data
        """
        responses = ping(address, verbose=False, count=5)

        # get percent packet loss and averate return time
        total_success = 0
        rta = 0
        for r in responses:
            total_success = total_success + 1 if r.success is True else total_success
            rta = rta + r.time_elapsed_ms

        packet_loss = 1 - (total_success/len(responses))
        rta = rta/len(responses)

        # if less than 50% packet loss
        return {"success": True if (packet_loss < .5) else False,
                "performance_data": f"percent_packet_loss={packet_loss}% average_return_time={rta}ms"}

    def __make_service_output(self, host, service, return_code, text):
        """Helper method to take the name, return_code, and output and wrap
        it in a Dict.
        """
        service_id = f"{host.id}-{slugify(service['name'])}"
        now = datetime.datetime.now()
        result = {"name": service['name'], "return_code": return_code, "text": text, "raw_text": text, "id": service_id,
                  "check_attempt": 1, "state": utils.CONFIRMED_STATE, "last_state_change": now.strftime(utils.TIME_FORMAT),
                  "host": {"id": host.id, "name": host.name},
                  "tags": service['tags'] if 'tags' in service else []}

        # filter the service output text
        jinja_vars = {"value": text, "return_code": return_code}
        jinja_vars.update(self.custom_jinja_constants)  # add any custom constants

        # convert to dict if response is JSON
        if(utils.is_json(text)):
            jinja_vars['value'] = json.loads(text)

        jinja_template = service['output_filter'] if 'output_filter' in service else "{{ (value | string).split('|') | first }}"
        result['text'] = self.__render_template(jinja_template, jinja_vars)

        # generate the performance data (per nagios spec)
        perf_data = self.__parse_perf_data(service_id, result['raw_text'])
        if(perf_data):
            result['perf_data'] = perf_data

        # set service url if it exists
        if('service_url' in service and service['service_url'].strip() != ""):
            result['service_url'] = service['service_url']

        # add notifier if set at service level
        if('notifier' in service):
            result['notifier'] = service['notifier']

        # determine check attempts and service state (skip OK and Unknown states)
        old_service = self.history.get_service(service_id)
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
            result.append(self.__make_service_output(host, s, output.returncode, output.stdout))
            time.sleep(1)

        return result

    def check_hosts(self):
        """runs host checks on any host currently outside of their check interval
        the the updated hosts are returned as an array"""
        result = []
        now = datetime.datetime.now()

        with self.lock:
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
                    host_alive = list(filter(lambda x: x['id'] == f"{aHost.id}-alive", host_check['services']))
                    host_check['alive'] = host_alive[0]['return_code']

                    if(host_alive[0]['return_code'] > 0):
                        # if the host isn't alive that is the overall status
                        host_check['overall_status'] = host_alive[0]['return_code']

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
        """sets the next check time on the host to now, forcing a check"""
        result = {"success": False}

        aHost = self.get_host(id)

        if(aHost is not None):
            with self.lock:
                # reset the next check time and update the host
                aHost.next_check = datetime.datetime.now().strftime(utils.TIME_FORMAT)
                self.hosts[id] = aHost

                result['next_check'] = aHost.next_check
                result['success'] = True

        return result

    def silence_host(self, id, until):
        """sets the silenced property on a host which will expire when the current time
        exceeds the given datetime object
        """
        result = {"success": False}

        aHost = self.get_host(id)

        if(aHost is not None):
            with self.lock:
                # set the host as silenced until this datetime
                aHost.silenced = until.strftime(utils.TIME_FORMAT)
                self.hosts[id] = aHost

                logging.debug(f"Silencing {id} until {aHost.silenced}")
                result['is_silenced'] = aHost.is_silenced()
                result['until'] = aHost.silenced
                result['success'] = True

        return result
