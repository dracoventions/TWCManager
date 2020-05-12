# Troubleshooting

## First Steps

### Debug Level

Before undertaking any troubleshooting, the number one most useful piece of informaton to have on hand is a lot with the debugLevel turned up high. 

To make sure you capture everything, set debugLevel to 11 in ```/etc/twcmanager/config.json``` and run TWCManager in the following way to log the output:

```python -u -m TWCManager | tee debug.log```

Please provide the log output when you [raise an issue on GitHub](https://github.com/ngardiner/TWCManager/issues/)! This information is most useful in diagnosing a problem.

### TWCManager Version

Are you using the development version of TWCManager? If so, and if you are having issues, please switch to the Stable version and see if it is working. If so, you've found a bug! Please [raise an issue on GitHub](https://github.com/ngardiner/TWCManager/issues/) and let us know.

## Adapter

   * The required adaptor for this communication is an **RS485** adaptor. Be careful that you are not using an RS232 adaptor which is more common, but which uses a different duplexing system and uses more pins to communicate.

   * If you did happen to use an RS232 adaptor, you may decode the communications correctly, but you will likely have issues with transmissions (due to the lack of RTS/CTS signalling and half-duplex operation)

   * Known working adapters include:

      * USB-RS485-WE-1800-BT 
      * JBtek USB to RS485 Converter Adapter ch340T
      * DSD TECH USB 2.0 to RS485 Serial Data Converter CP2102
      * Raspberry Pi RS422 RS485 Shield

## Wiring

   * There are two In and two Out pins for RS485 Master/Slave configuration on a V2 TWC. The important detail is the polarity (+/-) of each wire, it does not effectively matter which of the 2 pairs of pins you use for TWCManager communications.

   * The following diagram gives a good overview of the Half-Duplex system used for TWC communication: https://zone.ni.com/reference/en-XX/help/373197L-01/lvaddon11/987x_halfduplex/

   * In some cases, messages can become corrupted unless a 120 ohm resistor is placed in parallel between the TX and RX lines. The following diagram (see the Half-Duplex diagram) provides a good overview of this: https://zone.ni.com/reference/en-XX/help/373197L-01/lvaddon11/987x_rs485termination/

   * Similarly, some installations have seen corruption unless 680 ohm "bias" resistors are wired between the D+ (usually orange) wire and the Red (+5v) wire, and the D- (usually yellow) wire and Black (Gnd) wire.

   * You should twist the pair of wires around each other to avoid cross-talk. As short as 6 inches of non-twisted wire is enough to cause cross-talk corruption. In addition, you should avoid long cable runs wherever possible.

   * Check your terminals to ensure they are tightly screwed or wound.

## Messages

The TWCManager communications protocol consists of messages sent back and forward between Master and Slave. Observing these messages will assist to identify issues with your configuration.

### Slave Linkready

The Slave linkready message is:

```fd e2 .. .. .. .. .. 00 00 00 00 00 00```

(The .. sections being the Slave ID, Sign and Maximum Amps)

This is sent when:

   * The slave is first powered on and is looking to link to a master
   * The master stopped communicating with the slave for 30 seconds.

If you are seeing repeated Slave Linkready messages (x amp slave TWC is ready to link) in the logs with your debugLevel set to 1 or more, this signals that an issue with communications is stopping your TWCManager from managing the Slave TWC.

### Unknown Message Type

When a message is recieved which does not match the currently known message types, TWCManager will log ```*** UNKNOWN MESSAGE FROM SLAVE:```

These messages are particularly important when debugging communication, as they either signal:

   * A new message from a Slave that doesn't match previously known protocol signatures was recieved (unlikely), or
   * There is some issue with the wiring between the TWCs that causes the messages to be recieved in a corrupted form, or to run into one another.

### Checksum incorrect

If you see Checksum does not match messages, it means the checksum bit is not correct when computed from the data sent. This is a very strong sign of corruption between TWCManager and the Slave TWC(s).

The recommendation here is to refer to the cabling section above and ensure everything is per the recommendations there.

## LED Lights

The LED lights on the TWC are useful for debugging what is happening.

   * Continuous blinking red light on the TWC suggests that it is in slave mode and has not been in communication with a master for 30 seconds or more.
