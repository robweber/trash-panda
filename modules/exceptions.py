class DeviceNotFoundError(Exception):
    """Exeption thrown when a device type definition is referenced but not found within a host config"""
    def __init__(self, device_name, type):
        super().__init__(f"There is no device type definition '{type}' referenced in host config for {device_name}")

class ServiceNotFoundError(Exception):
    """Exception thrown when a service definition is referenced but not found within a host config"""
    def __init__(self, service_name):
        super().__init__(f"There is no definition for service: {service_name}")


class ConfigValueMissingError(Exception):
    """Exception thrown when a configuration value is listed as required for a device type but missing from the host config"""
    def __init__(self, device_name, config_value, type):
        super().__init__(f"A config value ({config_value}) for device {device_name} is missing but required for device type {type}")
