# Default Policies

TWCManager ships with a set of four default policies which can be controlled by
the web interface:

- **Charge Now** charges at the maximum speed supported by the connector for 24
  hours when requested by the web interface
- **Scheduled Charging** charges at a specified rate during a timeframe
  specified on the web interface
- **Track Green Energy** attempts to route excess solar production to your car's
  battery during hours when solar production is likely
- **Non-Scheduled Charging** charges at a specified rate (typically zero) at all
  other times

The basic properties of these policies are set through the web interface, but can
be further adjusted using the config file.

## Additional Restrictions

If you want to impose additional restrictions on when these policies run, use
the `restrictions` node in the config file.  For example:

    "restrictions":{
      "Charge Now":{
        "match":[ "modules.TeslaPowerwall2.gridStatus" ],
        "condition":[ "eq" ],
        "value":[ true ]
      }
    }

This prevents the Charge Now policy from matching when the Powerwall EMS reports that
there is a utility outage.  See a more detailed description of policy restrictions
in the custom policy section.

Note:
: If no policy matches, the last policy chosen continues to apply despite its
  conditions no longer matching.  This is probably not what you want.  This
  cannot happen unless additional restrictions are added to the "Non-Scheduled
  Charging" policy or you have fully replaced the set of policies. Therefore,
  neither of these is recommended.

## Charge Limits

Each of these policies has the ability to apply a different charge limit to your
vehicle when the policy comes into effect.  For instance, you might charge to
50% during scheduled charging to ensure the car always has plenty of range, but
charge up to 90% if excess solar production permits.

These limits are GPS-based.  They will be applied to cars at home when the
policy changes, and to cars which arrive while the policy is in effect.  The
car's original charge limit is remembered and restored when the car leaves or
when a new policy does not apply a limit.

Acceptable values are 50-100; -1 means not to apply a limit / restore the car's
original limit.

These limits are not exposed through the web interface, but can be configured in
the `config.json` file:

- `chargeNowLimit`
- `scheduledLimit`
- `greenEnergyLimit`
- `nonScheduledLimit`

## Latching

Sometimes, the conditions that trigger a policy could cause those conditions no
longer to be true.  This does not occur with the built-in policy conditions, but
could with custom conditions.  For example, a policy that allows charging when
power is being exported could increase consumption and eliminate the export.

Alternatively, you might have a condition which occasionally fails to match. If
you restrict Track Green Energy to run only when generation is above a certain
level, a passing cloud might cause you to exit and later re-enter the policy.

To handle these cases, policies support latching.  When a policy is defined to
latch, the conditions are treated as continuing to be true for a specified
number of minutes after they last evaluated true.

Note:
: This does not prevent a policy change if an earlier policy's conditions become
  true.  It also does not prevent the Track Green Energy policy from deciding
  there is insufficient power to charge, but see Flex below.

Caution:
: Exercise care with latching.  If a policy is restricted to apply only when the
  grid is online, but latches, it will continue operating during the beginning
  of a grid outage.

The Track Green Energy policy can be latched using the `greenEnergyLatch` value.
Custom policies can be latched using the `latch_period` attribute.

## Flexibility

The Track Green Energy policy attempts to send only excess power to the car.
However, on cloudy days, this power might be inconsistent.  Setting an amount of
Flex current permits the policy to continue charging at the minimum rate,
drawing up to the specified amount from the grid, even if Green Energy becomes
insufficient temporarily.

The policy will stop charging if available power drops too low even with the
flex, and will not wake a car to start charging until there is sufficient power
without considering the flex.

Flex for the Track Green Energy policy can be set using the
`greenEnergyFlexAmps` value; custom policies can include an `allowed_flex`
attribute.

## Webhooks

If you want to trigger external actions based on TWCManager state changes
(home automation, IFTTT, etc.), you can define a set of webhooks on each
policy.  The URL you supply will receive a POST with the TWCManager status
on the event you select.

For each policy, the events are:

- "enter" when the policy becomes selected
- "start" when a vehicle begins charging with this policy selected
- "stop" when a vehicle stops charging with this policy selected
- "exit" when the policy is no longer selected

For example, suppose Scheduled Charging is configured to charge for one hour
beginning at midnight.  Two vehicles are connected, and one reaches its charge
limit during this time.  The events fired would be:

- "enter" for Scheduled Charging at midnight
- "start" for Scheduled Charging when a vehicle begins charging shortly after
  midnight; occurs twice
- "stop" for Scheduled Charging when the first vehicle reaches its charge limit
- "exit" for Scheduled Charging at 1 AM
- "enter" for Non Scheduled Charging at 1 AM
- "stop" for Non Scheduled Charging shortly after 1 AM when the second
  vehicle stops due to the policy change

Note that stops which occur due to the policy change will be attributed to the
new policy.

Webhooks can be set for built-in policies using the `webhooks` node under
`policy.extend` in the `config.json` file.  For example:

    "webhooks": {
      "Scheduled Charging": {
        "start": "http://IP/apps/api/737/trigger?access_token=TOKEN",
        "exit": "http://IP/apps/api/866/trigger?access_token=TOKEN",
        "stop": "http://IP/apps/api/866/trigger?access_token=TOKEN",
      }
    }

For custom policies, they can be set using the `webhooks` property of the
policy.

