import os
import modules.utils as utils
from .. device import DRDevice


class SwitchDevice(DRDevice):
    """
    Represents a generic network switch
    """
    community = None

    def __init__(self, name, address, config):
        super().__init__(name, address, "switch")

        self.community = config['community']

        self.icon = "router-network"
        self.info = ("This device type will work with generic managed switches. SNMP information must be correct "
                     "and setup on the switch for services to properly be queried.")

    def _custom_checks(self):
        result = []

        # basic args all scripts need
        args = ["-H", self.address, "-c", self.community]

        # check system uptime
        output = self._run_python(os.path.join(utils.DIR_PATH, "check_scripts", "check_snmp.py"), args + ['-o', '1.3.6.1.2.1.1.3.0'])
        result.append(self._make_service("Switch Uptime", output.returncode, output.stdout))

        return result

    def _get_services(self):
        return ["Uptime"]
