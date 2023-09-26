import logging
import smtplib
import ssl
import modules.utils as utils
from pushover import Client
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


class NotificationGroup:
    """Contains a group of notification objects that can be triggered all at once"""
    default = "all"
    notifiers = {}

    def __init__(self, default_type, notify_types):
        """notify_types should be a list of notification types from the config"""

        # the type to use if none is given
        self.default = default_type
        logging.info(f"Default notification type is: {self.default}")

        # go through the list and create each notifier
        for n in notify_types:
            self.notifiers[n['type']] = self.__create_notifier(n)

    def __create_notifier(self, notifier):
        """Create a notifier class using the given config"""
        result = None

        if(notifier['type'] == 'log'):
            result = LogNotification(notifier['args'])
        elif(notifier['type'] == 'pushover'):
            result = PushoverNotification(notifier['args'])
        elif(notifier['type'] == 'email'):
            result = EmailNotification(notifier['args'])

        return result

    def __get_notify_group(self, type=None):
        """Find the notification group based on the type given

        returns: list of matching notifiers
        """
        if(type is None):
            type = self.default

        if(type == 'all'):
            # special case for using all types
            return self.notifiers.values()
        elif(type == 'none'):
            # special case, return blank list
            return []
        else:
            # use only the type specified
            return [self.notifiers[type]]

    def notify_host(self, host, status):

        # determine the type
        type = host['notifier'] if 'notifier' in host else self.default

        # send to any notifier in this group
        for n in self.__get_notify_group(type):
            n.notify_host(host, status)

    def notify_service(self, host, service):

        # determine the type
        type = service['notifier'] if 'notifier' in service else (host['notifier'] if 'notifier' in host else self.default)

        for n in self.__get_notify_group(type):
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
        message = f"{host['name']} is {status_msg}"

        self._send_message(message)

    def notify_service(self, host, service):
        """Create a service message from the host and service information and pass along
        to the implementing class via the _send_message() function
        """
        # create the message
        message = f"{service['name']} on host {host['name']} is {utils.SERVICE_STATUSES[service['return_code']]}"

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

    Custom config:
    * application key
    * user identifiction key
    """
    client = None

    def __init__(self, args):
        super().__init__('pushover')

        self.client = Client(args['user_key'], api_token=args['api_key'])

    def _send_message(self, message):
        self.client.send_message(message, title="Monitoring Notification")


class EmailNotification(MonitorNotification):
    """Sends notifications using built-in Python SMTP classes

    Custom Config:
    * server
    * port (default 25)
    * secure
    * username (if secure)
    * password (if secure)
    * sender
    * recipient
    """

    smtp_args = {}

    def __init__(self, args):
        super().__init__('email')
        self.smtp_args = args

        if('port' not in self.smtp_args):
            self.smtp_args['port'] = 25

    def _send_message(self, message):
        # generate both a text and html message
        email = MIMEMultipart("alternative")
        email["Subject"] = "Monitoring Notification"

        html = f"<html><body><p>{ message }</p></body></html>"

        email.attach(MIMEText(message, "plain"))
        email.attach(MIMEText(html, "html"))

        if(self.smtp_args['secure']):
            # Create a secure SSL context
            context = ssl.create_default_context()

            with smtplib.SMTP_SSL(self.smtp_args['server'], self.smtp_args['port'], context=context) as server:
                server.login(self.smtp_args['username'], self.smtp_args['password'])
                server.sendmail(self.smtp_args['sender'], self.smtp_args['recipient'], email.as_string())
        else:
            with smtplib.SMTP() as server:
                server.sendmail(self.smtp_args['sender'], self.smtp_args['recipient'], email.as_string())
