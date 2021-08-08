FROM debian:buster
RUN apt-get -y update && apt-get -y install build-essential ca-certificates git lsb-release make python3 python3-pip libatlas-base-dev
RUN cd /usr/src && git clone https://github.com/ngardiner/TWCManager

# Remove problematic depedencies
RUN cp /usr/src/TWCManager/setup.py /usr/src/TWCManager/setup.py.tmp
RUN cat /usr/src/TWCManager/setup.py.tmp | grep -v numpy | grep -v scipy | grep -v websockets > /usr/src/TWCManager/setup.py
RUN cd /usr/src/TWCManager && make install SUDO=""

VOLUME /etc/twcmanager
WORKDIR /usr/src/TWCManager

COPY entrypoint.sh ./entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
CMD ["/usr/bin/python3","TWCManager.py"]
