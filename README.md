# balkonkraftwerk
The purpose of this repository is to control a balcony power plant extended with a battery. 
The focus is on a German regulation with simplified requirements for setups with feed-in below 600W which disclaim feed-in remuneration. 
Therefore, it might be useful to use as much of the energy as possible on your own. 
This setup is made for apartment buildings where the electricity meter is far away from the apartment itself without any option to install a readout device there.

## Raspberry Pi setup
Start with a fresh image of the Raspberry Pi OS in the Lite version.
Depending on the type of your Raspberry Pi your may either the 32bit or the 64bit version.
Using the imager for the SD card you could already set up your WiFi credentials, username, hostname and SSH access.
You are free to choose your username except for the name "balkonkraftwerk" which will be generated later.
In the following we assume "pi" as username.

### Installation with sudo privileges
These steps are performed under your username with sudo privileges:
```
sudo apt update
sudo apt upgrade -y
sudo apt dist-upgrade -y
sudo apt autoremove -y
sudo apt install git redis-server python3-pip python3-venv iptables python3-requests libopenblas0 -y
sudo useradd -m balkonkraftwerk
```

### Install software
We created a "balkonkraftwerk" user with the required privileges.
Now let's switch to this user (to go back to your user, type "exit"):
```
sudo su - balkonkraftwerk  # or login as user balkonkraftwerk directly
git clone https://github.com/jaluebbe/balkonkraftwerk.git
cd balkonkraftwerk
python -m venv venv
source venv/bin/activate
pip install -r requirements_raspi.txt
```

Create your own config.py based on config.py.example .
Now it's time to test if all scripts are working.
Later they will be managed by systemd.
The main process is called by
```
./balkonkraftwerk.py
```
and should run until you press Ctrl+C .
Permanent install (to be called under your user account):
```
sudo cp /home/balkonkraftwerk/balkonkraftwerk/etc/systemd/system/balkonkraftwerk.service /etc/systemd/system/
sudo systemctl enable balkonkraftwerk.service
```

If you would like to push data to your balkonkraftwerk cloud:
```
push_data.py
```
Permanent install:
```
sudo cp /home/balkonkraftwerk/balkonkraftwerk/etc/systemd/system/balkonkraftwerk_push.service /etc/systemd/system/
sudo systemctl enable balkonkraftwerk_push.service
```

If you are operating a Tibber Pulse to read out your elecricity meter (requires API key):
```
tibber_pulse.py
```
Permanent install:
```
sudo cp /home/balkonkraftwerk/balkonkraftwerk/etc/systemd/system/tibber_pulse.service /etc/systemd/system/
sudo systemctl enable tibber_pulse.service
```
If you would like to restart this service if it is hanging add the following line to /etc/crontab (requires your user account with sudo privileges):
```
* *     * * *   root    /home/balkonkraftwerk/balkonkraftwerk/check_tibber.py || systemctl restart tibber_pulse.service
```

### Local web interface and API
The web interface is run by:
```
./backend_raspi.py
```
Permanent install:
```
sudo cp /home/balkonkraftwerk/balkonkraftwerk/etc/systemd/system/balkonkraftwerk_api.service /etc/systemd/system/
sudo systemctl enable balkonkraftwerk_api.service
```
You may access the web interface via [ip or hostname]:8080 or the API via [ip or hostname]:8080/docs .


To archive data the data of the previous day automatically call
```
crontab -e
```
and add the following line:
```
27 3 * * * /home/balkonkraftwerk/balkonkraftwerk/archive_data.py
```

If you would like to create a redirection from port 80 to port 8080,
you should add the following line to /etc/rc.local :
```
/usr/sbin/iptables -A PREROUTING -t nat -i wlan0 -p tcp --dport 80 -j REDIRECT --to-port 8080
```
