"""
utils.py

Utility functions and variables for global use

"""
import json
import logging
import os
import yaml

# full path to the running directory of the program
DIR_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
NAGIOS_PATH = "/usr/lib/nagios/plugins/"

# Redis Keys
HOST_STATUS = "host_status"
COMMAND_TASK_ID = "command_task_id"


# read JSON formatted file
def read_json(file):
    result = {}

    try:
        result = json.loads(read_file(file))
    except Exception:
        logging.error(f"error parsing json from file {file}")

    return result


# read a YAML formatted file
def read_yaml(file):
    result = {}

    with open(file, 'r') as file:
        result = yaml.safe_load(file)

    return result


# read a key from the database, converting to dict
def read_db(db, db_key):
    result = {}

    if(db.exists(db_key)):
        result = json.loads(db.get(db_key))

    return result


# write a value to the datase, converting to JSON string
def write_db(db, db_key, db_value):
    db.set(db_key, json.dumps(db_value))


# write JSON to file
def write_json(file, data):
    write_file(file, json.dumps(data))


# read contents of a file
def read_file(file):
    result = ''
    try:
        with open(file) as f:
            result = f.read()
    except Exception:
        logging.error(f"error opening file {file}")

    return result


# write data to a file
def write_file(file, pos):
    try:
        with open(file, 'w') as f:
            f.write(str(pos))
    except Exception:
        logging.error('error writing file')
