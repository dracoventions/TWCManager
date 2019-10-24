# HTTP Control Module

## Introduction

The HTTP Control module allows control of the TWCManager Tesla Wall Charger controller via an in-built HTTP web server.

The web-server is multi-threaded (ie, it can be managed by multiple clients simultaneously), but does not support HTTPS encryption. It listens on Port 8080. As of release v1.1.5, it does not currently have any configurable options (but will in the future).

### HTTP Control Module vs IPC Web Interface

There are two separate interfaces for managing TWCManager via web browser. These are:

   * WebIPC - The original web interface bundled with TWCManager
   * HTTPControl - The new in-built web interface
   
**Benefits of HTTPControl**

   * Tightly integrated with the TWCManager controller. Less development lead-time to add functions.

**Drawbacks of HTTPControl**

   * Does not support HTTPS encryption.

### Status

| Detail          | Value          |
| --------------- | -------------- |
| **Module Name** | HTTPControl    |
| **Module Type** | Status         |
| **Status**      | In Development |
