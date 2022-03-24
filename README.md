# Simple Monitoring

This is a _very_ basic monitoring solution meant for simple home use. It will monitor the status of some basic IP systems and services in a simple dashboard. Some basic service and device type definitions are supplied; however more can be added by altering the YAML configuration files.

## Table of Contents

- [Install](#install)
- [Usage](#usage)
- [Dashboard](#dashboard)
  - [API](#api)
- [Config File](#config-file)
  - [Global Configuration](#global-configuration)
  - [Notifications](#notifications)
- [Services](#services)
- [Host Types](#host-types)
- [Host Definitions](#host-definitions)
  - [Optional Attributes](#optional-attributes)
- [Templating](#templating)
  - [Host](#host)
  - [Service](#service)
  - [Script Paths](#script-paths)
  - [Custom Functions](#custom-functions)
- [Contributing](#contributing)
- [License](#license)

## Install

Install the repository according to the instructions in the [Install](install/Install.md) guide. Once this is done you can proceed to the Usage section.

### Usage

Before the program can be used services, device types, and hosts need to be configured in the `monitor.yaml` file created during the install. Detailed instructions for how to do this are below. Running the program must be done with `sudo` as root privileges are needed to bind to a socket. Once running the dashboard page will be available at `http://server_ip:5000/`. _Note the port may be different if you change it using the arguments below._

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

usage: dashboard.py [-h] [-c CONFIG] [-f FILE] [-p PORT] [-D]

Simple Monitoring

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to custom config file
  -f FILE, --file FILE  Path to the config file for the host data,
                        conf/monitor.json by default
  -p PORT, --port PORT  Port number to run the web server on, 5000 by default
  -D, --debug           If the program should run in debug mode

```

## Dashboard

Once running the dashboard page can be loaded. The landing page will display all currently configured hosts and their overall status. If the host is down, or any configured service unavailable, the overall status will change. This page is refreshed every __15 seconds__. Data will change depending on the update interval set when the program is loaded.

Clicking on a host name will show you more information about that device. Individual services will be listed along with any output to indicate their current status. If configured, the management page for the host can also be launched from here.

### API

For integration with other systems the API can be used. To decode the status return codes use the following:

* 0 - OK, everything normal
* 1 - Warning, potential problem
* 2 - Critical, definitely a problem

The status codes are determined by the settings for the device and the output of the various check utilities. See the `check_scripts/` folder for individual scripts that are run.

__/api/status__ - detailed listing of the status of each host

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

__/api/overall_status__ - a status summary of the overall status of all hosts

```
{
  "hosts_with_errors": 0,
  "overall_status": 0,
  "overall_status_description": "OK",
  "total_hosts": 3
}
```

## Config File

The monitor file is where the configuration is set for services, device type, and host definitions which are loaded when the program starts. This config is done using YAML. The sections below are all needed but can be separated into their own files for ease of readability. Look at the example file `install/monitor_example.yaml` for a full example. Errors in syntax will be flagged on startup.

* config - items that control the overall configuration of the monitor service
* services - an array of service definitions that can be included in device types or individual hosts
* types - definitions for specific device types and required configuration variables needed.
* hosts - a list of the actual hosts to be monitored on the network. Each one must inherit a device type but can add their own service checks.

Example file where these are imported from separate files:
```
config: !include conf/config.yaml
services: !include conf/services.yaml
types: !include conf/types.yaml
hosts: !include conf/hosts.yaml
```

The following additional options are available depending on the type of device:

* management_page - a link to the local management page of the host, if there is one. This will be displayed in the dashboard
* icon - the icon to use for the device, overrides the default type. Should be found on [Material Design Icons](https://materialdesignicons.com/)
* interval - how often this host should be checked, in minutes. If not given this is the system default.
* config - an additional mapping of config options specific to this host type

### Global Configuration

Global configuration options are set under the `config` key in the YAML configuration file. Some have defaults set and can be omitted if not needed.

```
config:
  default_interval: 3
  check_on_startup: True
  notify:
    type: log
```

* default_interval - the default host check interval, in minutes. This will default to 3 unless changed. [Individual hosts](#host-types) can set their own interval if needed.
* check_on_startup - if hosts should all be checked immediately after startup. Defaults to True. If this is set to False, host checks will start on their normal interval from the program start time.
* notifier - defines a notification channel, see more below

### Notifications

By default the system will not send any notifications, but there is support for some built-in notification methods. These can be defined in the `config` section of the YAML file by creating a `notifier` option. A notifier is loaded at startup and will send notifications on host status (up/down) changes or service status changes each time a check is run.

Additional notification methods can be defined by extending the `MonitorNotification` class. Built-in notification types are listed below.

__Log Notifier__ - writes all notification messages directly to the log
```
config:
  notifier:
    type: log
```

__Pushover Notifier__ - sends messages through the [Pushover Notification Service](https://pushover.net/). A valid application key and user key are needed for your account and can be generated using [their instructions](https://pushover.net/api). 
```
config:
  notifier:
    type: pushover
    args:
      api_key: pushover_api_key
      user_key: pushover_user_key
```

## Services

Services are defined in the __services__ section of the `monitor.yaml` file, or included as a separate file. Each service listed needs to include a name, path to the service check command, and a list of arguments that will be sent at runtime to perform the check. [Jinja templates](https://jinja.palletsprojects.com/en/3.0.x/templates/) can be used to expand variables from the host config. An example config to check a web service would be:

```
http:
  command: "{{ path(NAGIOS_PATH, 'check_http') }}"
  args:
    - "-H"
    - "{{ host.virtual_host }}"
    - "-p"
    - "{{ default(service.port, 80) }}"
    - "-u"
    - "{{ default(service.path, '/') }}"
```

Breaking this down the __command__ statement points to the path of the Nagios `check_http` command. The __args__ section defines arguments to be passed to this executable.

Within the arguments several custom variable placeholders and methods used. These are available for all service definitions and are listed in the [Templating section](#templating). You can see that the host address is used; which is expanded at runtime. A default of port 80 is given but can be changed if the user sets the `service.port` variable on the host. Similarly the web path of `/` is given as a default but could be changed to something liked `/login` if the `services.path` variable is set.




## Host Types

Host types are a way to define specific types of device, such as a server or network switch. Each type can include service checks that you'd expect every device of this type to have. An example may be a Web Server device type that includes a status check on port 80 by default.

Device types can also define configuration variables that must be included in host configs so that service checks execute properly. Using the above example of an http command from above an example host type definition could be:

```
web_server:
  name: Web Server
  icon: server
  interval: 10
  config:
    virtual_host:
      required: True
  services:
    - type: http
      name: "Check Website"
```

The above defines a device type of __web_server__ that can be implemented by a host. The host must have the variable __virtual_host__ present, as it's used in the http service config; and also will automatically have the service check __http__ assigned to it.

Also notice the __interval__ value. This is optional. By default the global interval will be used, but individual device types, or individual hosts, can set their own.  

## Host Definitions

Finally, the Service and Device Type definitions are put together into an actual host definition. This represents the actual device you wish to monitor on the network. Continuing with the web server example our host could look something like:

```
type: web_server
name: "My Web Server"
# the info tag is optional
info: "A local webserver hosting a few sites"
address: 192.168.0.2
management_page: "http://myserver:5000/admin"
config:
  virtual_host: "myserver"
services:
  - type: http
    name: "Admin Page"
    args:
      port: 5000
      path: "/admin"
```

The above host will inherit the services from the __web_server__ type above but it also adds an additional http check on port 5000 for a different site. Both of these will be checked at run time.

### Optional Attributes

The following attributes are useful, but not necessary, for any host definition:
* icon - a custom icon from [Material Design Icons](https://materialdesignicons.com/)
* info - any additional information on this device you want displayed on the Dashboard page.
* management_page - the full URL to web management for this device, if it exists
* interval - the check interval, if different than the global value

## Templating

When expanding templates for service variables there are a few global variables and custom functions available.

### Host

The `host` variable is a dictionary containing any configuration listed for the host under the `config` section. Additionally `host.address` will always contain the host address.

### Service

The `service` variable is a dictionary containing any configuration listed for the service specifically as defined in the host config.

### Script Paths

The OS path to both the Nagios default scripts and the `custom_scripts` directory of the simple-monitoring repo are available as shortcuts to defined command paths. These are:

* NAGIOS_PATH
* SCRIPTS_PATH

### Custom Functions

The following custom functions are available in addition to any standard [Jinja templating functions](https://jinja.palletsprojects.com/en/3.0.x/templates/#list-of-global-functions).

* `path()` - this is a shortcut for the Python os.path.join() method to easily join paths togehter.
* `default()` - allows for setting a default in cases where the user may or may not set a variable. If the user variable doesn't exist the default is used.


## License

[GPLv3](https://github.com/robweber/simple-monitoring/blob/main/LICENSE)
