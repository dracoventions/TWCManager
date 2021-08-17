# Manual Raspbian Installation

## Operating System Installation

The recommended installation for this project is on a Raspberry Pi machine using Raspbian. The Raspbian OS can be downloaded from the following location:

   * https://www.raspberrypi.org/downloads/raspbian/

You can flash the Raspbian OS using the tools listed on the following page:

   * https://www.raspberrypi.org/documentation/installation/installing-images/README.md

## Install Required Packages (Debian/Ubuntu/Raspbian)

The following packages are required to fetch and install the TWCManager project. These are the minimal required packages to start the installation process, during which any other required dependencies will be fetched automatically.

```
sudo apt-get update
sudo apt-get install -y git python3 python3-setuptools python3-dev libatlas-base-dev
```

## Default to Python3

TWCManager requires a minimum of python 3.4 to work correctly. To attempt to support Raspberry Pi OS versions going back to 2019, TWCManager is regularly tested against Python 3.4 and above to ensure that support is retained. As of TWCManager v1.2.2, a number of features are beginning to diverge based on minimum Python versions being higher than those required by TWCManager, so the following features may be unavailable if your Python version is below the minimum:

   * Support for OCPP control module requires a minimum Python 3.6.1 version

Raspberry Pi OS version 9 (stretch) from 2019 ships with Python 3.5.3. If you are running Raspberry Pi OS version 9 or earlier, you may not have access to a Python interpreter which supports the above features. You may want to consider the use of [pyenv](pyenv.md) to support installation of a newer Python interpreter.

Python versions below 3.6 may show the following error when running ```setup.py```:

```
Traceback (most recent call last):
  File "setup.py", line 3, in <module>
    from setuptools import setup, find_namespace_packages
ImportError: cannot import name find_namespace_packages
```

This indicates an older version of setuptools is installed. To resolve this issue, run the following command:

```
pip3 install --upgrade setuptools
```

### Raspberry Pi OS / Raspbian Buster

You may need to set python3 as your default python interpreter version on Raspberry Pi OS / Debian Buster. The following command will set python 3.7 as your default interpreter.

```
sudo update-alternatives --install /usr/bin/python python /usr/bin/python2.7 1
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.7 2
```

You can check that this command has been successful by running ```python --version``` and checking that the version is python3.

### Raspbian Stretch

You may need to set python3 as your default python interpreter version on Debian/Ubuntu. The following command will set python 3.5 as your default interpreter.

```
sudo update-alternatives --install /usr/bin/python python /usr/bin/python2.7 1
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.5 2
```

You can check that this command has been successful by running ```python --version``` and checking that the version is python3.

## Clone GIT Repository and copy files

During this step, the source code and all related files will be cloned from the GitHub repository and installed into the appropriate location on your system.

We have two versions of the codebase that you may want to check out. The stable version is **v1.2.2**, which will only change for stability or urgent fixes. To check out **v1.2.2**, follow these steps:


```
git clone https://github.com/ngardiner/TWCManager
cd TWCManager
git checkout v1.2.2
sudo make install
```

Alternatively, the **main** branch is the development branch, where all of the new ideas and features are tested prior to becoming the stable branch. This version has more features, but we can't guarantee stability.

```
git clone https://github.com/ngardiner/TWCManager
cd TWCManager
git checkout main
make install
```

## Configure TWCManager
After performing the installation tasks above, edit the /etc/twcmanager/config.json file and customize to suit your environment.

The following documents provide detail on specific areas of configuration:

   * [Policy Customization](PolicyCustomization.md)

## Running TWCManager
Once the above steps are complete, start the TWCManager script with the following command:

Prior to v1.2.3:

```
python -m TWCManager
```

From v1.2.3 onwards:

```
sudo -u twcmanager python -m TWCManager
```

### Monitoring the script operation

After starting TWCManager, the script will run in the foreground and will regularly update with the current status. An example output is as follows:

<pre>
11:57:49: <b>SHA 1234</b>: 00 <b>00.00/00.00A</b> 0000 0000  <b>M</b>: 09 <b>00.
00/17.00A</b> 0000 0000
11:57:49: Green energy generates <b>4956W</b>, Consumption <b>726W</b>, Charger Load <b>0W</b>
          Limiting car charging to 20.65A - 3.03A = <b>17.62A</b>.
          Charge when above <b>6A</b> (minAmpsPerTWC).
</pre>

   * SHA 1234 is the reported TWC code for each of the Slave TWCs that the Master is connected to.
   * The 00.00/00.00A next to the Slave TWC code is the current number of amps being utilised and the total number of amps available to that slave. The master divides the total amperage available for use between the connected slaves.
   * M is the same values for the Master device (our script). It shows current utilization and total available amps (in this case, 17A) available for all connected slaves.

   * The second line shows the green energy values detected. In this case, the attached green energy device (solar inverter) is reporting 4956W being generated from solar, 726W being used by other household appliances, and no load being generated by the charger. As we charge a vehicle, that value will increase and maybe subtracted from the consumption value if configured to do so.
   * The line below this reports the same values but in amps instead of watts.
   * The final line shows the minAmpsPerTWC value, which is the minimum number of amps that the master must offer each slave before we tell the attached vehicle to charge (via the Tesla API).

## Running TWCManager as a Service

The following commands make TWCManager run automatically (as a service) when the Raspberry Pi boots up.

Enable the service. The --now flag also makes it start immediately. This will persist after rebooting.

```
sudo cp contrib/twcmanager.service /etc/systemd/system/twcmanager.service
sudo systemctl enable twcmanager.service --now
```

   * Note: The ```systemd``` service file assumes that your TWCManager installation is in ```/home/pi/TWCManager```. If this is not the case, edit ```/etc/systemd/system/twcmanager.service``` and update the ```WorkingDirectory``` parameter to suit.

To check the output of the TWCManager service as it runs in the background, use the following command:
```
journalctl -f
```
To disable the TWCManager service permanently use the following command.  This will persist after rebooting.
```
sudo systemctl disable twcmanager
```
