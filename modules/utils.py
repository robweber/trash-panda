"""
utils.py

Utility functions and variables for global use

"""
import json
import logging
import os

# full path to the running directory of the program
DIR_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


# read JSON formatted file
def read_json(file):
    result = {}

    try:
        result = json.loads(read_file(file))
    except Exception:
        logging.error(f"error parsing json from file {file}")

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
