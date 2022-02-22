# Install

Instructions to install the system with all required libraries and binary files.


### Initial OS setup and Python library install

This commands will setup the operating system and install the required Python libraries.

```
cd ~

sudo apt-get update

# install default packages we'll need
sudo apt-get install apt-transport-https gnupg git nagios-plugins nagios-plugins-basic nagios-plugins-standard python3 python3-pip redis-server wget

# clone repo
git clone https://github.com/eau-claire-energy-cooperative/dr-dashboard.git

# go into the project dir and set directory as a variable
cd dr-dashboard
PROJECT_DIR=$(pwd)

# install python deps
sudo pip3 install -r install/requirements.txt
```

### Celery setup

Running celery as a daemon is required so that asynchronous commands can be executed on devices.

```
# run celery as service
sudo cp install/celeryd /etc/init.d/
sudo chmod 755 /etc/init.d/celeryd
sudo chown root:root /etc/init.d/celeryd

# create config file for celery
echo CELERY_BIN=\"/usr/local/bin/celery\" > celeryd.config
echo CELERY_APP=\"module.commands.celery\" >> celeryd.config
echo CELERYD_CHDIR=\"$PROJECT_DIR\" >> celeryd.config
echo CELERYD_OPTS=\"--concurrency=8\" >> celeryd.config
echo CELERYD_LOG_FILE=\"/var/log/celery/%n%I.log\" >> celeryd.config
echo CELERYD_PID_FILE=\"/var/run/celery/%n.pid\" >> celeryd.config
echo CELERYD_USER=\"$USER\" >> celeryd.config
echo CELERYD_GROUP=\"$USER\" >> celeryd.config
echo CELERY_CREATE_DIRS=1 >> celeryd.config
echo export SECRET_KEY=\"Ms53K10Xlf\" >> celeryd.config

# move config file and start celery on startup
sudo mv celeryd.config /etc/default/celeryd
sudo chown root:root /etc/default/celeryd
sudo chmod 640 /etc/default/celeryd
sudo update-rc.d celeryd defaults

# services
sudo systemctl daemon-reload

# start with
sudo service celeryd start

```

### Running the program

A configuration file is needed. This will copy the example config to the default directory for editing. Edit this file according to the instructions in the README document and run the `dashboard.py` file.

```

mkdir conf
cp install/monitor_example.yaml conf/monitor.yaml

```
