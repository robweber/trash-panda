import datetime
import json
import redis
import modules.utils as utils
from enum import Enum


class HostHistory:
    """ Encapulates reading/writing to the Redis database"""

    db = None

    def __init__(self, db_host):
        self.db = redis.Redis(db_host, decode_responses=True)

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

    def list_groups(self):
        # get all the group names
        groups = self.__read_db_json(DBQueries.GET_GROUP_NAMES.value)

        # only return unique set
        return list(set(groups))

    def get_hosts(self):
        """ returns all host information from the database """
        all_hosts = self.__read_db_json("$[*]")

        for i in range(0, len(all_hosts)):
            all_hosts[i].pop("services")

        return all_hosts

    def get_group(self, group_name):
        """ get all hosts assigned to a given group

        :param group_name: a valid group name

        :returns: a list containing each host as a dictionary object
        """

        group = self.__read_db_json(DBQueries.GET_GROUP.value.format(group_name=group_name))

        # remove service info
        for i in range(0, len(group)):
            group[i].pop("services")

        return group

    def get_tags(self, type):
        result = []

        if(type == 'host'):
            tags = self.__read_db_json(DBQueries.GET_HOST_TAG_IDS.value)
        else:
            tags = self.__read_db_json(DBQueries.GET_SERVICE_TAG_IDS.value)

        # flatten the array
        result = [t for h_tags in tags for t in h_tags]

        # return unique set
        return list(set(result))

    def get_host(self, host_id):
        """ get host information from the database based on the ID

        :param host_id: a valid host

        :returns: a dict with the host information, empty if not found
        """
        host = self.__read_db_json(DBQueries.GET_HOST.value.format(host_id=host_id))

        if(not host):
            host = [{}]

        return host[0]

    def get_host_tag(self, tag_id):
        """ finds hosts matching the given tag id

        :param tag_id: the id of the tag to lookup

        :returns: list of hosts that include this tag
        """

        # get list of services matching this tag id
        result = {"id": tag_id}
        result['members'] = self.__read_db_json(DBQueries.GET_HOST_TAG.value.format(tag_id=tag_id))

        # remove service info
        for i in range(0, len(result['members'])):
            result['members'][i].pop("services")

        return result

    def get_service_tag(self, tag_id):
        """ finds services matching the given tag id

        :param tag_id: the id of the tag to lookup

        :returns: list of services that include this tag
        """

        # get list of services matching this tag id
        result = {"id": tag_id}
        result['members'] = self.__read_db_json(DBQueries.GET_SERVICE_TAG.value.format(tag_id=tag_id))

        return result

    def get_services(self, return_codes=[0], service_filter=".*"):
        """ returns a list of services where the status is one of the the given return_codes
        AND the id matches the given service filter

        :param return_codes: list of return codes to find as an array
        :param service_filter: service_id syntax to match - this is a regular expression

        :returns: list of services that meet these criteria
        """

        # turn the list into a JPath query ()
        query = " || ".join([f"@.return_code == {r}" for r in return_codes])

        return self.__read_db_json(DBQueries.GET_SERVICES_BY_QUERY.value.format(return_codes=query, service_regex=service_filter))

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
            result['unix_times'].append(d[0] / 1000)
            result['times'].append(datetime.datetime.fromtimestamp(d[0] / 1000).strftime("%m/%d/%y %H:%M:%S"))
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
            old_hosts = list(set(all_hosts) - set(host_ids))

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

    def consume_queued_actions(self):
        """ load any actions queued in the database and reset the queue to 0 """
        result = self.__read_db(DBKeys.QUEUED_ACTIONS.value)

        self.__write_db(DBKeys.QUEUED_ACTIONS.value, {})

        return result

    def check_host_now(self, host_id):
        """sets the next check time on the host to now, forcing a check

        :param host_id: a valid host id
        """
        action_obj = {'next_check': datetime.datetime.now().strftime(utils.TIME_FORMAT),
                      "action": "check_now"}

        # load queued actions
        queue = self.__read_db(DBKeys.QUEUED_ACTIONS.value)

        # update queue or add new list
        if(host_id in queue):
            queue[host_id].append(action_obj)
        else:
            queue[host_id] = [action_obj]

        self.__write_db(DBKeys.QUEUED_ACTIONS.value, queue)

        return {"success": True, "next_check": action_obj['next_check']}

    def silence_host(self, host_id, minutes):
        """sets the silenced property on a host which will expire from the current time
        plus the number of minutes indicated

        :param host_id: a valid host id
        :param minutes: the number of minutes the host will be silenced
        """
        until = datetime.datetime.now() + datetime.timedelta(minutes=int(minutes))
        action_obj = {'action': 'silence',
                      'until': until.strftime(utils.TIME_FORMAT)}

        # load queued actions
        queue = self.__read_db(DBKeys.QUEUED_ACTIONS.value)

        # update queue or add new list
        if(host_id in queue):
            queue[host_id].append(action_obj)
        else:
            queue[host_id] = [action_obj]

        self.__write_db(DBKeys.QUEUED_ACTIONS.value, queue)

        return {"success": True, 'is_silenced': True, 'until': action_obj['until']}

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
        """ write a value to the Redis DB as a JSON String"""
        self.db.set(db_key, json.dumps(db_value))


class DBKeys(Enum):
    """Enum that holds the keys for Redis data lookups"""
    HOST_KEY = 'hosts'
    LAST_CHECK = "last_check_timestamp"
    QUEUED_ACTIONS = "queued_actions"


class DBQueries(Enum):
    """Enum that holds keys for JSON Queries"""
    GET_HOST_IDS = '$[*].id'
    GET_HOST_TAG_IDS = '$[*].tags'
    GET_SERVICE_TAG_IDS = '$[*].services[*].tags'
    GET_GROUP_NAMES = '$[*].group'
    GET_HOST = '$[?(@.id=="{host_id}")]'
    GET_HOST_TAG = '$[?(@.tags[*]=="{tag_id}")]'
    GET_GROUP = '$[?(@.group=="{group_name}")]'
    GET_SERVICE = '$[*].services[?(@.id=="{service_id}")]'
    GET_SERVICE_TAG = '$[*].services[?(@.tags[*]=="{tag_id}")]'
    GET_SERVICES_BY_QUERY = '$[*].services[?(({return_codes}) && @.id=~"{service_regex}")]'
