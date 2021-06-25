## Introduction

The Debug Interface provides advanced control over TWCs managed by TWCManager. In normal operation, it is rare to require the use of these advanced interfaces, however if you have a use case that isn't covered by the TWCManager defaults, you may choose to make modifications using the Debug interface.

## Sending Debug Commands

The Send Debug Commands function is a powerful interface to allow direct querying of TWCs using commands that provide visibility of internal settings and values within the TWC.

### Warning

There are several known commands which do cause damage to TWCs! These are blocked by the TWCManager Debug Interface and will result in a warning being printed and the command being ignored, however there may be other commands that we are not aware of that could damage your TWC, and as a result you should limit your commands to known commands.

## Advanced Settings
### Spike Amps

The Spike Amps option in advanced settings allows you to configure when the TWCManager will spike the power offered to the vehicle in order to ensure that the vehicle charges at the highest offered rate wherever possible.

There are a number of scenarios in which it has been identified that Tesla vehicles may require this spike in order to react to the change in power offering.

There are two options that may be tuned:

   * Proactively

TWCManager will proactively spike the amps offered to TWCs where the amps offered are not greater than a certain value. This avoids situations where vehicles may get "stuck" on the lower power offering.

   * Reactively

Reactive amp spiking is where a vehicle is detected as being "stuck" on a given offering. If we have increased our offering and the vehicle has not responded for some time, a spike in the offered amps is used to "reset" the vehicle's charge rate.
