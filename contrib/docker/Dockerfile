FROM debian:buster
RUN apt-get -y update && apt-get -y install build-essential ca-certificates git lsb-release make python3 python3-pip libatlas-base-dev
RUN cd /usr/src && git clone https://github.com/ngardiner/TWCManager

# Pre-install dependencies on arm7l (setuptools failing to install)
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install commentjson; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install cryptography; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install jinja2; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install numpy; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install ocpp; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install paho_mqtt; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install pyModbusTCP; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install pymysql; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install pyserial; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install requests; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install scipy; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install sentry_sdk; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install sysv_ipc; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install termcolor; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install websockets; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install ww; fi

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
