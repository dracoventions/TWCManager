#!/usr/bin/python3

from setuptools import setup, find_namespace_packages

setup(
    name="TWCManager",
    version="1.2.4",
    package_dir={"": "lib"},
    packages=find_namespace_packages(where="lib"),
    python_requires=">= 3.4",
    include_package_data=True,
    # Dependencies
    install_requires=[
        "commentjson < 0.9.0; python_version < '3.6'",
        "commentjson >= 0.8.3; python_version >= '3.6'",
        "cryptography==2.1.4; python_version < '3.6'",
        "cryptography<3.4; python_version >= '3.6'",
        "growattServer>=1.0.0",
        "jinja2==2.11.2; python_version == '3.4'",
        "jinja2==2.11.2; python_version == '3.5'",
        "jinja2>=2.11.2; python_version >= '3.6'",
        "MarkupSafe < 2.0.0; python_version < '3.6'",
        "ocpp",
        "paho_mqtt>=1.5.0",
        "psycopg2 <= 2.8.6; python_version < '3.6'",
        "psycopg2; python_version >= '3.6'",
        "pyModbusTCP>=0.1.8",
        "pymysql==0.9.3; python_version < '3.6'",
        "pymysql; python_version >= '3.6'",
        "pyserial>=3.4",
        "requests>=2.23.0",
        "sentry_sdk>=0.11.2",
        "sysv_ipc < 1.1.0; python_version < '3.6'",
        "sysv_ipc >= 1.0.1; python_version >= '3.6'",
        "termcolor>=1.1.0",
        "websockets==7.0; python_version < '3.6'",
        "websockets>=9.1; python_version >= '3.6'",
        "ww>=0.2.1"
    ],
    # Package Metadata
    author="Nathan Gardiner",
    author_email="ngardiner@gmail.com",
    description="Package to manage Tesla Wall Connector installations",
    keywords="tesla wall connector charger",
    url="https://github.com/ngardiner/twcmanager",
)
