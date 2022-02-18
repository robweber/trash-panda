from .. device import DRDevice


class GenericDevice(DRDevice):
    """
    Represents a generic network device, only alive status supported
    """

    def __init__(self, name, address):
        super().__init__(name, address, "generic")

        self.info = ("This is a generic network device that checks up/down status only. No services exposed or available.")

    def _custom_checks(self):
        result = []

        return result

    def _get_services(self):
        return []
