#!/usr/bin/python3

from setuptools import setup, find_namespace_packages

setup(
    name="TWCManager",
    version="1.2.4",
    package_dir={"": "lib"},
    packages=find_namespace_packages(where="lib"),
    python_requires=">= 3.6",
    include_package_data=True,
    # Dependencies
    install_requires=[
        "cryptography<3.4",
        "growattServer>=1.0.0",
        "jinja2>=2.11.2",
        "ocpp",
        "paho_mqtt>=1.5.0",
        "psycopg2",
        "pyModbusTCP>=0.1.8",
        "pymysql",
        "pyserial>=3.4",
        "pyyaml",
        "requests>=2.23.0",
        "sentry_sdk>=0.11.2",
        "sysv_ipc",
        "termcolor>=1.1.0",
        "websockets<=9.1; python_version == '3.6'",
        "websockets>=9.1; python_version >= '3.7'",
    ],
    # Package Metadata
    author="Nathan Gardiner",
    author_email="ngardiner@gmail.com",
    description="Package to manage Tesla Wall Connector installations",
    keywords="tesla wall connector charger",
    url="https://github.com/ngardiner/twcmanager",
)
