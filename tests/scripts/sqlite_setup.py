#!/usr/bin/env python3

import subprocess

def execute_query(query, database):

    queryb = query.encode('utf-8')
    process = subprocess.Popen(['sqlite3', database],
                               stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT,
                               stdin=subprocess.PIPE)

    stdout, _ = process.communicate(input=queryb)

    if process.returncode != 0:
        print("Query failed: %s" % query)
        print("Output was: %s" % stdout)

execute_query("""CREATE TABLE charge_sessions (
  chargeid int,
  startTime datetime,
  startkWh int,
  slaveTWC varchar(4),
  endTime datetime,
  endkWh int,
  vehicleVIN varchar(17),
  primary key(startTime, slaveTWC)
);
""", "/etc/twcmanager/twcmanager.sqlite")

execute_query("""CREATE TABLE green_energy (
  time datetime,
  genW DECIMAL(9,3),
  conW DECIMAL(9,3),
  chgW DECIMAL(9,3),
  primary key(time)
);
""", "/etc/twcmanager/twcmanager.sqlite")

execute_query("""CREATE TABLE slave_status (
  slaveTWC varchar(4),
  time datetime,
  kWh int,
  voltsPhaseA int,
  voltsPhaseB int,
  voltsPhaseC int,
  primary key (slaveTWC, time)
);
""", "/etc/twcmanager/twcmanager.sqlite")
