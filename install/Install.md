# Install

Instructions to install the system with all required libraries and binary files. This installation will run both the service and database on the same machine. Installation of the Redis database can be done on a different device. 

### Initial OS setup and Python library install

This commands will setup the operating system and install the required Python libraries.

```
cd ~

# redis-stack-server needs additional repo
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
sudo chmod 644 /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt-get update

# install default packages we'll need
sudo apt-get install apt-transport-https gnupg git nagios-plugins nagios-plugins-basic nagios-plugins-standard python3 python3-pip redis-stack-server wget

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

A configuration file is needed. This will copy the example config to the default directory for editing and copy an example custom page to the docs directory. Edit the config file according to the instructions in the README document and run the `dashboard.py` file.

```

mkdir conf
cp install/monitor_example.yaml conf/monitor.yaml
mv docs/wiki.example docs/wiki.md

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
