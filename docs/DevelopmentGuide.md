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

### Debug Levels

Currently, there are inconsistent debug levels used throughout the project. This has been flagged as a high priority area of improvement. The following tables aim to clarify 

#### Core (TWCManager, TWCMaster, TWCSlave)

| Debug Level | Used for |
| ----------- | -------- |
| 1           | Notification to users, initialization messages and errors |
| 1           | Confirmation of policy selection |
| 2           | Internal error/parameter issue eg missing value for *internal* function call |
| 7           | Policy selection, module loaded |
| 8           | Policy parameter comparison and non-selection of policy |
| 10          | Loop entry, loop exit debugs |
| 11          | Developer-defined debug checkpoints/output/etc |

#### Modules (Control, EMS, Status)

| Debug Level | Used for |
| ----------- | -------- |
| 1           | Critical error which prevents module functionality (eg. not configured / incorrect config |
| 10          | Loop entry, loop exit debugs |
| 11          | Developer-defined debug checkpoints/output/etc |

### When working with persistent values (config/settings)

The values which are stored in the config and settings dicts are interpreted from JSON storage after each restart. This can cause an issue, in that whilst they are a true representation of the data 
