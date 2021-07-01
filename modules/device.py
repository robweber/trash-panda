import logging
import subprocess

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
