# MySQL Logging

## Introduction

The MySQL logging module allows the storage of statistics in a MySQL database either locally or on a remote machine.

This module is disabled by default. You might want this module enabled in your environment if you would like to log statistics from your TWCManager installation. In particular, you may find this module useful if you would like to log externally to the device you are running TWCManager on.

## Dependency Warning

There is an extra python3 dependency required if you would like to use MySQL as a Logging module, this is not installed automatically using setup.py:

```pip3 install pymysql```

## Configuration Options

The following configuration parameters exist for this logging module:

| Option   | Example | Description |
| -------- | ------- | ----------- |
| database | *twcmanager* | *required* The name of the database that you would like to log to on the MySQL host. |
| enabled  | *false* | *required* Boolean value determining if the console logging module should be activated. The default is *false*. |
| host     | *10.10.10.5* | *required* The hostname or IP address of the MySQL server that you would like to log to. |
| password | *abc123* | *required* The password to use. |
| username | *twcmanager* | *required* The username to use. |

### Muting Logging Topics

Logging modules allow for the individual toggling of certain topics to filter output. This is entirely optional and will default to output of all topics if it does not exist under the module's configuration. Below are the topics that may be toggled:

```
"mute":{
   "ChargeSessions": false,
   "GreenEnergy": false,
   "SlavePower": false,
   "SlaveStatus": false
}
```

Setting a topic to true will cause that topic's output to be muted.

### Example Configuration

```
"logging":{
    "MySQL": {
        "enabled": false,
        "host": "1.2.3.4",
        "database": "twcmanager",
        "username": "twcmanager",
        "password": "twcmanager"
    }
```

## Database Schema

Unlike the SQLite database, the MySQL database logging module currently requires that you create the database schema manually from the SQL below on the target database server.

The following is the database schema for **v1.2.0** of TWCManager 

```
CREATE TABLE charge_sessions (
  chargeid int,
  startTime datetime,
  startkWh int,
  slaveTWC varchar(4),
  endTime datetime,
  endkWh int,
  vehicleVIN varchar(17),
  primary key(startTime, slaveTWC)
);

CREATE TABLE green_energy (
  time datetime,
  genW DECIMAL(9,3),
  conW DECIMAL(9,3),
  chgW DECIMAL(9,3),
  primary key(time)
);

CREATE TABLE slave_status (
  slaveTWC varchar(4), 
  time datetime, 
  kWh int, 
  voltsPhaseA int, 
  voltsPhaseB int, 
  voltsPhaseC int, 
  primary key (slaveTWC, time));
```
