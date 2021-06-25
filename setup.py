#!/usr/bin/python3

from setuptools import setup, find_namespace_packages

setup(
    name="TWCManager",
    version="1.2.3",
    package_dir={"": "lib"},
    packages=find_namespace_packages(where="lib"),
    python_requires=">= 3.4",
    # Dependencies
    install_requires=[
        "commentjson < 0.9.0; python_version < '3.6'",
        "commentjson >= 0.8.3; python_version >= '3.6'",
        "cryptography==2.1.4",
        "growattServer>=1.0.0",
        "jinja2==2.11.2",
        "MarkupSafe < 2.0.0; python_version < '3.6'",
        "ocpp",
        "paho_mqtt>=1.5.0",
        "pyModbusTCP>=0.1.8",
        "pymysql==0.9.3; python_version < '3.6'",
        "pymysql; python_version >= '3.6'",
        "pyserial>=3.4",
        "requests>=2.23.0",
        "sentry_sdk>=0.11.2",
        "sysv_ipc < 1.1.0; python_version < '3.6'",
        "sysv_ipc >= 1.0.1; python_version >= '3.6'",
        "termcolor>=1.1.0",
        "websockets; python_version >= '3.6'",
        "ww>=0.2.1"
    ],
    # Package Metadata
    author="Nathan Gardiner",
    author_email="ngardiner@gmail.com",
    description="Package to manage Tesla Wall Connector installations",
    keywords="tesla wall connector charger",
    url="https://github.com/ngardiner/twcmanager",
)
