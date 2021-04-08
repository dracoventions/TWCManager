#!/usr/bin/python3

from setuptools import setup, find_namespace_packages

setup(
    name="TWCManager",
    version="1.2.2",
    package_dir={"": "lib"},
    packages=find_namespace_packages(where="lib"),
    # Dependencies
    install_requires=[
        "commentjson>=0.8.3",
        "jinja2==2.11.2",
        "ocpp",
        "paho_mqtt>=1.5.0",
        "pyModbusTCP>=0.1.8",
        "pymysql", 
        "pyserial>=3.4",
        "requests>=2.23.0",
        "sentry_sdk>=0.11.2",
        "sysv_ipc>=1.0.1",
        "termcolor>=1.1.0",
# Not adding this dependency yet, it is neede for OCPP but will stop this
# project from working for those using Python 3.5
#        "websockets",
        "ww>=0.2.1"
    ],
    # Package Metadata
    author="Nathan Gardiner",
    author_email="ngardiner@gmail.com",
    description="Package to manage Tesla Wall Connector installations",
    keywords="tesla wall connector charger",
    url="https://github.com/ngardiner/twcmanager",
)
