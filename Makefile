install:

	sudo apt-get update
	sudo apt-get install -y lighttpd php7.3-cgi screen git python3-pip
	pip3 install pyserial
	pip3 install sysv_ipc
	sudo lighty-enable-mod fastcgi-php ; exit 0
	sudo service lighttpd force-reload
	
	sudo chown -R www-data:www-data /var/www/html
	sudo chmod -R 665 /var/www/html
	sudo usermod -a -G www-data pi
	
	sudo cp html/* /var/www/html/
	cp TWCManager.py /usr/bin/

	# Create configuration directory
	mkdir /etc/twcmanager
	cp etc/twcmanager/config.json /etc/twcmanager/
