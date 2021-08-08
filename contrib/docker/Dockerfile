FROM debian:buster
RUN apt-get -y update && apt-get -y install build-essential ca-certificates git lsb-release make python3 python3-pip libatlas-base-dev
RUN cd /usr/src && git clone https://github.com/ngardiner/TWCManager

# Remove problematic depedencies on arm7l
RUN if [ "`uname -m`" = "armv7l" ]; then cp /usr/src/TWCManager/setup.py /usr/src/TWCManager/setup.py.tmp; fi
# See if this is related
RUN if [ "`uname -m`" = "armv7l" ]; then cat /usr/src/TWCManager/setup.py.tmp | grep -v cryptography > /usr/src/TWCManager/setup.py; fi
#RUN if [ "`uname -m`" = "armv7l" ]; then cat /usr/src/TWCManager/setup.py.tmp | grep -v numpy | grep -v scipy | grep -v sysv_ipc | grep -v websockets > /usr/src/TWCManager/setup.py; fi
RUN cd /usr/src/TWCManager && make install SUDO=""

VOLUME /etc/twcmanager
WORKDIR /usr/src/TWCManager

COPY entrypoint.sh ./entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
CMD ["/usr/bin/python3","TWCManager.py"]
