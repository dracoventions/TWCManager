DEPS := git libffi-dev libpq-dev libssl-dev
WEBDEPS := $(DEPS) lighttpd
SUDO := sudo
USER := twcmanager
GROUP := twcmanager
VER := $(shell lsb_release -sr)

.PHONY: tests upload

build: deps build_pkg
docker: deps build_pkg config
webbuild: webdeps build_pkg

config:
	# Create twcmanager user and group
	$(SUDO) useradd -U -M $(USER) 2>/dev/null; exit 0
	$(SUDO) usermod -a -G dialout $(USER)

	# Create configuration directory
	$(SUDO) mkdir -p /etc/twcmanager
ifeq (,$(wildcard /etc/twcmanager/config.json))
	$(SUDO) cp etc/twcmanager/config.json /etc/twcmanager/
endif
	$(SUDO) chown $(USER):$(GROUP) /etc/twcmanager -R
	$(SUDO) chmod 755 /etc/twcmanager -R

deps:
	$(SUDO) apt-get update
	$(SUDO) apt-get install -y $(DEPS)

webdeps:
	$(SUDO) apt-get update

ifeq ($(VER), 9.11)
	$(SUDO) apt-get install -y $(WEBDEPS) php7.0-cgi
else ifeq ($(VER), stretch)
	$(SUDO) apt-get install -y $(WEBDEPS) php7.0-cgi
else ifeq ($(VER), 16.04)
	$(SUDO) apt-get install -y $(WEBDEPS) php7.0-cgi
else ifeq ($(VER), 16.10)
	$(SUDO) apt-get install -y $(WEBDEPS) php7.0-cgi
else ifeq ($(VER), 20.04)
	$(SUDO) apt-get install -y $(WEBDEPS) php7.4-cgi
else
	$(SUDO) apt-get install -y $(WEBDEPS) php7.3-cgi
endif
	$(SUDO) lighty-enable-mod fastcgi-php ; exit 0
	$(SUDO) service lighttpd force-reload ; exit 0

install: deps install_pkg config
webinstall: webdeps install_pkg config webfiles

testconfig:
	# Create twcmanager user and group
	$(SUDO) useradd -U -M $(USER); exit 0

	# Create configuration directory
	$(SUDO) mkdir -p /etc/twcmanager
ifeq (,$(wildcard /etc/twcmanager/config.json))
	$(SUDO) cp etc/twcmanager/.testconfig.json /etc/twcmanager/config.json
endif
	$(SUDO) chown $(USER):$(GROUP) /etc/twcmanager -R
	$(SUDO) chmod 755 /etc/twcmanager -R

build_pkg:
	# Install build pre-requisite
	$(SUDO) apt-get -y install python3-venv

	# Install TWCManager packages
ifeq ($(CI), 1)
	$(SUDO) /home/docker/.pyenv/shims/pip3 install -r requirements.txt
	$(SUDO) /home/docker/.pyenv/shims/python3 -m build
else
ifneq (,$(wildcard /usr/bin/pip3))
	$(SUDO) pip3 install --upgrade pip
	$(SUDO) pip3 install --upgrade setuptools
	$(SUDO) pip3 install -r requirements.txt
else
ifneq (,$(wildcard /usr/bin/pip))
	$(SUDO) pip install --upgrade pip
	$(SUDO) pip install --upgrade setuptools
	$(SUDO) pip install -r requirements.txt
endif
endif
	$(SUDO) python3 -m build
endif

install_pkg:
ifneq (,$(wildcard /usr/bin/pip3))
	$(SUDO) pip3 install -r requirements.txt
	$(SUDO) pip3 install .
else
ifneq (,$(wildcard /usr/bin/pip))
	$(SUDO) pip install -r requirements.txt
	$(SUDO) pip install .
endif
endif

test_direct:
	cd tests && make test_direct

test_service:
	cd tests && make test_service

test_service_nofail:
	cd tests && make test_service_nofail

tests:
	cd tests && make

upload:
	cd tests && make upload

webfiles:
	$(SUDO) cp html/* /var/www/html/
	$(SUDO) chown -R www-data:www-data /var/www/html
	$(SUDO) chmod -R 755 /var/www/html
	$(SUDO) usermod -a -G www-data $(USER)
