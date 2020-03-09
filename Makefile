install:

	sudo apt-get update
	sudo apt-get install -y lighttpd php7.3-cgi screen git
	sudo lighty-enable-mod fastcgi-php ; exit 0
	sudo service lighttpd force-reload

	sudo cp html/* /var/www/html/
	sudo chown -R www-data:www-data /var/www/html
	sudo chmod -R 665 /var/www/html
	sudo usermod -a -G www-data pi

	# Install TWCManager packages
	./setup.py install

	# Create configuration directory
	sudo mkdir /etc/twcmanager
	sudo cp etc/twcmanager/config.json /etc/twcmanager/
	sudo chown root:pi /etc/twcmanager -R
