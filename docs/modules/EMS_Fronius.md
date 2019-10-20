# Fronius Inverter EMS Module

## Introduction

### Note

In many Fronius installations, the installation will involve a Fronius Meter mounted within the electricity meter box. If you have one of these installed, it will be between 2-4 DIN slots wide, with an LCD screen showing metering information, and will have a model number similar to 63A-1 or 63A-3.

If you have such a meter installed, you are able to obtain Consumption information via the Fronius interface, and it is likely that the TWC's power draw is being metered. If this is the case, the TWC's load will show as Consumption via the Fronius EMS module. If this is the case, please ensure the following configuration setting is enabled in your ```config.json``` file:

```
{
    "config": {
        "subtractChargerLoad": true
    }
}
```

### Status

| Detail          | Value                          |
| --------------- | ------------------------------ |
| **Module Name** | Fronius                        |
| **Module Type** | Energy Management System (EMS) |
| **Features**    | Consumption, Generation        |
| **Status**      | Implemented, Mature, Tested    |
