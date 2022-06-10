""""
Checks the status of a MythTV install by getting the status and parsing the returned xml

Current types of checks available are:
tuner - checks the status of each tuner

"""
import argparse
import requests
import sys
import xml.dom.minidom

TUNER_STATES = ("Idle", "Watching Live TV", "Watching Recorded", "Watching Recording",
                "Watching DVD", "Recording", "Recording", "Recording", "Recording")


def get_single_element(name, element):
    """Returns a single child element with the tag name specified from this parent"""
    element_list = element.getElementsByTagName(name)

    return element_list[0]


# parse the arguments
parser = argparse.ArgumentParser()
parser.add_argument('-H', '--host', required=True, help='MythTV address or hostname')
parser.add_argument('-p', '--port', default=6544, help='MythTV port, default is 6544')
parser.add_argument('-t', '--type', default="tuner", choices=("tuner", "guide", "storage"),
                    help='The type of check to run, options are: tuner, guide, and storage')
parser.add_argument('-w', '--warning', type=int, help='Warning value, required for guide check')
parser.add_argument('-c', '--critical', type=int, help='Critical value, required for guide check')

args = parser.parse_args()

status = None
try:
    # pull in the site
    response = requests.get(f"http://{args.host}:{args.port}/Status/GetStatus")

    # parse the xml
    doc = xml.dom.minidom.parseString(response.text)
    status = doc.documentElement

except Exception:
    # there was a problem, print error and exit critical
    print(f"MythTV could not be contacted at {args.host}")
    sys.exit(2)


result = 0
if(args.type == 'tuner'):
    # get some information about each tuner
    for enc in status.getElementsByTagName('Encoder'):
        print(f"Tuner {enc.getAttribute('devlabel')} is {TUNER_STATES[int(enc.getAttribute('state'))]}")
elif(args.type == 'guide'):
    # check the number of guide days avaiable
    machineInfo = get_single_element('MachineInfo', status)
    guide = get_single_element('Guide', machineInfo)

    guide_days = int(guide.getAttribute('guideDays'))

    if(guide_days < args.warning):
        result = 1
    elif(guide_days < args.critical):
        result = 2

    print(f"There are {guide_days} guide days available")
elif(args.type == 'storage'):
    # check available disk storage
    machineInfo = get_single_element('MachineInfo', status)
    storage = get_single_element('Storage', machineInfo)

    # this first node is the liveTV node with the total
    firstGroup = get_single_element('Group', storage)

    # get the total available after expirations
    free_space = int(firstGroup.getAttribute('free'))
    deleted = int(firstGroup.getAttribute('deleted'))
    expirable = int(firstGroup.getAttribute('expirable'))
    total = free_space + deleted + expirable  # the free space + reclaimed

    if(total < args.warning):
        result = 1
    elif(total < args.critical):
        result = 2

    print(f"{total} MB available after auto-expire")

sys.exit(result)
