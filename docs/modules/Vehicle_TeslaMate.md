# TeslaMate Vehicle Integration

## Introduction

<a href="https://github.com/adriankumpf/teslamate">TeslaMate</a> is a self-hosted Tesla datalogger.

The purpose of this integration is to allow users of TWCManager who also use <a href="https://github.com/adriankumpf/teslamate">TeslaMate</a>

## Integrations

### Tesla API Tokens

TWCManager can synchronize the TeslaMate API tokens from the TeslaMate database. This allows token management to be performed on our behalf by TeslaMate rather than within TWCManager.

This is performed through direct queries of the TeslaMate database, and is not used by the telemetry feature of the TeslaMate module, which is separate. You do not need to use the API Token sync function even if you do use the telemtry sync function.

Please note that turning on the Token Sync functionality of this module will have the following affect on TWCManager's Tesla API token handling functionality:

   * You will no longer be prompted for your Tesla API login. Even if the TeslaMate tokens are invalid, you will not be prompted.
   * TWCManager will not refresh API tokens, however on refresh of the TeslaMate token, the token will be used by TWCManager.

#### Configuration

```
   "vehicle": {
       "TeslaMate": {
           "enabled": true,
           "syncTokens": true,
           "db_host": "192.168.1.1",
           "db_name": "teslamate",
           "db_pass": "teslamate",
           "db_user": "teslamate"
       }
   }
```

#### Access to Database Instance

By default, TWCManager may not be able to access the database for TeslaMate.

Depending on your TeslaMate installation type, you may need to take different steps to make the PostgreSQL database available to TWCManager in order to sync Tesla auth tokens. Follow the appropriate section below for your installation type.

##### Manual Installation

For a manual installation, the ```/etc/postgresql/pg_hba.conf``` file will need to be updated to allow the TWCManager host to connect remotely to the database.

Add the following line below to pg_hba.conf, substituting the IP address of your TWCManager machine:

```
host    teslamate       teslamate       192.168.1.1/32        md5
```

After adding this, reload the PostgreSQL configuration:

```
service postgresql reload
```

##### Docker Installation

To be updated

### Telemetry Information

TWCManager can use the MQTT topics advertised by TeslaMate to recieve charge state and SoC information from your vehicle

Note: This functionality is not yet available. This guide will be updated once it is.
