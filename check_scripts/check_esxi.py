"""check status of an ESXi server, requires pyVmomi"""
import atexit
import argparse
import sys
import datetime
import ssl
#https://github.com/vmware/pyvmomi
from pyVim import connect
from pyVmomi import vmodl
from pyVmomi import vim

#need this to supress any ssl warnings
import requests
requests.packages.urllib3.disable_warnings()

#for unverified certs
if hasattr(ssl,'_create_unverified_context'):
    ssl._create_default_https_context = ssl._create_unverified_context

OK=0
WARNING=1
CRITICAL=2
UNKNOWN=3


def get_args():

    parser = argparse.ArgumentParser(description="arguments for vcenter api checker")

    parser.add_argument('-p',"--port",required=True,type=int,help="Port of the vCenter service sdk")
    parser.add_argument('-U','--user',required=True,type=str,help='Username to connect to vCenter with')
    parser.add_argument('-P','--password',required=True,type=str,help='Password to connect to vCenter with')
    parser.add_argument('-H','--host',required=False,type=str,help='The host to get information about')
    parser.add_argument('-t','--type',required=True,type=str,help='The type of check (status|datastore|snapshot|vms)')
    parser.add_argument('-w','--warning',required=False,type=int,help='The warning value as a percent')
    parser.add_argument('-c','--critical',required=False,type=int,help='the critical value, as a percent')

    args = parser.parse_args()

    return args

def memory_usage(host,perfManager):
    metricId = vim.PerformanceManager.MetricId(counterId=6, instance="*")

    startTime = datetime.datetime.now() - datetime.timedelta(hours=1)
    endTime = datetime.datetime.now()

    query = vim.PerformanceManager.QuerySpec(maxSample=1,
                                                 entity=host,
                                                 metricId=[metricId],
                                                 startTime=startTime,
                                                 endTime=endTime)

    print(perfManager.QueryPerf(querySpec=[query]))

def overall_status(host):

    if(host.overallStatus == 'red'):
        print('Host status is critical')
        for alarm in host.triggeredAlarmState:
            print(alarm.alarm.info.name)

        sys.exit(CRITICAL)
    elif(host.overallStatus == 'yellow'):
        print('Host status at a warning state')
        for alarm in host.triggeredAlarmState:
            print(alarm.alarm.info.name)

        sys.exit(WARNING)
    else:
        print('Host is OK')
        sys.exit(OK)

def datastores(host,warn,crit):
    all_stores = []
    critical_stores = []
    warning_stores = []

    for aStore in host.datastore:
        #compute the disk usage
        used = (float(aStore.summary.capacity - aStore.summary.freeSpace) / aStore.summary.capacity) * 100

        all_stores.append(aStore.name + " " + str(used) + "%")

        if(used > crit):
            critical_stores.append(aStore.name + " " + str(used) + "%")
        elif(used > warn):
            warning_stores.append(aStore.name + " " + str(used) + "%")

    print('\n'.join(all_stores))
    if(len(critical_stores) > 0):
        sys.exit(CRITICAL)
    elif(len(warning_stores) > 0):
        sys.exit(WARNING)
    else:
        sys.exit(OK)

def snapshots(vmList,warn,crit):
    outOfDate = []
    now = datetime.datetime.now(UTC())

    for VM in vmList.view:
        #check if this vm has a snapshot
        print(VM)
        if(VM.snapshot != None):
            for aSnap in VM.snapshot.rootSnapshotList:
                #get the difference between these two days
                tdelta = now - aSnap.createTime

                if(tdelta.days >= crit):
                    outOfDate.append(VM.name + " - " + str(tdelta.days) + " days")

    if(len(outOfDate) > 0):
        print(outOfDate)
        sys.exit(CRITICAL)
    else:
        print("Snapshots OK")
        sys.exit(OK)

def list_vms(vmList):
    for VM in vmList.view:
        print(f"{VM.name} - {VM.runtime.powerState}")

def main():

    args = get_args()

    #connect to vCenter
    host = None
    service_instance = connect.SmartConnect(host=args.host,user=args.user,pwd=args.password,port=args.port)

    if not service_instance:
        print("Could not connect to ESXi host")
        sys.exit(-1)

    atexit.register(connect.Disconnect,service_instance)

    #get the content from vcenter
    content = service_instance.RetrieveContent()

    if(args.type == 'snapshot'):
        #get all vms
        all_vms = content.viewManager.CreateContainerView(content.rootFolder,[vim.VirtualMachine],True)

        snapshots(all_vms,args.warning,args.critical)
    elif(args.type == 'vms'):
        #get all vms
        all_vms = content.viewManager.CreateContainerView(content.rootFolder,[vim.VirtualMachine],True)

        list_vms(all_vms)
    else:

        if(content != None):
            if(args.type == 'status'):
                overall_status(content.rootFolder)
            elif(args.type == 'datastore'):
                datastores(content.rootFolder.childEntity[0],args.warning,args.critical)
        else:
            print("Host " + args.host + " cannot be found")
            sys.exit(CRITICAL)

class UTC(datetime.tzinfo):
    ZERO = datetime.timedelta(0)

    def utcoffset(self, dt):
        return self.ZERO
    def tzname(self, dt):
        return "UTC"
    def dst(self, dt):
        return self.ZERO

#run the program
if __name__ == "__main__":
    main()
