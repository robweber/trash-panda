# Trash Panda
![alt text](https://github.com/robweber/trash-panda/raw/main/install/monitor_dashboard.png "Dashboard Screen")
[![PEP8](https://img.shields.io/badge/code%20style-pep8-orange.svg)](https://www.python.org/dev/peps/pep-0008/)
[![standard-readme compliant](https://img.shields.io/badge/readme%20style-standard-brightgreen.svg)](https://github.com/RichardLitt/standard-readme)

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
- [Host Documentation](#host-documentation)
- [Templating](#templating)
  - [Host](#host)
  - [Service](#service)
  - [Script Paths](#script-paths)
  - [Custom Functions](#custom-functions)
- [Watchdog](#watchdog)
- [Credits](#credits)
- [License](#license)

## Install

Install the repository according to the instructions in the [Install](install/Install.md) guide. Once this is done you can proceed to the Usage section.

## Usage

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

Trash Panda

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

Clicking on a host name will show you more information about that device. Individual services will be listed along with any output to indicate their current status. From the host status page a check of all services can be forced, and notifications temporarily silenced. If configured, a management page for the host can also be launched from here. For additional flexibility more host information can be displayed in the [documentation](#host-documentation) tab via custom Markdown files.

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
    "interval": 3,
    "service_check_attempts": 2,
    "last_check": "07-21-2022 11:01AM",
    "next_check": "07-21-2022 11:04AM",
    "services": [
      {
        "check_attempt": 1,
        "id": "alive",
        "last_state_change": "07-02-2022 11:40AM",
        "name": "Alive",
        "return_code": 0,
        "state": "CONFIRMED",
        "text": "Ping successfull!"
      },
      {
	      "check_attempt": 1,
        "id": "switch-uptime",
        "last_state_change": "07-02-2022 11:40AM",
        "name": "Switch Uptime",
        "return_code": 1,
        "state": "UNCONFIRMED",
        "text": "11 days, 2:09:34\n",
        "notifier": "none"
      }
    ],
    "silenced": false,
    "type": "switch"
  }
]
```

__/api/overall_status__ - a status summary of the overall status of all hosts. The `services` array is a list of all services currently in an error state.

```
{
  "hosts_with_errors": 0,
  "overall_status": 0,
  "overall_status_description": "OK",
  "total_hosts": 3,
  "services_with_errors": 0,
  "services": []
}
```

__/api/health__ - basic program health. Status is set to _Offline_ if the main system checking loop hasn't run in over 2 minutes. This should look for services to check every 60 seconds when running properly.

```
{
  "last_check_time": "07-05-2022 12:00PM",
  "text": "Online",
  "return_code": 0
}
```

__/api/check_now/<host_id>__ - updates a given host's next check time to the current time. This forces a service check instead of waiting for the normal update interval. The host id can be found via the `/api/status` endpoint for each host.

```
{
  "success": true
  "next_check": "09-14-2022 09:44AM"
}
```

__/api/silence_host/<host_id>/<minutes>__ - sets the given hosts silenced property to True for the given amount of minutes. This will silence any notifications for this time.

```
{
  "is_silenced": true,
  "success": true,
  "until": "05-02-2023 01:31PM"
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

The following additional options are available for every configured device:

* management_page - a link to the local management page of the host, if there is one. This will be displayed in the dashboard
* icon - the icon to use for the device, overrides the default type. Should be found on [Material Design Icons](https://materialdesignicons.com/)
* interval - how often this host should be checked, in minutes. If not given this is the system default. At runtime this value is randomly adjusted +/- 60 seconds to help spread load.
* service_check_attempts - how many times a service should be checked before confirming a warning or critical state. Default is 3, set this to 1 to automatically confirm state changes.
* config - an additional mapping of config options specific to this host type

### Global Configuration

Global configuration options are set under the `config` key in the YAML configuration file. Some have defaults set and can be omitted if not needed.

```
config:
  default_interval: 3
  service_check_attempts: 3
  check_on_startup: True
  docs_dir: docs
  jinja_constants:
    CUSTOM_PATH: /path/
  notify:
    type: log
```

* default_interval - the default host check interval, in minutes. This will default to 3 unless changed. [Individual hosts](#host-types) can set their own interval if needed. At runtime this value is randomly adjusted +/- 60 seconds to help spread load.
* service_check_attempts: how many times a service should be checked before confirming a warning or critical state. [Individual hosts](#host-types). Default is 3, set this to 1 to automatically confirm state changes.
* check_on_startup - if hosts should all be checked immediately after startup. Defaults to True. If this is set to False, host checks will start on their normal interval from the program start time.
* docs_dir - directory containing host documentation files, defaults to `docs`.
* jinja_constants - a list of key:value pairs that will be passed to the [Jinja templating engine](#templating). These can be things like commonly used system paths or referenced names used in defining host or service values.
* notifier - defines a notification channel, see more below

### Notifications

By default the system will not send any notifications, but there is support for some built-in notification methods. These can be defined in the `config` section of the YAML file by creating a `notifications` option. One, or more, notification types can be specified. By default notifications will be sent to `all` configured types, however a `primary` type can be specified that will be used by default unless another is specified at the host or service level. A special `none` type can also be used to specify no notifications. This is useful at the host or service level.

Notifications are triggered on host status (up/down) changes or service status changes each time a check is run. Services must be in a CONFIRMED state before a notification is sent. Services are in an UNCONFIRMED state when either a warning or critical state has not reached the `service_check_attempts` threshold described above. It is possible to temporarily silence notifications using the web interface or [API](#api).

Additional notification types can be defined by extending the `MonitorNotification` class. Built-in notification types are listed below.

__Email Notifier__ - sends notifications to an email address. Requires a valid SMTP server to route the mail through. Can be something like Gmail if valid permissions are given to send mail through the account.
```
config:
  notifications:
    primary: email
    types:
      - type: email
        args:
          server: email.server.com
          port: 25  # could be different, check your outgoing mail server settings
          secure: True  # if False, make sure your server allows non-authenticated connections
          username: user  # if secure=True
          password: password  # if secure=True
          sender: sender@email.server.com
          recipient: recipient@address.com
```

__Log Notifier__ - writes notification messages directly to the log. Optionally the `path` argument can be used to specify a custom log path for notification messages.
```
config:
  notifications:
    primary: all
    types:
      - type: log
        args:
          path: /path/to/custom.log
          propagate: True  # controls if notifications also written to root logger
```

__Pushover Notifier__ - sends messages through the [Pushover Notification Service](https://pushover.net/). A valid application key and user key are needed for your account and can be generated using [their instructions](https://pushover.net/api).
```
config:
  notifications:
    primary: none
    types:
      - type: pushover
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
  notifier: log
  service_check_attempts: 2
  config:
    virtual_host:
      required: True
  services:
    - type: http
      name: "Check Website"
```

The above defines a device type of __web_server__ that can be implemented by a host. The host must have the variable __virtual_host__ present, as it's used in the http service config; and also will automatically have the service check __http__ assigned to it.

Also of note are some optional variables.

* __interval__: By default the global interval will be used, but individual device types, or individual hosts, can set their own.
* __notifier__: Again, by default the global notification type will be used but hosts types can set their own. This will apply to the host and all services under it.
* __service_check_attempts__: Override the global service check value with a custom value for this host

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

The above host will inherit the services from the __web_server__ type above but it also adds an additional http check on port 5000 for a different site. Both of these will be checked at run time. Any variables available within the Host Type can be overridden by an individual host as well (icon, check interval, etc).

### Optional Attributes

The following attributes are useful, but not necessary, for any host definition:
* id - defaults to a slugified version of the name (`my-web-server` in example), but can be set specifically using the id value
* icon - a custom icon from [Material Design Icons](https://materialdesignicons.com/)
* info - any additional information on this device you want displayed on the Dashboard page.
* management_page - the full URL to web management for this device, if it exists
* interval - the check interval, if different than the global value
* service_check_attempts - how many service checks to confirm warning/critical states. Only needed if different than the global value.

## Host Documentation

On every host status page there is a tab for the configured services, and host documentation. The documentation tab is an optional feature that can pull host information from a Markdown file for that host. By default the location of these files is in the `docs` directory, but this can be changed in the config file.

To work properly the documentation file should have the same ID as as the host and end in `.md`. For a host named __My Web Server__ the file would be the slugified version of the host __my-web-server.md__. This is the same as the host id returned by the [API](#api) or found in the browser path when viewing the host status.

## Templating

When expanding templates for service variables there are a few global variables and custom functions available. Global variables can be added to by setting values in the `jinja_constants` section of the [global config](#global-configuration). Check the [example config file](https://github.com/robweber/trash-panda/blob/main/install/monitor_example.yaml) to see how these can be used within host and service configurations.

### Host

The `host` variable is a dictionary containing any configuration listed for the host under the `config` section. Additionally `host.address` will always contain the host address.

### Service

The `service` variable is a dictionary containing any configuration listed for the service specifically as defined in the host config.

### Script Paths

The OS path to both the Nagios default scripts and the `check_scripts` directory of the trash-panda repo are available as shortcuts to defined command paths. A default is set but you can override these by using the same name as `jinja_constants` values in the [global config](#global-configuration).

* NAGIOS_PATH - default is `/usr/lib/nagios/plugins/`
* SCRIPTS_PATH - path to [trash-panda-scripts](https://github.com/robweber/trash-panda-scripts) directory, default is `../trash-panda-scripts`

### Custom Functions

The following custom functions are available in addition to any standard [Jinja templating functions](https://jinja.palletsprojects.com/en/3.0.x/templates/#list-of-global-functions).

* `path()` - this is a shortcut for the Python os.path.join() method to easily join paths together.
* `default()` - allows for setting a default in cases where the user may or may not set a variable. If the user variable doesn't exist the default is used.

## Watchdog

Trash Panda will check if defined hosts and services are running, but what keeps track of Trash Panda? The `watchdog.py` script can be used to externally check the Trash Panda web service via the [health api](#api) endpoint. This script should be setup to run via a cron job and can read in the same YAML config file to trigger monitoring notifications. If the health service is either not running, or it reports that the monitoring system checker is not running, a notification will be sent using the configured notifier from the YAML file.

```
python3 watchdog.py -c conf/monitor.yaml
```

Once a notification is sent a flag file is created in the Trash Panda repo directory named `.service_down`. This file prevents further notifications and will be deleted when the Trash Panda service is restarted.

## Credits

The following projects are used within this project and contributed most of the heavy lifting in getting it completed.

* [Flask](https://flask.palletsprojects.com/en/2.1.x/#) - a micro web framework for Python
* [Jinja](https://palletsprojects.com/p/jinja/) - templating engine
* [Cerebrus](https://docs.python-cerberus.org/en/stable/) - used for YAML data validation
* [Bootstrap](https://getbootstrap.com/) - web frontend toolkit
* [JQuery](https://jquery.com/) - Javascript library
* [Material Design Icons](https://materialdesignicons.com/) - open source web icons

## License

[GPLv3](https://github.com/robweber/trash-panda/blob/main/LICENSE)
