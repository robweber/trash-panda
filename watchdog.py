"""
The watchdog is meant to check if the trash panda service is running and trigger a notification if it is not.
Best practice would be to set this up on a cron schedule within the running OS. The up/down check uses the web service
/api/health endpoint to determine if the monitoring system is running.

The watchdog does need to read in the same configuration file information as the main dashboard process so that notifications will work properly.
The port of the web service should also be given.
Unlike the main program the watchdog does not need root priveledges to run.

python3 watchdog.py -c /path/to/config.yaml -p 5000

For a list of arguments use:

python3 watchdog.py -h

"""
import argparse
import datetime
import json
import logging
import os.path
import requests
import sys
import modules.utils as utils
from modules.notifications import NotificationGroup


# parse the CLI args
parser = argparse.ArgumentParser(description='Trash Panda Watchdog')
parser.add_argument('-c', '--config', required=False,
                    help="Path to the config file, notifications will be sent if given")
parser.add_argument('-p', '--port', default=5000,
                    help="Port number the web server runs on, %(default)d by default")
parser.add_argument('-H', '--host', default="localhost",
                    help="Host running the web service, %(default)s by default")
parser.add_argument('-D', '--debug', action='store_true',
                    help='If the program should run in debug mode')

args = parser.parse_args()

# setup the logger
logLevel = 'INFO' if not args.debug else 'DEBUG'
logHandlers = [logging.StreamHandler(sys.stdout)]
logging.basicConfig(format="%(message)s",
                    level=getattr(logging, logLevel),
                    handlers=logHandlers)

# check if the service is running
service_url = f"http://{args.host}:{args.port}/api/health"
return_code = 0
try:
    response = requests.get(service_url)

    if(response.status_code == 200):
        # attempt to load results
        result = json.loads(response.text)

        if('return_code' not in result or result['return_code'] > 0):
            return_code = 2
    else:
        return_code = 2

except Exception as e:
    # any error set return code to Critical
    logging.error(e)
    return_code = 2

if(return_code == 0):
    logging.info("Trash Panda is running normally")
else:
    logging.info("Trash Panda is down")

# attempt to send notifications if configured
if(args.config and return_code > 0 and not os.path.exists(utils.WATCHDOG_FILE)):
    # load the config file
    yaml_check = utils.load_config_file(args.config)

    if(yaml_check['valid']):
        yaml_file = yaml_check['yaml']
    else:
        logging.error("Error reading configuration file")
        logging.error(yaml_check['errors'])
        sys.exit(return_code)

    # create the notifier, if defined
    if('notifications' in yaml_file['config']):
        notify = NotificationGroup(yaml_file['config']['notifications']['primary'],
                                   yaml_file['config']['notifications']['types'])

        # notify the host, expects a host dict
        notify.notify_host({"name": "Trash Panda"}, return_code)
        utils.write_file(utils.WATCHDOG_FILE, datetime.datetime.now())

# exit
sys.exit(return_code)
