FROM debian:buster
RUN apt-get -y update && apt-get -y install build-essential ca-certificates gfortran git lsb-release make python3 python3-pip libatlas-base-dev
RUN cd /usr/src && git clone https://github.com/ngardiner/TWCManager

# Helper script for downloading arm python wheels for dependencies. Saves hours of compiling.
# Non-ARM6 and 7 wheels are downloaded normally
RUN echo "#!/bin/sh" > /tmp/install.sh
RUN echo 'if [ "`/usr/src/TWCManager/contrib/docker/checkarch.sh`" = "y" ]; then pip3 install --extra-index-url=https://www.piwheels.org/simple $1; fi' > /tmp/install.sh
RUN chmod +x /tmp/install.sh

# Upgrade script for dependencies which require upgrade
RUN echo "#!/bin/sh" > /tmp/upgrade.sh
RUN echo 'if [ "`/usr/src/TWCManager/contrib/docker/checkarch.sh`" = "y" ]; then pip3 install --upgrade --extra-index-url=https://www.piwheels.org/simple $1; fi' > /tmp/upgrade.sh
RUN chmod +x /tmp/upgrade.sh

# Install prerequisites. Only active for arm platforms
RUN /tmp/install.sh commentjson
RUN /tmp/upgrade.sh cryptography
RUN /tmp/install.sh growattServer
RUN /tmp/install.sh jinja2
RUN /tmp/install.sh MarkupSafe
RUN /tmp/install.sh numpy
RUN /tmp/install.sh ocpp
RUN /tmp/install.sh paho_mqtt
RUN /tmp/install.sh pyModbusTCP
RUN /tmp/install.sh pymysql
RUN /tmp/install.sh pyserial
RUN /tmp/install.sh requests
RUN /tmp/install.sh scipy
RUN /tmp/install.sh sentry_sdk
RUN /tmp/install.sh sysv_ipc
RUN /tmp/install.sh termcolor
RUN /tmp/install.sh websockets
RUN /tmp/install.sh ww

# Install TWCManager
RUN cd /usr/src/TWCManager && make install SUDO=""

VOLUME /etc/twcmanager
WORKDIR /usr/src/TWCManager

COPY entrypoint.sh ./entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
CMD ["/usr/bin/python3","TWCManager.py"]

# SSL_CERTIFICATE_FAILED errors
# These errors began appearing and impacing the build pipeline in Jul 2021
# They occur only for the arm7 arch (which is the RPi) and only for some
# packages. Affected packages seem to be those with no wheel package for
# arm7.
#
# Things we've investigated:
# - Checked commits around the time it broke, nothing relevant
# - Public or private worker, no change
# - Changed debian to ubuntu LTS, no cbange
# - Skipped installation of cryptography package
# - Skipped impacted packages from setuptools script
