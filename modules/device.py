import logging
import subprocess
from slugify import slugify
from pythonping import ping


class DRDevice:
    """
    Abstract device that represents a specific type of device.
    Subclasses must implement specific methods or NotImplementedErrors will throw at runtime.
    """
    name = None
    address = None
    type = None
    info = ""

    def __init__(self, name, address, type):
        self.name = name
        self.address = address
        self.type = type

    def _ping(self):
        """
        Will attempt to ping the IP address via ICMP and return True or False
        True will only return if 50% or more pings are responded to
        """
        responses = ping(self.address, verbose=False, count=5)

        # get total of "success" responses
        total = list(filter(lambda x: x.success is True, responses))

        # if over 50% responded return True
        return True if (len(total)/len(responses) > .5) else False

    # executes a subprocess (python script) and returns the results
    def _run_process(self, script, args):
        """
        Kicks off a subprocess to run the defined python script
        with the given arguments. Returns subprocess output.
        """
        command = ["python3", script] + args
        logging.debug(command)
        # run process, pipe all output
        output = subprocess.run(command, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return output

    def _make_service(self, name, return_code, text):
        """
        Helper method to take the name, return_code, and output and wrap
        it in a Dict.
        """
        return {"name": name, "return_code": return_code, "text": text, "id": slugify(name)}

    def _custom_checks(self):
        """
        Runs the checks on this host and return the results as an array of dicts in the format:
        {"name": "", "return_code": 0-3, "text": ""}
        The helper method _make_service() can be used to generate these.

        Implementing classes must override.
        """
        raise NotImplementedError

    def _get_services(self):
        """
        Returns a list of services this host will check.

        Implementing classes must override.
        """
        raise NotImplementedError

    def check_host(self):
        """
        Called to run the checks on this host. If the ping check fails all subsequent checks are skipped
        and a result listing them as Not Attempted (return code of 3) is used.
        """
        result = []

        if(self._ping()):
            logging.debug(f"{self.name}: Is Alive")

            # the host is alive, continue checks
            result = self._custom_checks()

            result.append(self._make_service("Alive", 0, "Ping successfull!"))
        else:
            logging.debug(f"{self.name}: Is Not Alive")

            # the host is not alive, set "unknown" for all other services
            for service in self._get_services():
                result.append(self._make_service(service, 3, "Not attempted"))

            result.append(self._make_service("Alive", 2, "Ping failed"))

        return result

    def find_command(self, id):
        """
        Returns the command object based on the given id
        """
        result = None
        commands = self.get_commands()

        for c in commands:
            if(c['command'] == id):
                result = c

        return result

    def get_commands(self):
        """
        Returns an array of commands this device supports, if any, in the following format
        {"name":"", "type": "", "command": ""}
        """
        return []

    def get_services(self):
        """
        Returns and array of all services this device will check
        """
        return ["Alive"] + self._get_services()

    def run_command(self, command):
        """
        Runs the given command, logging any output or errors

        Must be implemented, even if no commands valid for device.
        """
        raise NotImplementedError
