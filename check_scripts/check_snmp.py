""""
Gets a single SNMP value from the given OID and returns it
Requires hnmp
"""


import argparse
import sys
from hnmp import SNMP, SNMPError

#parse the arguments
parser = argparse.ArgumentParser()
parser.add_argument('-H', '--host', required=True, help='The host address')
parser.add_argument('-c', '--community', required=True, help='The community string')
parser.add_argument('-o', '--oid', required=True, help='The oid to check')

args = parser.parse_args()

#setup the snmp object
snmp = SNMP(args.host, community=args.community)

try:
    output = snmp.get(args.oid)
    print(output)
except SNMPError:
    print(f"Could not reach server {args.host} or find given oid")
    sys.exit(1)
