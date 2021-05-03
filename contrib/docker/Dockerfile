FROM debian:buster
RUN apt-get -y update && apt-get -y install build-essential git lsb-release make python3 python3-pip
RUN cd /usr/src && git clone https://github.com/ngardiner/TWCManager
RUN cd /usr/src/TWCManager && make SUDO=""

VOLUME /etc/twcmanager
WORKDIR /usr/src/TWCmanager

ENTRYPOINT ["/usr/bin/python3","TWCManager.py"]
