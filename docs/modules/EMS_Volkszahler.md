# Volkszahler

The Volkszahler EMS module allows reading of a meter value from the Volkszahler platform which represents the Solar Generation value for a meter managed by Volkszahler.

## Configuration

The following table shows the available configuration parameters for the Volkszahler EMS Module:

| **Parameter** | **Value** |
| ------------- | --------- |
| enabled       | *required* Boolean value, ```true``` or ```false```. Determines whether we will poll the Volkszahler Server |
| serverIP      | *required* The IP address of the Volkszahler server that we will query for the generation value |
| serverPort    | *required* The Server Port that we will query. This is the port that the front-end UI uses, not the VZLOGGER port. |
| uuid          | *required* The UUID of the channel "Total Consumption" of your houshold grid meter.

## UUID Creation

The following steps explain how to create the Channel in Volkszähler

   * Step 1: open Frontend and click "Kanal hinzufügen"(= add channel)
   * Step 2: in next window select tab "Kanal erstellen" (= create new channel) and fill any parameter.
Then the channel got a new random UUID (is like GUID)
   * Step 3: after the dialog was closed is the channel was added below and an the mot richt column is a blue "i" : There you can read the new UUID.
   * Step 4: Now edit the VZLOGGER config file. Here you fill in the UUID and define where you get data and the format. 

Then the VZLOGGER service will do the rest. VZLOGGER is best for reading electricity meters (there exist also plugin for OCR reading from Video). Since data is pushed by a simple URL to database, you can also use any own active device, which knows the syntax.

My electricity meter has 4 readings: 3 counters kWh and a Watt display. You have to try baud, parity, protocol and other stuff to find correct format.
My electricity meter Watt display show + and - , some have two separate values both +, this depend on the meter manufacturer.

Url to try out reading: http://<your volkszähler ip-address>/api/data.txt?from=now&uuid=00000000-1111-1670-ffff-0123456789ab
Use your own UUID of the channel "Total Consumption" of your houshold grid meter. (see at blue "i")
Reading must be negative on "Consumption < solar production". TWCManager uses negative value as "green energy".
If you have only positive value than just create a new virtual channel fill in 'Regel'(=calulation formula): "-val(in1)"
Example reading: "-5520.8 W" (=Watt).
