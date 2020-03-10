# Development Guide

## Introduction

Welcome to TWCManager development, and a very big thank you for your contribution to the project. This guide is intended to kick-start development efforts by acting as a knowledgebase for useful details about developing for TWCManager.

## Testing & Developing

The easiest way to maintan and test a TWCManager source tree is to run the TWCManager.py script directly from the repository directory. For example:

### Cloning Git Repository

```
git clone https://github.com/ngardiner/TWCManager
cd TWCManager
```

### Make changes

This is your working branch of the repository.

### Running the script locally

```
./TWCManager.py
```

### Adding new python dependencies

Python dependencies are documented in the setup.py script.

## Conventions

### When working with persistent values (config/settings)

The values which are stored in the config and settings dicts are interpreted from JSON storage after each restart. This can cause an issue, in that whilst they are a true representation of the data 
