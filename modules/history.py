import datetime
import json
import redis
import modules.utils as utils
from enum import Enum


class HostHistory:
    """ Encapulates reading/writing to the Redis database"""

    db = None

    def __init__(self):
        self.db = redis.Redis('localhost', decode_responses=True)

    def save_last_check(self):
        """sets the last check time using the current time as a unix timestamp"""
        now = datetime.datetime.now()

        self.__write_db(DBKeys.LAST_CHECK.value, datetime.datetime.timestamp(now))

    def get_last_check(self):
        """returns the last check time saved in the DB

        :returns: the last update time as a datetime object
        """
        last_update = datetime.datetime.fromtimestamp(self.__read_db(DBKeys.LAST_CHECK.value))

        return last_update

    def list_hosts(self):
        return self.__read_db(DBKeys.VALID_HOSTS.value)

    def get_host(self, host_id):
        """ get host information from the database based on the ID

        :param host_id: a valid host

        :returns: a dict with the host information, empty if not found
        """
        return self.__read_db(f"{DBKeys.HOST_STATUS.value}.{host_id}")

    def get_service(self, host_id, service_id):
        """ get information on a specific service from a specific host

        :param host_id: a valid host
        :param service_id: a valid service

        :returns: a dict with the service information, empty if not found
        """
        result = {}

        host = self.get_host(host_id)

        # find the service in the list
        if('services' in host):
            service_list = list(filter(lambda x: x['id'] == service_id, host['services']))

            # should only have one result
            if(len(service_list) > 0):
                result = service_list[0]

        return result

    def set_hosts(self, names):
        """ saves a list of valid host names """
        self.__write_db(DBKeys.VALID_HOSTS.value, names)

    def save_host(self, host_id, host_status):
        """ saves the host status to the database with the given ID

        :param host_id: a valid host id
        :param host_status: the host's status as a dict
        """

        self.__write_db(f"{DBKeys.HOST_STATUS.value}.{host_id}", host_status)

    def __read_db(self, db_key):
        """ read a value from the Redis DB based on the given key
        read values are returned as a JSON parsed value
        """
        result = {}

        if(self.db.exists(db_key)):
            result = json.loads(self.db.get(db_key))

        return result

    def __write_db(self, db_key, db_value):
        """ write a value to the Redis DB as  JSON String"""
        self.db.set(db_key, json.dumps(db_value))


class DBKeys(Enum):
    """Enum that holds the keys for Redis data lookups"""
    VALID_HOSTS = "host_names"
    HOST_STATUS = "host_status"
    LAST_CHECK = "last_check_timestamp"
