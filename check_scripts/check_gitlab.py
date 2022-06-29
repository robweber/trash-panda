#!/usr/bin/env python
"""Check the health of a gitlab server instance using the /health_check.json status point. Make sure the IP is whitelisted
according to Gitlab's instructions:  https://docs.gitlab.com/ee/administration/monitoring/ip_allowlist.html"""
import argparse
import json
import sys
import requests


class Gitlab:
    hostname = None

    def __init__(self, hostname):
        self.hostname = hostname + '/health_check.json'

    def request(self):
        result = None

        try:
            response = requests.get(self.hostname)

            if(response.status_code == 200):
                result = json.loads(response.text)

        except Exception as e:
            print(e)
            pass

        return result


def main():
    parser = argparse.ArgumentParser(description='Checks GitLab Server using an API')
    parser.add_argument('-H', '--hostname', required=True, type=str, help='Hostname or IP address')

    args = parser.parse_args(sys.argv[1:])

    # run the status check
    gitlab = Gitlab(args.hostname)
    response = gitlab.request()

    if(response is not None):
        if(response['healthy']):
            print('GitLab is healthy')
            sys.exit(0)
        else:
            print(response['message'])
            sys.exit(2)
    else:
        print('Problem getting health from GitLab')
        sys.exit(2)


if __name__ == "__main__":
    main()
