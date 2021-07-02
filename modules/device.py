import logging
import subprocess
from pythonping import ping


class DRDevice:
    name = None
    address = None
    type = None
    info = ""

    def __init__(self, name, address, type):
        self.name = name
        self.address = address
        self.type = type

    def _ping(self):
        responses = ping(self.address, verbose=False, count=5)

        # get total of "success" responses
        total = list(filter(lambda x: x.success == True, responses))

        # if over 50% responded return True
        return True if (len(total)/len(responses) > .5) else False

    # executes a subprocess (python script) and returns the results
    def _run_process(self, script, args):
        command = ["python3", script] + args
        logging.debug(command)
        # run process, pipe all output
        output = subprocess.run(command, encoding="utf-8", stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return output

    def _make_service(self, name, return_code, text):
        return {"name": name, "return_code": return_code, "text": text}

    # implementing classes will override, should return an array
    def _custom_checks(self):
        raise NotImplementedError

    def _get_services(self):
        raise NotImplementedError

    def check_host(self):
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
        result = None
        commands = self.get_commands()

        for c in commands:
            if(c['command'] == id):
                result = c

        return result

    # return a JSON formatted list of commands this device supports, if any
    def get_commands(self):
        return {}

    # return the name of all services for this device
    def get_services(self):
        return ["Alive"] + self._get_services()

    def run_command(self, command):
        raise NotImplementedError
