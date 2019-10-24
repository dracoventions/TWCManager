# Web IPC Control Module

## Introduction

The Web IPC Control module allows control of the TWCManager Tesla Wall Charger controller via an external HTTP web server, using PHP scripts. This is the web interface that was used in cdragon's TWCManager fork.

This offers decoupling of the Web Server component from TWCManager.

### HTTP Control Module vs IPC Web Interface

There are two separate interfaces for managing TWCManager via web browser. These are:

   * WebIPC - The original web interface bundled with TWCManager
   * HTTPControl - The new in-built web interface
   
**Benefits of WebIPCControl**

   * Supports HTTPS (when used with a HTTPS-capable Web Server)

**Drawbacks of WebIPCControl**

   * More complex - requires additional administration of a web server to operate.

### Status

| Detail          | Value          |
| --------------- | -------------- |
| **Module Name** | WebIPCControl  |
| **Module Type** | Status         |
| **Status**      | In Development |
