all: test_direct
test_direct: general_prereqs mqtt_setup mysql_setup run_twcmanager wait preflight api ems
test_service: general_prereqs mqtt_setup mysql_setup run_service wait preflight api ems
test_service_nofail: general_prereqs mqtt_setup mysql_setup run_service_nofail wait

bold:=$(shell tput -T ansi bold)
red:=$(shell tput -T ansi setaf 1)
reset:=$(shell tput -T ansi sgr0)
yellow:=$(shell tput -T ansi setaf 3)

api := 10
ems := 2
pre := 7

general_prereqs:
	@echo "${bold}${red}(P1/${pre})${reset} ${yellow}Installing Prerequisites for Test Suite"
	@sudo apt-get install -y debconf-utils iproute2 > /dev/null 2>&1
	@mkdir -p /tmp/twcmanager-tests
	@chmod 777 /tmp/twcmanager-tests

mqtt_setup:
	@echo "${bold}${red}(P2/${pre})${reset} ${yellow}Installing MQTT Prerequisites"
	@sudo apt-get install -y mosquitto > /dev/null 2>&1

mysql_setup:
	@echo "${bold}${red}(P3/${pre})${reset} ${yellow}Installing MySQL Server"
	@sudo apt-get install -y mysql-server sqlite3 > /dev/null 2>&1
	@echo "${bold}${red}(P4/${pre})${reset} ${yellow}Setup MySQL Database"
	@sudo /home/docker/.pyenv/shims/python3 scripts/mysql_setup.py
	@echo "${bold}${red}(P5/${pre})${reset} ${yellow}Environment Preparation"
	@sudo /home/docker/.pyenv/shims/python3 pre-flight/env_preparation.py
	@echo "${bold}${red}(P6/${pre})${reset} ${yellow}Set up SQLite Database"
	@sudo -u twcmanager /home/docker/.pyenv/shims/python3 scripts/sqlite_setup.py

run_service:
	@cd .. && sudo cp contrib/.twcmanager.service.testing /etc/systemd/system/twcmanager.service
	@sudo apt-get install -y systemctl > /dev/null
	@echo "${bold}${red}(M1/2)${reset} ${yellow}Running TWCManager"
	@sudo /usr/bin/systemctl enable twcmanager.service --now
	@sleep 5
	@systemctl status twcmanager.service --full

run_service_nofail:
	@cd .. && sudo cp contrib/.twcmanager.service.testing /etc/systemd/system/twcmanager.service
	@sudo apt-get install -y systemctl > /dev/null
	@echo "${bold}${red}(M1/2)${reset} ${yellow}Running TWCManager"
	@sudo /usr/bin/systemctl enable twcmanager.service --now
	@sleep 5
	@systemctl status twcmanager.service --full || exit 0
	ls -l /var/log/

run_twcmanager:
	@echo "${bold}${red}(M1/2)${reset} ${yellow}Running TWCManager"
	@cd .. && sudo -u twcmanager /usr/bin/env PYTHONIOENCODING=UTF-8 /home/docker/.pyenv/shims/python3 -m TWCManager &

upload:
	@echo Uploading debug files
	@find /tmp/twcmanager-tests -type f | xargs -L 1 scripts/upload_file.sh
	@rm -r /tmp/twcmanager-tests

api:
	@echo "${bold}${red}(A1/${api})${reset} ${yellow}Test API Listener"
	@cd API && ./test_apilistener.sh
	@echo "${bold}${red}(A2/${api})${reset} ${yellow}Test API getConfig"
	@cd API && ./test_getConfig.py
	@echo "${bold}${red}(A3/${api})${reset} ${yellow}Test API getLastTWCResponse"
	@cd API && ./test_getLastTWCResponse.py
	@echo "${bold}${red}(A4/${api})${reset} ${yellow}Test API getPolicy"
	@cd API && ./test_getPolicy.py
	@echo "${bold}${red}(A5/${api})${reset} ${yellow}Test API getSlaveTWCs"
	@cd API && ./test_getSlaveTWCs.py
	@echo "${bold}${red}(A6/${api})${reset} ${yellow}Test API getStatus"
	@cd API && ./test_getStatus.py
	@echo "${bold}${red}(A7/${api})${reset} ${yellow}Test API chargeNow functionality"
	@cd API && ./test_chargeNow.py
	@echo "${bold}${red}(A8/${api})${reset} ${yellow}Test API sendStartCommand"
	@cd API && ./test_sendStartCommand.py
	@echo "${bold}${red}(A9/${api})${reset} ${yellow}Test API sendStopCommand"
	@cd API && ./test_sendStopCommand.py
	@echo "${bold}${red}(A10/${api})${reset} ${yellow}Test API consumption offsets"
	@cd API && ./test_consumptionOffsets.py

ems:
	@echo "${bold}${red}(E1/${ems})${reset} ${yellow}Starting EMS Test Web Server"
	@cd EMS && ./ems_emulator.py &
	@echo "${bold}${red}(E2/${ems})${reset} ${yellow}Testing SmartPi EMS Module"
	cd EMS && ./test_SmartPi.py

preflight:
	@echo "${bold}${red}(P7/${pre})${reset} ${yellow}Testing file existence and permissions"
	@cd pre-flight && ./check_environment.py
	ls -l /etc/twcmanager

wait:
	@echo "${bold}${red}(M2/2)${reset} ${yellow}Wait for TWCManager to start"
	@sleep 120
