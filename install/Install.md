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
git clone https://github.com/robweber/trash-panda.git

# optionally clone the scripts repo (needed for examples to run)
git clone https://github.com/robweber/trash-panda-scripts.git

# go into the project dir and set directory as a variable
cd trash-panda
PROJECT_DIR=$(pwd)

# install python deps
sudo -H pip3 install -r install/requirements.txt
```

### Running the program

A configuration file is needed. This will copy the example config to the default directory for editing. Edit this file according to the instructions in the README document and run the `dashboard.py` file.

```

mkdir conf
cp install/monitor_example.yaml conf/monitor.yaml

```

### Installing as a Service

Install as a service by modifying the paths in the `install/trash-panda.service` file.

```
sudo cp install/trash-panda.service /etc/systemd/system/trash-panda.service
sudo chown root:root /etc/systemd/system/trash-panda.service
sudo systemctl enable trash-panda

# start the service
sudo systemctl start trash-panda

# stop the Service
sudo systemctl stop trash-panda
```
