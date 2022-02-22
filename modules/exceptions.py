class ServiceNotFoundError(Exception):

    def __init__(self, service_name):
        super().__init__(f"There is no definition for service: {service_name}")

class ConfigValueMissingError(Exception):

    def __init__(self, config_value, type):
        super().__init__(f"A config value ({config_value}) is missing but required for device type {type}")