# Defining Custom Policies

If you wish to add additional policies, they can be specified in the
`config.json` file as well.

## Anatomy of a Policy

Here is a simple policy:

    { "name": "Storm Watch",
      "match": [ "modules.TeslaPowerwall2.gridStatus", "modules.TeslaPowerwall2.stormWatch" ],
      "condition": [ "eq", "eq" ],
      "value": [ true, true ],
      "charge_amps": "settings.chargeNowAmps",
      "charge_limit": 90
    }

The values in a policy definition are:

- `name`: The name of the policy, shown in the console output of TWCManager
- `match`:  An array of policy values to be tested
- `value`:  A corresponding array of values to be tested against
- `condition`:  An array of relationships between `match` and `value` elements for the
  policy to apply
- `charge_amps`:  The maximum current to permit while the policy is in effect
- `charge_limit`:  The charge limit to apply to vehicles while the policy is in
  effect (optional)
- `background_task`:  A background task to be run periodically while the policy
  is in effect (optional)
- `latch_period`:  If the conditions for this policy are ever matched, treat
  them as matched for this many minutes, even if they change. (optional)
- `allowed_flex`:  If the available current is reduced below the minimum for
  charging, continue to supply the minimum.  Only useful for policies where the
  charge amps vary.
- `webhooks`:  An object containing desired webhooks for the policy.  See above.

### Policy Values

`match` and `value` can contain several different properties to check.

- Literal strings or numbers
- `now`: The current time as seconds past the epoch
- `tm_hour`:  The current hour as an integer (0-23)
- `config.*`: Retrieves a value from `config.json`
- `settings.*`:  Retrieves a value from `settings.json`
- `modules.*`:  Retrieves a value exposed by the specified module.  Some useful
  module properties are:
  - From `TeslaPowerwall2`:
    - `gridStatus`:  `True` if the grid is up and working properly; `False` if
      disconnected
    - `batteryLevel`:  Current charge state (0-100); note that this does not
      precisely match the value displayed in the Tesla app
    - `operatingMode`:  Current operating mode; one of `self_consumption`,
      `backup`, or `autonomous` (Advanced Time-of-Use)
    - `reservePercent`:  The percentage to reserve for backup events
    - `stormWatch`:  Whether Storm Watch is currently in effect
  - From `TeslaAPI`:
    - `numCarsAtHome`:  The number of (Tesla) vehicles currently believed to be
      at home
    - `minBatteryLevelAtHome`:  The lowest battery level (0-100) of any Tesla
      currently believed to be at home; `10000` if unknown / no cars are home.
- Sub-lists

(Note that TWCManager does not know which vehicle is connected to which TWC, so
only aggregate properties of all vehicles at home can be accessed.)

### Comparisons

The comparisons which can be employed are:

- `gt`: Match must be greater than value
- `gte`: Match must be greater than or equal to value
- `lt`: Match must be less than value
- `lte`: Match must be less than or equal to value
- `eq`: Match must be equal to value
- `ne`: Match must not be equal to value
- `false`: Never true, regardless of values
- `none`: Always true, regardless of values

### Grouping of Requirements

The top-level list of requirements are AND'd together.  If a sub-list is used,
the sub-list is OR'd together; further sub-lists continue to alternate AND/OR.
Here is a more complex policy which combines conditions:

    { "name": "Powerwall Full",
      "match": [
        "modules.TeslaPowerwall2.batteryLevel",
        [ "modules.TeslaPowerwall2.exportW",
          "modules.TeslaPowerwall2.gridStatus" ] ],
      "condition": [ "gte", [ "gte", "eq" ] ],
      "value": [ 95, [ 1500, false ] ],
      "charge_amps": "config.minAmpsPerTWC",
      "charge_limit": 90,
      "latch_period": 30
    }

This policy will match when the Powerwall battery level is at least 95%, and either
power is being exported to the grid or the grid is unavailable.

### Background Tasks

Most policies will not require a background task.  There are two exceptions:

- If defining a policy that behaves like **Track Green Energy**, the background
  task `checkGreenEnergy` will track generation and consumption metrics from the
  configured EMS plugins.  Do not set `charge_amps`; the background task will
  update it each time it runs.
- If defining a policy that depends on `modules.TeslaAPI.minBatteryLevelAtHome`,
  the background task `checkCharge` will track the charge state of cars at home
  more closely while the policy is selected.

## Policy Extension Points

The simplest way to extend the default policies is to insert additional ones.
There are three extension points:

- `emergency` defines policies which apply before **Charge Now**, meaning they
  override explicit user commands.  Define policies here which should abort a
  manual charge command, such as not charging during a grid outage.
- `before` defines policies which apply between **Charge Now** and **Scheduled
  Charging**.  Define policies here which are exceptions to your normal schedule,
  such as charging at full speed when the battery is extremely low.
- `after` defines policies which apply between **Track Green Energy** and
  **Non-Scheduled Charging**.  Define policies here which augment your daily
  schedule.

## Policy Replacement

If you have unusual policy requirements, you can instead replace the built-in
policies.  Note that if you still need any of the default policies, you will
need to re-define them yourself.  For your convenience, the default policies are
present in `config.json` to use as a starting point.

**This is not recommended.**  The default policies will be improved over time,
while your copies of them will be left unchanged.