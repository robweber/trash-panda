"""
utils.py

Utility functions and variables for global use

"""
import json
import logging
import markdown
import markdown.extensions.fenced_code
import os
import os.path
import yaml
from cerberus import Validator

# full path to the running directory of the program
DIR_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
NAGIOS_PATH = "/usr/lib/nagios/plugins/"
WATCHDOG_FILE = os.path.join(DIR_PATH, '.service_down')

# valid status descriptions
SERVICE_STATUSES = ["OK", "Warning", "Critical", "Unknown"]

# valid service state statuses
CONFIRMED_STATE = "CONFIRMED"
UNCONFIRMED_STATE = "UNCONFIRMED"

# allowed file types for web editor
ALLOWED_EDITOR_TYPES = ('.yaml', '.py', '.md')

# time format when converting datetime objects
TIME_FORMAT = "%m-%d-%Y %I:%M%p"


def custom_yaml_loader(loader, node):
    """custom YAML loader for !include syntax"""
    yaml_file = loader.construct_scalar(node)
    return read_yaml(os.path.join(DIR_PATH, yaml_file))


def load_config_file(file):
    """Load the YAML config file and validate it's structure
    errors in the file will be added to the result
    """
    result = {'valid': True}

    yaml.add_constructor('!include', custom_yaml_loader, Loader=yaml.SafeLoader)
    yaml_file = read_yaml(file)

    if(yaml_file):
        # validate the config file
        schema = read_yaml(os.path.join(DIR_PATH, 'install', 'schema.yaml'))
        v = Validator(schema)
        if(not v.validate(yaml_file, schema)):
            result['valid'] = False
            result['errors'] = str(v.errors)

        # normalize for missing values
        result['yaml'] = v.normalized(yaml_file)
    else:
        result['valid'] = False
        result['errors'] = 'Error parsing YAML file'

    return result


# load the markdown documenation, if it exists
def load_documentation(host_file):
    result = ""

    if(os.path.exists(host_file)):
        result = read_file(host_file)

    return markdown.markdown(result, extensions=['fenced_code'])


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

    try:
        with open(file, 'r') as f:
            result = yaml.safe_load(f)
    except Exception:
        logging.error(f"Error parsing YAML file {file}")

    return result


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
