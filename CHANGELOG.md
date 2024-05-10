# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## 6.1

### Changed

- migrated Pushover to use [chump](https://chump.readthedocs.io/en/latest/) instead of python-pushover library

## 6.0

### Added

- Service Tagging. Allows for services to be tagged within the config file. Tags will group the services so that they can display together on a common dashboard. This allows similar services across hosts to be viewed together.
- Service Tags can set colors within the `web` key of the configuration file, default color is black.
- New notifier type: __webhook__. This sends a JSON payload to the given url
- New API endpoint `/api/status/services` to list services. Filtering by the return_code is also possible
- API endpoints that return service related data now include performance data (`perf_data`) if the service check command returns it. This is parsed according to the Nagios standards.
- Redis Time Series integration is used to save perf data for each host for 24 hours.
- performance data web pages with ChartJS integration to view perf data if available
- New API endpoint `/api/status/service/<service_id>` to get information about a specific service
- New API endpoint `/api/time/<perf_id>/<int:start>/<int:end>` to retieve time series information from a performance data point. start and end are unix timestamps

### Changed

- Redis backend is now changed to rely on the [Redis JSON module](https://redis.io/docs/latest/develop/data-types/json/). This requires the `redis-stack-server` and not the `redis-server` for the key store.
- Many API endpoints now have different paths. This is an attempt to organize similar calls under a tree such as `/api/status` for all status related calls and `/api/command/` for command related calls. See the API section of the README for all changes.
- made `/api/status/summary` more efficient at filtering services in error
- modified menu to include a dropdown menu. The Dashboard is now renamed the Overview page and two new dashboards are available. Issues and Tags.
- the built in ping check now includes some basic performance data (percent packet loss and average return time) as part of the raw data
- `/api/status/all` is now `/api/status/hosts`. It also excludes service information from each host, this speeds up the return time and the `/api/status/host` endpoint can be used to get the full host info with service information

### Fixed

- fixed overwriting host key for services on `/api/status/summary` endpoint. This is already set when the service output is created

### Removed

- removed `commands.html`. This was file wasn't used and was part of an older version of the project

## Version 5.2

### Added

- `/editor` now accepts query param to load a document `/editor?path=/path/to/file`
- Edit button now jumps direction to documentation file editor

### Changed

- changed behavior of the watchdog service. It now sends both __up__ and __down__ status messages. The main dashboard program does not modify the .service_down file any longer, this is done in the watchdog only.

## Version 5.1

### Added

- can set editor to __read only__ mode. Allows files to be viewed but not saved
- optional `ping_command` value can be set per device or per device type. Allows for alive checks other than built in ICMP.

### Changed

- example config file utilizes fake service and ping checks to give a more realistic demo environment

## Version 5.0

### Added

- added ability to add links to top nav via the config file, part of #25
- can set color and style of top nav links, either `button` or `link` (plain hyperlink) styles are supported
- any Markdown file from the __docs_dir__ can be loaded directly using the endpoint `/docs/<filename>`. This allows for custom pages to be created and linked within the site. Part of #25
- Added link in footer to current README as an html page `/guide`. User can reference YAML syntax locally.
- Enabled [Markdown extensions](https://python-markdown.github.io/extensions/) for Table of Contents and Tables
- Favicon and logo from [Twemoji](https://github.com/twitter/twemoji)
- ability to edit the landing page text

### Changed

- _Status_ link changed to _Dashboard_ on top nav
- example config now includes example for top nav link and custom page
- only show title on desktop view, otherwise show only icon image

## Version 4.2

### Added

- in the `/api/status` endpoint services now contain a `text` and `raw_text` attribute. Raw text is the output directly from the service check while the text attribute may be filtered for better readability.
- host service definitions can include an `output_filter` template to modify the output of a service check for better readability

### Changed

- service check output is filtered based on the [Nagios performance data output format](https://nagios-plugins.org/doc/guidelines.html#AEN200). Output in the form `"output|performance data"` is split on the pipe (|) character and only the output portion rendered in the UI.

## Fixed

- if host status is "not alive" do not use overall status output from the services for overall host status, this will always be "unknown" since services are set to unknown when host is down. Instead use host status return value
- fixed `watchdog.py`, this was never amended to the new notifications methods added in 4.0
- fixed checking for `notifier` key with a host definition before sending notifications. Was not working properly as the host was passed as a string

## Version 4.1

### Added

- host status page can show documentation specific to that host. Created using markdown files in the `docs` directory, or a custom directory
- Markdown (.md) is a valid file type to edit in the Configuration editor
- added `docs_dir` configuration key to specify custom documentation directory
- overall host status displayed on status page

### Changed

- can set host ID using the `id` value if needed. Will default to a slugified version of the name if not set

## Version 4.0

### Added

- new http call `/api/silence_host/<id>/<minutes>` will put host in silent mode for the given number of minutes
- added property `silence` to API status output. Set to true when host is still in silent mode
- updated web interface so hosts can be put in silent mode and show silent mode status
- multiple notification channels can be added instead of just one. Can also set primary type (`all`) by default.
- `notifier` tag can be set at the host or service level to override the default notification method. Special options `all` and `none` are also available
- new `email` notification type to route messages through to an email account

### Changed

- global notifications are now set with the `notification` option instead of `notifier`
- condensed `schema.yaml` file layout

### Fixed

- can use floating point numbers as arguments for a service, previously was limited to integers

## 3.3

### Added

- added custom CSS for mobile devices

## 3.2

### Added

- added `services_with_errors` count to the `/api/overall_status` endpoint
- added new endpoint `/api/check_now/<id>` to reset a given hosts next check time to now
- "Check Now" button available in web interface to update host next check time

### Changed

- `monitor.py` stores hosts in a dict instead of an array, easier to find specific host information when needed

### Fixed

- minor grammar mistakes on dashboard pages
- fixed logic for getting the `next_check` value on startup, attempt to use the previously set value if host has one
- removed some deprecated variables

## 3.1

### Added

- screenshot to README
- added `/api/health` endpoint to determine the running status of the main program loop. Returns _Offline_ if the main check loop hasn't run in 2 minutes - in theory this should run once every 60 seconds
- `watchdog.py` script that can be used to externally check if the service is healthy
- added column headers to the host status page

### Changed

- `SCRIPTS_PATH` template variable now points to [trash-panda-scripts](https://github.com/robweber/trash-panda-scripts) repo. Default location is same parent folder containing main repo.
- the main service check loop now waits until the top of the next minute instead of 60 seconds from the end of the previous loop

### Fixed

- minor spelling and syntax in the README

### Removed

- moved all scripts from the `check_scripts` directory to their own repo

## 3.0

### Added

- added `HostHistory` class to encapsulate Redis db activity
- can specify a number of check attempts before confirming critical/warning states. global, device type, and specific host definitions available
- services now have a `last_state_change` attribute that has the date/time of the last confirmed state change
- __log__ type notifier can now optionally log to a separate file as defined by the `path` argument

### Changed

- updated `dashboard.py` to use history class instead of direct Redis db access
- notifications only go out on CONFIRMED states
- removed showing all config entries on the host status page - these can be viewed in the config area
- rebranded to __Trash Panda__

### Fixed

- don't show debug messages from `asyncio` package

## 2.1

### Added

- added config value `jinja_constants` to define a list of values that can be passed to the Jinja templating engine. These can be paths or just general constants.
- added services list to overall status to list all services currently in an error state
- added web based configuration file editor - can load YAML and Python files, save files, and check currently loaded config
- added check script for Gitlab services
- added the next check time to the returned host information as well as display on host status page. This value reflects some randomness to help spread load (check interval +/- 60 seconds)

### Fixed

- catch for if services are added/removed from a host when checking notifications. For now just skip the notification check until the next run
- device type name displayed funny when it contained spaces on the host status page
- fixed `notifications.py` file defining it's own Statuses list, use one from `utils.py` instead for consistency
- catch errors when YAML files can't be loaded due to parsing errors

### Changed

- used the default setting of the schema document to set the service_url so that something always exists in that field instead of checking for None all the time
- changed last references form "dr dashboard" to "simple monitoring"

### Removed

- `celeryd` file from Install directory, oversight

## 2.0

### Added

- added schema validator for checking the layout of the yaml file on startup
- ability to toggle if host check should be forced on startup via the `check_on_startup` config value, default is True
- support for sending notifications on host or service status changes. Notifiers are setup via the YAML config
- Log and Pushover notification options added

### Changed

- service arguments are now under an `args` key
- moved default interval from a command line argument to setting within the yaml file

### Fixed

- added catch for rare condition where overall status is not available for a particular host

## 1.1

### Added

- added a function to get all valid host id slugs from the monitor class
- added DB key for the current list of valid hosts
- added nagios plugins as part of base install
- additional API endpoint `/api/overall_status` to get a summary of overall system statuses for all devices
- throw an exception if a device type is referenced but doesn't actual exist
- added service file and instructions for install

### Changed

- `monitor.check_hosts()` only returns hosts that have changed, status updates are now cached per host in redis

### Fixed

- fixed address showing up twice on host status page
- host config wasn't be passed back on /api/status call

## 1.0

### Added

- added a generic network device that allows for custom tcp and udp services
- allow custom override of device icon
- added custom yaml !include directive to include other files within main hosts.yaml file

### Changed

- switch to YAML for the format of the host config file for better readability and easier config
- device classes are loaded dynamically in monitor class
- check interval is now per-host with a system wide default. This is set in the host config
- all host configuration now done in YAML through the use of `services`, `types`, and `hosts` definitions, custom types are removed

### Removed

- removed custom Device class objects, custom types should be created within the `types` area of the YAML config

## 0.0.2

### Added

- added basic information to the README document (host types, basic usage, license info)
- masking of passwords on status page

### Changed

- device type set their own icons in the device class instead of keeping track separate in index.html file
- replaced Bootstrap Icons with [Material Design Icons](https://materialdesignicons.com/)

### Fixed

- make sure port value from args is pushed to the web app
- fixed some typos in the install instructions

### Removed

- removed commands area, not going to use this from original

## Version 0.0.1

### Added

- moved code from original repo
