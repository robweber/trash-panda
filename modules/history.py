import datetime
import json
import redis
from enum import Enum
from slugify import slugify


class HostHistory:
    """ Encapulates reading/writing to the Redis database"""

    db = None

    def __init__(self):
        self.db = redis.Redis('127.0.0.1', decode_responses=True)

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
        return self.__read_db_json(DBQueries.GET_HOST_IDS.value)

    def list_tags(self):
        all_tags = self.__read_db_json(DBQueries.GET_TAG_IDS.value)

        # flatten down to unique names
        reduced = [y for x in all_tags for y in x]

        # convert to dict in form {id: name}
        tags = {slugify(x): x for x in list(set(reduced))}

        return tags

    def get_hosts(self):
        """ returns all host information from the database """
        all_hosts = self.__read_db_json("$[*]")

        for i in range(0, len(all_hosts)):
            all_hosts[i].pop("services")

        return all_hosts

    def get_host(self, host_id):
        """ get host information from the database based on the ID

        :param host_id: a valid host

        :returns: a dict with the host information, empty if not found
        """
        host = self.__read_db_json(DBQueries.GET_HOST.value.format(host_id=host_id))

        if(not host):
            host = [{}]

        return host[0]

    def get_tag(self, tag_id):
        """ finds services matching the given tag id

        :param tag_id: the id of the tag to lookup

        :returns: list of services that include this tag
        """
        # get a list of all tags
        all_tags = self.list_tags()

        # get list of services matching this tag id
        result = {"id": tag_id, "name": all_tags[tag_id]}
        result['services'] = self.__read_db_json(DBQueries.GET_TAG.value.format(tag_id=all_tags[tag_id]))

        return result

    def get_services(self, return_codes=[0]):
        """ returns a list of services where the status is one of the the given return_codes """

        # turn the list into a JPath query ()
        query = " || ".join([f"@.return_code == {r}" for r in return_codes])

        return self.__read_db_json(DBQueries.GET_SERVICES_BY_STATUS.value.format(return_codes=query))

    def get_service(self, service_id):
        """ get information on a specific service from a specific host

        :param service_id: a valid service id

        :returns: a dict with the service information, empty if not found
        """
        service = self.__read_db_json(DBQueries.GET_SERVICE.value.format(service_id=service_id))

        if(not service):
            service = [{}]

        return service[0]

    def get_ts_data(self, key, start, end):
        result = {"times": [], "values": [], 'unix_times': []}

        # turn seconds into milliseconds
        ts_data = self.db.ts().range(key, start * 1000, end * 1000)

        for d in ts_data:
            result['unix_times'].append(d[0]/1000)
            result['times'].append(datetime.datetime.fromtimestamp(d[0]/1000).strftime("%m/%d/%y %H:%M:%S"))
            result['values'].append(d[1])

        return result

    def set_hosts(self, host_ids):
        """ takes a list of host names and compares against the DB,
        ids that do not exist are deleted - should be run at on startup

        :param host_ids: list of host ids from the config
        """
        # get a list of all hosts in DB
        all_hosts = self.list_hosts()

        if(all_hosts is None):
            # probably the first run
            self.__write_db_json("$", [])
        else:
            # get items that are not in current list
            old_hosts = list(set(all_hosts)-set(host_ids))

            # delete the old hosts
            for host_id in old_hosts:
                self.db.json().delete(DBKeys.HOST_KEY.value, DBQueries.GET_HOST.value.format(host_id=host_id))

    def save_host(self, host_id, host_status, update_perf_data=True):
        """ saves the host status to the database with the given ID

        :param host_id: a valid host id
        :param host_status: the host's status as a dict
        """

        # delete the old value
        self.db.json().delete(DBKeys.HOST_KEY.value, DBQueries.GET_HOST.value.format(host_id=host_id))

        # add the new value https://redis.io/docs/latest/commands/json.arrappend/
        self.db.json().arrappend(DBKeys.HOST_KEY.value, "$", host_status)

        if(update_perf_data):
            # save perf data
            for s in host_status['services']:
                unix_time = int(datetime.datetime.timestamp(datetime.datetime.strptime(host_status['last_check'], "%m-%d-%Y %I:%M%p")))

                # make sure perf data exists
                if('perf_data' in s):
                    for p in s['perf_data']:
                        if(not self.__exists(p['id'])):
                            # save for 30 days
                            self.db.ts().create(p['id'], retention_msecs=(86400000 * 30))

                        # add the value
                        self.db.ts().add(p['id'], unix_time * 1000, p['value'])

    def __exists(self, key):
        return self.db.exists(key) > 0

    def __read_db_json(self, query):
        """ read a value from the DB using the JSON Module - https://redis.io/docs/latest/commands/json.get/
        queries can be done as supported with JSON Paths - https://redis.io/docs/latest/develop/data-types/json/path/
        """
        result = self.db.json().get(DBKeys.HOST_KEY.value, query)

        return result

    def __write_db_json(self, db_filter, db_value):
        """ write an object to the DB using the JSON module"""
        self.db.json().set(DBKeys.HOST_KEY.value, db_filter, db_value)

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
    HOST_KEY = 'hosts'
    LAST_CHECK = "last_check_timestamp"


class DBQueries(Enum):
    """Enum that holds keys for JSON Queries"""
    GET_HOST_IDS = '$[*].id'
    GET_TAG_IDS = '$[*].services[*].tags'
    GET_HOST = '$[?(@.id=="{host_id}")]'
    GET_SERVICE = '$[*].services[?(@.id=="{service_id}")]'
    GET_TAG = '$[*].services[?(@.tags[*]=="{tag_id}")]'
    GET_SERVICES_BY_STATUS = "$[*].services[?({return_codes})]"
