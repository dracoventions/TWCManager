all: general_prereqs mqtt_setup mysql_setup run_twcmanager wait api ems

bold:=$(shell tput -T ansi bold)
red:=$(shell tput -T ansi setaf 1)
reset:=$(shell tput -T ansi sgr0)
yellow:=$(shell tput -T ansi setaf 3)

general_prereqs:
	@echo "${bold}${red}(P1/6)${reset} ${yellow}Installing Prerequisites for Test Suite"
	@sudo apt-get install -y debconf-utils iproute2 > /dev/null 2>&1
	@mkdir -p /tmp/twcmanager-tests
	@chmod 777 /tmp/twcmanager-tests

mqtt_setup:
	@echo "${bold}${red}(P2/6)${reset} ${yellow}Installing MQTT Prerequisites"
	@sudo apt-get install -y mosquitto > /dev/null 2>&1

mysql_setup:
	@echo "${bold}${red}(P3/6)${reset} ${yellow}Installing MySQL Server"
	@sudo apt-get install -y mysql-server sqlite3 > /dev/null 2>&1
	@echo "${bold}${red}(P4/6)${reset} ${yellow}Setup MySQL Database"
	@sudo /home/docker/.pyenv/shims/python3 scripts/mysql_setup.py
	@echo "${bold}${red}(P5/6)${reset} ${yellow}Environment Preparation"
	@sudo /home/docker/.pyenv/shims/python3 env_preparation.py
	@echo "${bold}${red}(P6/6)${reset} ${yellow}Set up SQLite Database"
	@python3 scripts/sqlite_setup.py

run_twcmanager:
	@echo "${bold}${red}(M1/2)${reset} ${yellow}Running TWCManager"
	@cd .. && python3 -m TWCManager &

upload:
	@echo Uploading debug files
	@find /tmp/twcmanager-tests -type f | xargs scripts/upload_file.sh
	@rm -r /tmp/twcmanager-tests

api:
	@echo "${bold}${red}(A1/6)${reset} ${yellow}Test API Listener"
	@cd API && ./test_apilistener.sh
	@echo "${bold}${red}(A2/6)${reset} ${yellow}Test API getConfig"
	@cd API && ./test_getConfig.py
	@echo "${bold}${red}(A3/6)${reset} ${yellow}Test API getLastTWCResponse"
	@cd API && ./test_getLastTWCResponse.py
	@echo "${bold}${red}(A4/6)${reset} ${yellow}Test API getPolicy"
	@cd API && ./test_getPolicy.py
	@echo "${bold}${red}(A5/6)${reset} ${yellow}Test API getSlaveTWCs"
	@cd API && ./test_getSlaveTWCs.py
	@echo "${bold}${red}(A6/6)${reset} ${yellow}Test API getStatus"
	@cd API && ./test_getStatus.py

ems:
	@echo "${bold}${red}(E1/2)${reset} ${yellow}Starting EMS Test Web Server"
	@cd EMS && ./ems_emulator.py &
	@echo "${bold}${red}(E2/2)${reset} ${yellow}Testing SmartPi EMS Module"
	cd EMS && ./test_SmartPi.py

wait:
	@echo "${bold}${red}(M2/2)${reset} ${yellow}Wait for TWCManager to start"
	@sleep 120
