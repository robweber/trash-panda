from .. device import DRDevice


class SwitchDevice(DRDevice):

    def __init__(self, name, address, config):
        super().__init__(name, address, "switch")

        self.info = "This device type will work with Cisco branded switches. SNMP information must be correct and setup on the switch for services to properly be queried."

    def _custom_checks(self):
        return []

    def _get_services(self):
        return ["Uptime"]
