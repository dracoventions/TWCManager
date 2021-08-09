FROM debian:buster
RUN apt-get -y update && apt-get -y install build-essential ca-certificates git lsb-release make python3 python3-pip libatlas-base-dev
RUN cd /usr/src && git clone https://github.com/ngardiner/TWCManager

# Pre-install dependencies on arm7l (setuptools failing to install)
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install pymysql; fi
RUN if [ "`uname -m`" = "armv7l" ]; then pip3 install sysv_ipc; fi

# Remove problematic depedencies on arm7l
RUN if [ "`uname -m`" = "armv7l" ]; then cp /usr/src/TWCManager/setup.py /usr/src/TWCManager/setup.py.tmp; fi
# See if this is related
RUN if [ "`uname -m`" = "armv7l" ]; then cat /usr/src/TWCManager/setup.py.tmp | grep -v numpy | grep -v scipy | grep -v sysv_ipc | grep -v websockets > /usr/src/TWCManager/setup.py; fi
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
