import os
import time
import modules.utils as utils
from .. device import DRDevice


class ESXiDevice(DRDevice):
    """
    Represents a stand alone ESXi host.
    """
    user = None
    password = None

    def __init__(self, name, address, config):
        super().__init__(name, address, "esxi")
        self.user = config['username']
        self.password = config['password']

        self.info = ("This device type works with stand alone ESXi devices. Username and password information "
                     "for a local user with admin permissions must be set for queries and commands to function.")

    def _custom_checks(self):
        result = []

        # common args, minus the -t value
        esxi_checks = {"VM Status": "vms", "Datastores": "datastore", "Host Status": "status"}
        common_args = ["-H", self.address, "-U", self.user, "-P", self.password,
                       "-p", "443", "-c", "90", "-w", "85", "-t"]

        # run the subprocess for each type of check
        for aKey in esxi_checks.keys():
            args = common_args + [esxi_checks[aKey]]
            output = self._run_python(os.path.join(utils.DIR_PATH, "check_scripts", "check_esxi.py"), args)

            result.append(self._make_service(aKey, output.returncode, output.stdout))

            time.sleep(2)  # sleep 2 seconds between checks

        return result

    def _get_services(self):
        return ["Datastores", "Host Status", "VM Status"]

    def get_commands(self):
        result = []

        result.append({"name": "Shutdown VMs", "type": "button", "command": "shutdown_vms"})

        return result

    def run_command(self, command):
        for i in range(0, 4):
            time.sleep(15)
