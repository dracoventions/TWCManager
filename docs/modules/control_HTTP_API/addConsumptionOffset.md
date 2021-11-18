# addConsumptionOffset API Command

## Introduction

The addConsumptionOffset API command requests TWCManager to add a new consumption offset, or edit an existing consumption offset. The Primary Key is the name of the offset.

## Format of request

The addConsumptionOffset API command is accompanied by a payload which describes the offset that you are configuring or editing. The following example payload shows a request to add or edit an offset called WattsOffset with a positive offset expressed in watts:

```
{
  "offsetName": "WattsOffset",
  "offsetValue": 500.5,
  "offsetUnit": "W"
}
```

   * Offsets can be expressed in either Amps or Watts.
   * Offsets can be either positive (count as consumption) or negative (count as generation)

An example of how to call this function via cURL is:

```
curl -X POST -d '{ "offsetName": "WattsOffset", "offsetValue": 500.5, "offsetUnit": "W" } http://192.168.1.1:8080/api/addConsumptionOffset

```

This would instruct TWCManager to add or edit the offset described above.

## Integration with other platforms

This API function can be called by external systems in order to control the charge rate of your TWC. This doesn't require any EMS modules or charging schedule, you can simply set your non-scheduled charging mode to Track Green Energy and then have the external system update an offset to either a negative (generation) or positive (consumption) value, and TWCManager will treat this value as if it were reported by an EMS and charge accordingly.

## Disabling an offset

Set an offset's value to 0 (zero) to disable it.

## Deleting an offset

See the [deleteConsumptionOffset](deleteConsumptionOffset.md) API call.
