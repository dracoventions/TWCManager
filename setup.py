#!/usr/bin/python3

from setuptools import setup, find_namespace_packages

setup(
    name="TWCManager",
    version="1.2.1",
    package_dir={"": "lib"},
    packages=find_namespace_packages(where="lib"),
    # Dependencies
    install_requires=[
        "commentjson>=0.8.3",
        "jinja2==2.11.2",
        "paho_mqtt>=1.5.0",
        "pyserial>=3.4",
        "requests>=2.23.0",
        "sysv_ipc>=1.0.1",
        "termcolor>=1.1.0",
        "ww>=0.2.1",
        "pyModbusTCP>=0.1.8",
    ],
    # Package Metadata
    author="Nathan Gardiner",
    author_email="ngardiner@gmail.com",
    description="Package to manage Tesla Wall Connector installations",
    keywords="tesla wall connector charger",
    url="https://github.com/ngardiner/twcmanager",
)
