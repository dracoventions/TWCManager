# Configuration Examples

## Introduction

## Export Limited Solar Installations

In some cases, solar installations may be limited in export tariffs by an electricity provider due to high solar export concentrations in an area.

   * What this might look like: You may have 10kW (41A at 240v) of peak generation capability through your solar panels, however your distributor may advise you that they will not pay for or accept export above 5kW (~20A) from your property. This effectively means that your solar PV generation above 5kWh is "lost".
   * Aim: To utilize as much of the lost export for vehicle charging as possible, whilst exporting as much energy as possible within the exportable range.
   * Considerations: We have the option to tune the charging to utilize flex power when charging starts. Rather than waiting for an entire 6A of generation above the intial 5kW to become available before we start charging, we can use flex to start charging just after we cross the 5kW threshold, which will dip into the exportable energy when we first start charging, but will give us a nice charge curve throughout the day.
   * Outcome: We will set a static 5kW consumption value, which makes it appear to TWCManager that we are already consuming 5kW of the 10kW generation. Any household consumption will then be added on top of this value. This would leave a maximum of 5kWh (21A) for charging, which is higher than ```minAmpsPerTWC = 6``` in our (EU) TWC example, and will allow us to start charging once 5kW is being generated - obviously you may change these values to suit your environment.
      * We will use flex charging to allow the charge to "dip" into up to 5kW of generation below the 5kW threshold to begin charging. The logic behind this is that once we have reached the threshold to start charging we can be relatively confident of remaining in positive generation throughout the day, however we may have short variances and a ramp-up period to get to peak generation. If we stop charging for every variance in output that puts us below 5kW, we're potentially then exporting up to 6.44kW of energy (5kW + 6A above export level), 1.44kWh of which is entirely wasted as it doesn't get counted toward export tariff, so dipping into up to 5A of exportable energy to keep from losing 6A of non-exportable energy is a reasonable balance to strike.


```
  "minAmpsPerTWC": 6,
  "greenEnergyFlexAmps": 5
```

   * Via the web interface, set a Consumption Offset in watts of 5000W

This will have the following effect:

   * Charging will not *start* until the generated energy is at least 20A (```minAmpsPerTWC``` being 6A and after the 5kW of consumption offset that we have configured).
   * Once charging has started, ```greenEnergyFlexAmps``` controls how low the generation can go without charging stopping. As ```greenEnergyFlexAmps``` is set to 5, this means that the generation can get as low as 16A without charging stopping (to account for cloud or conditions changing, or appliance loads). This ensures that we are always exporting at least 16A of the 20A exportable energy. 

The below shows an illustration of how this configuration improves the effeciency of this setup, by starting charging after the orange band (which is 5kW of generation) and stopping it at the same point at the end of the day. This results in avoiding the loss of exports between the orange (5kW) and green (5kW + 6A minAmpsPerTWC) bands.

[Illustration of Charge Curve](charge_curve.png)
