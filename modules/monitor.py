import logging
import modules.utils as utils
from pythonping import ping


class PingCheck:
    count = 5  # number of ping requests to make

    def __init__(self, count=5):
        self.count = count

    def check_host(self, ip):
        responses = ping(ip, verbose=False, count=self.count)

        # get total of "success" responses
        total = list(filter(lambda x: x.success == True, responses))

        # if over 50% responded return True
        return True if (len(total)/len(responses) > .5) else False


class HostMonitor:
    hosts = None

    def __init__(self, file):
        self.hosts = utils.read_json(file)

    def check_hosts(self):
        result = []
        ping = PingCheck()

        for aHost in self.hosts['hosts']:
            canSee = ping.check_host(aHost['ip'])
            logging.debug(f"{aHost['name']}: {canSee}")
            aHost['status'] = canSee
            result.append(aHost)

        return result
