# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

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
