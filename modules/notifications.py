import logging


def create_notifier(notifier):
    """Create a notifier class using the given config"""
    result = None

    if(notifier['type'] == 'log'):
        result = LogNotification(notifier['args'])

    return result


class MonitorNotification:
    """Abstract class for sending notifications about service changes
    Implementing classes will implement the logic of actually sending a message through
    a notification channel
    """
    STATUSES = ["OK", "Warning", "Critical"]
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
        message = f"{service['name']} on host {host} is {self.STATUSES[service['return_code']]}"

        # send message
        self._send_message(message)


class LogNotification(MonitorNotification):
    """Logs all notification methods using the logging.info() function"""
    def __init__(self, args):
        super().__init__('log')

    def _send_message(self, message):
        logging.info(f"Notification: {message}")
