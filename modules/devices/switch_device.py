from .. device import DRDevice


class SwitchDevice(DRDevice):

    def __init__(self, name, address, config):
        super().__init__(name, address, "switch")


    def _custom_checks(self):
        return []
