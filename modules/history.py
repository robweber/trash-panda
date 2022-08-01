import json
import redis
from enum import Enum


class HostHistory:
    db = None

    def __init__(self):
        self.db = redis.Redis('localhost', decode_responses=True)

    def list_hosts(self):
        return self.__read_db(DBKeys.VALID_HOSTS.value)

    def get_host(self, host_id):
        """ get host information from the database based on the ID

        :param host_id: a valid host

        :returns: a dict with the host information, empty if not found
        """
        return self.__read_db(f"{DBKeys.HOST_STATUS.value}.{host_id}")

    def set_hosts(self, names):
        """ saves a list of valid host names """
        self.__write_db(DBKeys.VALID_HOSTS.value, names)

    def save_host(self, host_id, host_status):
        """ saves the host status to the database with the given ID

        :param host_id: a valid host id
        :param host_status: the host's status as a dict
        """

        self.__write_db(f"{DBKeys.HOST_STATUS.value}.{host_id}", host_status)

    def reset(self):
        """ resets host data in the database """
        self.__write_db(DBKeys.VALID_HOSTS.value, [])

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
