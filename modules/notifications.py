import logging
import modules.utils as utils
from pushover import Client


class NotificationGroup:
    """Contains a group of notification objects that can be triggered all at once"""
    notifiers = []

    def __init__(self, notify_types):
        """notify_types should be a list of notification types from the config"""
        # go through the list and create each notifier
        for n in notify_types:
            self.notifiers.append(self.__create_notifier(n))

    def __create_notifier(self, notifier):
        """Create a notifier class using the given config"""
        result = None

        if(notifier['type'] == 'log'):
            result = LogNotification(notifier['args'])
        elif(notifier['type'] == 'pushover'):
            result = PushoverNotification(notifier['args'])

        return result

    def notify_host(self, host, status):
        for n in self.notifiers:
            n.notify_host(host, status)

    def notify_service(self, host, service):
        for n in self.notifiers:
            n.notify_service(host, service)


class MonitorNotification:
    """Abstract class for sending notifications about service changes
    Implementing classes will implement the logic of actually sending a message through
    a notification channel
    """
    name = None

    def __init__(self, name):
        self.name = name
        logging.debug(f"Creating notifier: {name} notifier")

    def _send_message(self, message):
        """Child classes will implement this to actually send a message"""
        raise NotImplementedError

    def notify_host(self, host, status):
        """Create a service message from the host and service information and pass along
        to the implementing class via the _send_message() function
        """
        # create the message
        status_msg = "Up" if status == 0 else "Down"
        message = f"{host} is {status_msg}"

        self._send_message(message)

    def notify_service(self, host, service):
        """Create a service message from the host and service information and pass along
        to the implementing class via the _send_message() function
        """
        # create the message
        message = f"{service['name']} on host {host} is {utils.SERVICE_STATUSES[service['return_code']]}"

        # send message
        self._send_message(message)


class LogNotification(MonitorNotification):
    """Logs all notifications to the application log. A custom log file location
    can also be specified.

    Custom config:
    * path - path to where a custom log file should go
    * propagate - if log messages should be in both the root and custom log (default True)
    """
    notify_logger = None

    def __init__(self, args):
        super().__init__('log')

        # create the logger and specify the log location
        self.notify_logger = logging.getLogger("trash-panda-notify")

        # if a custom file path is given
        if('path' in args):
            logging.info(f"Setting notification log to {args['path']}")

            file_handler = logging.FileHandler(args['path'])
            file_handler.setFormatter(logging.Formatter(fmt="%(asctime)s: %(message)s", datefmt="%Y-%m-%d %H:%M"))
            self.notify_logger.addHandler(file_handler)

            self.notify_logger.propagate = args['propagate'] if 'propagate' in args else True

    def _send_message(self, message):
        self.notify_logger.info(f"Notification: {message}")


class PushoverNotification(MonitorNotification):
    """Sends notification messages through the Pushover messenger service
    https://pushover.net/
    https://pypi.org/project/python-pushover/

    Both application and user identification keys are needed
    """
    client = None

    def __init__(self, args):
        super().__init__('pushover')

        self.client = Client(args['user_key'], api_token=args['api_key'])

    def _send_message(self, message):
        self.client.send_message(message, title="Monitoring Notification")
