install:

        sudo apt-get install -y lighttpd php7.0-cgi
        sudo lighty-enable-mod fastcgi-php ; exit 0
        sudo service lighttpd force-reload

        sudo chown -R www-data:www-data /var/www/html
        sudo chmod -R 665 /var/www/html
        sudo usermod -a -G www-data pi

        sudo cp HTML/* /var/www/html/
