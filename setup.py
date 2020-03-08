#!/usr/bin/python3

from setuptools import setup, find_packages
setup(
    name="TWCManager",
    version="1.1.7",
    packages=find_packages(),

    # Dependencies
    install_requires = [
      "commentjson",
      "json"
    ],

    # Package Metadata
    author="Nathan Gardiner",
    author_email="ngardiner@gmail.com",
    description="Package to manage Tesla Wall Connector installations",
    keywords="tesla wall connector charger",
    url="https://github.com/ngardiner/twcmanager"
)
