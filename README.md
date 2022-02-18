# Simple Monitoring

This is a _very_ basic monitoring solution meant for simple home use. It will monitor the status of some basic IP systems and services in a simple dashboard.

## Install

Install the repository according to the instructions in the [Install](install/Install.md) guide. Once this is done you can proceed to the Usage section.

### Usage

Before the program can be used hosts need to be configured in the `hosts.yaml` file created during the install. Detailed instructions for how to do this for different host types is below. Running the program must be done with `sudo` as root privileges are needed to bind to a socket. Once running the dashboard page will be available at `http://server_ip:5000/`. _Note the port may be different if you change it using the arguments below._

```
sudo python3 dashboard.py
```

You can also specify the `-c` flag to read in a config file instead of passing in arguments from the command line.

```
sudo python3 dashboard.py -c /path/to/config.conf
```

A full list of arguments can be found by using the `-h` flag.

```
python3 dashboard.py -h

usage: dashboard.py [-h] [-c CONFIG] [-f FILE] [-p PORT] [-i INTERVAL] [-D]

Simple Monitoring

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to custom config file
  -f FILE, --file FILE  Path to the config file for the host data,
                        conf/hosts.json by default
  -p PORT, --port PORT  Port number to run the web server on, 5000 by default
  -i INTERVAL, --interval INTERVAL
                        The monitoring system check interval, in minutes. 3 by
                        default
  -D, --debug           If the program should run in debug mode

```

## Dashboard

Once running the dashboard page can be loaded. The landing page will display all currently configured hosts and their overall status. If the host is down, or any configured service unavailable, the overall status will change. This page is refreshed every __15 seconds__. Data will change depending on the update interval set when the program is loaded.

Clicking on a host name will show you more information about that device. Individual services will be listed along with any output to indicate their current status. If configured, the management page for the host can also be launched from here.

### API

For integration with other systems the API can be used to pull in a JSON listing of all hosts and their statuses. This is available at: `http://server_ip:5000/api/status`. To decode the status return codes use the following:

* 0 - OK, everything normal
* 1 - Warning, potential problem
* 2 - Critical, definitely a problem

The status codes are determined by the settings for the device and the output of the various check utilities. See the `check_scripts/` folder for individual scripts that are run.

```
[
  {
    "alive": 0,
    "config": {
      "community": "public"
    },
    "icon": "router-network",
    "id": "switch-1",
    "info": "This device type will work with generic managed switches. SNMP information must be correct and setup on the switch for services to properly be queried.",
    "ip": "192.168.0.1",
    "name": "Switch 1",
    "overall_status": 1,
    "services": [
      {
        "id": "alive",
        "name": "Alive",
        "return_code": 0,
        "text": "Ping successfull!"
      },
      {
        "id": "switch-uptime",
        "name": "Switch Uptime",
        "return_code": 1,
        "text": "11 days, 2:09:34\n"
      }
    ],
    "type": "switch"
  }
]
```

## Hosts File

The hosts file is where the configuration is set for what hosts are to be monitored when the program starts. This config is done using YAML as an array of values. At minimum each host needs the following config options:

* type - the host type as defined below
* name - the name of the host to show up in the dashboard
* ip - the ip to check for a basic PING status

```
type: host_type
name: "Host Name"
ip: 127.0.0.1
```

The following additional options are available depending on the type of device:

* management_page - a link to the local management page of the host, if there is one. This will be displayed in the dashboard
* config - an additional mapping of config options specific to this host type

### Host Types

#### ESXi

This will define checks on a stand alone ESXi server. This includes overall ESXi status, status of running VMs, and datastore use. Below is an example configuration:

```
type: esxi
  name: "ESXi 1"
  ip: 192.168.0.2
  management_page: "https://192.168.0.2/ui/"
  config:
    username: "root"
    password: "pass"
```

### Generic Device

The most  basic device class available. Will check if the device is alive via a network ping but no other services will be checked.

```
type: generic
  name: "Device 1"
  ip: 192.168.0.5
```

#### Switch

The switch host type will check the status of a basic managed switch that has generic SNMP enabled. Below is an example configuration:

```
type: switch
  name: "Switch 1"
  ip: 192.168.0.1
  config:
    community: "public"
```

## License

[GPLv3](https://github.com/robweber/simple-monitoring/blob/main/LICENSE)
