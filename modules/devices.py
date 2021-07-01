import logging
import os
import subprocess
import time
import modules.utils as utils


class DRDevice:
    name = None
    address = None
    type = None

    def __init__(self, name, address, type):
        self.name = name
        self.address = address
        self.type = type

    # executes a subprocess (python script) and returns the results
    def _run_process(self, script, args):
        command = ["python3", script] + args
        logging.debug(command)
        # run process, pipe all output
        output = subprocess.run(command, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return output

    # implementing classes will override
    def check_host(self):
        raise NotImplementedError

class ESXiDevice(DRDevice):
    user = None
    password = None

    def __init__(self, name, address, config):
        super().__init__(name, address, "esxi")
        self.user = config['username']
        self.password = config['password']


    def check_host(self):
        result = []

        # common args, minus the -t value
        esxi_checks = {"VM Status": "vms", "Datastores": "datastore", "Host Status": "status"}
        common_args = ["-H", self.address, "-U", self.user, "-P", self.password, "-p", "443", "-c", "90", "-w", "85", "-t"]

        # run the subprocess for each type of check
        for aKey in esxi_checks.keys():
            args = common_args + [esxi_checks[aKey]]
            output = self._run_process(os.path.join(utils.DIR_PATH, "check_scripts", "check_esxi.py"), args)

            result.append({"return_code": output.returncode, "text": output.stdout, "name": aKey})

            time.sleep(2)  # sleep 2 seconds between checks

        return result
