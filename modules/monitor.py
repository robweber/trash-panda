import logging
import os
import subprocess
import time
import modules.utils as utils
from functools import reduce
from pythonping import ping
from slugify import slugify


class PingCheck:
    count = 5  # number of ping requests to make

    def __init__(self, count=5):
        self.count = count

    def check_host(self, ip):
        responses = ping(ip, verbose=False, count=self.count)

        # get total of "success" responses
        total = list(filter(lambda x: x.success == True, responses))

        # if over 50% responded return True
        return True if (len(total)/len(responses) > .5) else False


class ESXiCheck:
    host = None
    user = None
    password = None

    def __init__(self, host, config):
        self.host = host
        self.user = config['username']
        self.password = config['password']


    def __run_process(self, script, args):
        command = ["python3", script] + args
        logging.debug(command)
        # run process, pipe all output
        output = subprocess.run(command, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return output

    def check_host(self):
        result = []

        # common args, minus the -t value
        esxi_checks = {"VM Status": "vms", "Datastores": "datastore", "Host Status": "status"}
        common_args = ["-H", self.host, "-U", self.user, "-P", self.password, "-p", "443", "-c", "90", "-w", "85", "-t"]

        # run the subprocess for each type of check
        for aKey in esxi_checks.keys():
            args = common_args + [esxi_checks[aKey]]
            output = self.__run_process(os.path.join(utils.DIR_PATH, "check_scripts", "check_esxi.py"), args)

            result.append({"return_code": output.returncode, "text": output.stdout, "name": aKey})

            time.sleep(2)  # sleep 2 seconds between checks

        return result


class HostMonitor:
    hosts = None
    types = {"esxi"}

    def __init__(self, file):
        self.hosts = utils.read_json(file)

    def check_hosts(self):
        result = []
        ping = PingCheck()

        for aHost in self.hosts['hosts']:
            services = []

            # check if the host can be pinged
            canSee = ping.check_host(aHost['ip'])
            logging.debug(f"{aHost['name']}: Alive {canSee}")

            # check if there are any other services we should pull in
            if(canSee and aHost['type'] in self.types):
                services.append({"name": "Alive", "return_code": 0, "text": "Ping successfull!"})

                if(aHost['type'] == 'esxi'):
                    checker = ESXiCheck(aHost['ip'], aHost['config'])
                    services = services + checker.check_host()
            else:
                services.append({"name": "Alive", "return_code": 2, "text": "Ping failed"})

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
