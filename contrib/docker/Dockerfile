FROM debian:bullseye
RUN apt-get -y update && apt-get -y install build-essential ca-certificates gfortran git lsb-release make python3 python3-pip libatlas-base-dev
RUN cd /usr/src && git clone https://github.com/ngardiner/TWCManager

# Install TWCManager
RUN cd /usr/src/TWCManager && make docker SUDO=""

VOLUME /etc/twcmanager
WORKDIR /usr/src/TWCManager

ENTRYPOINT ["./contrib/docker/entrypoint.sh"]
CMD ["/usr/bin/python3","-m","TWCManager"]

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
