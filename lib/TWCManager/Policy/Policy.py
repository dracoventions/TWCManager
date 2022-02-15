import logging
import time


logger = logging.getLogger("\u26FD Policy")


class Policy:

    active_policy = None

    # This is the default charge policy.  It can be overridden or extended.
    default_policy = [
        # The first policy table entry is for chargeNow. This will fire if
        # chargeNowAmps is set to a positive integer and chargeNowTimeEnd
        # is less than or equal to the current timestamp
        {
            "name": "Charge Now",
            "match": [
                "settings.chargeNowAmps",
                "settings.chargeNowTimeEnd",
                "settings.chargeNowTimeEnd",
            ],
            "condition": ["gt", "gt", "gt"],
            "value": [0, 0, "now"],
            "charge_amps": "settings.chargeNowAmps",
            "charge_limit": "config.chargeNowLimit",
        },
        # Check if we are currently within the Scheduled Amps charging schedule.
        # If so, charge at the specified number of amps.
        {
            "name": "Scheduled Charging",
            "match": ["checkScheduledCharging()"],
            "condition": ["eq"],
            "value": [1],
            "charge_amps": "settings.scheduledAmpsMax",
            "charge_limit": "config.scheduledLimit",
        },
        # If we are within Track Green Energy schedule, charging will be
        # performed based on the amount of solar energy being produced.
        # Don't bother to check solar generation before 6am or after
        # 8pm. Sunrise in most U.S. areas varies from a little before
        # 6am in Jun to almost 7:30am in Nov before the clocks get set
        # back an hour. Sunset can be ~4:30pm to just after 8pm.
        {
            "name": "Track Green Energy",
            "match": ["tm_hour", "tm_hour", "settings.hourResumeTrackGreenEnergy"],
            "condition": ["gte", "lt", "lte"],
            "value": [6, 20, "tm_hour"],
            "background_task": "checkGreenEnergy",
            "allowed_flex": "config.greenEnergyFlexAmps",
            "charge_limit": "config.greenEnergyLimit",
        },
        # If all else fails (ie no other policy match), we will charge at
        # nonScheduledAmpsMax, unless overridden with nonScheduledAction,
        # which may cause us to Track Green Energy instead.
        {
            "name": "Non Scheduled Charging",
            "match": ["settings.nonScheduledAction"],
            "condition": ["lt"],
            "value": [3],
            "charge_amps": "settings.nonScheduledAmpsMax",
            "charge_limit": "config.nonScheduledLimit",
        },
        # Non-Scheduled Track Green Energy (if configured)
        # If selected in the Web UI, instead of falling back to non-scheduled
        # amps, we'll fall back to non-scheduled Track Green Energy
        {
            "name": "Track Green Energy",
            "match": ["settings.nonScheduledAction"],
            "condition": ["eq"],
            "value": [3],
            "background_task": "checkGreenEnergy",
            "allowed_flex": "config.greenEnergyFlexAmps",
            "charge_limit": "config.greenEnergyLimit",
        },
    ]
    charge_policy = default_policy[:]
    lastPolicyCheck = 0
    limitOverride = False
    master = None
    policyCheckInterval = 30

    def __init__(self, master):
        self.master = master
        self.config = self.master.config

        # Override Charge Policy if specified
        config_policy = self.config.get("policy")
        if config_policy:
            if len(config_policy.get("override", [])) > 0:
                # Policy override specified, just override in place without processing the
                # extensions
                self.charge_policy = config_policy.get("override")
            else:
                config_extend = config_policy.get("extend", {})

                # Get additional restrictions
                for (name, restrictions) in config_extend.get(
                    "restrictions", {}
                ).items():
                    restricted = self.getPolicyByName(name)
                    for key in ("match", "condition", "value"):
                        restricted[key] += restrictions.get(key, [])

                # Get webhooks
                for (name, hooks) in config_extend.get("webhooks", {}).items():
                    hooked = self.getPolicyByName(name)
                    hooked["webhooks"] = hooks

                # Green Energy Latching
                if "greenEnergyLatch" in self.config["config"]:
                    self.charge_policy[2]["latch_period"] = self.config["config"][
                        "greenEnergyLatch"
                    ]

                # Insert optional policy extensions into policy list:
                #   After - Inserted before Non-Scheduled Charging
                #   Before - Inserted after Charge Now
                #   Emergency - Inserted at the beginning
                for (name, position) in [("after", 3), ("before", 1), ("emergency", 0)]:
                    self.charge_policy[position:position] = config_extend.get(name, [])

            # Set the Policy Check Interval if specified
            policy_engine = config_policy.get("engine")
            if policy_engine:
                if policy_engine.get("policyCheckInterval"):
                    self.policyCheckInterval = policy_engine.get("policyCheckInterval")

    def applyPolicyImmediately(self):
        self.lastPolicyCheck = 0
        self.setChargingPerPolicy()

    def setChargingPerPolicy(self):
        # This function is called for the purpose of evaluating the charging
        # policy and matching the first rule which matches our scenario.

        # Once we have determined the maximum number of amps for all slaves to
        # share based on the policy, we call setMaxAmpsToDivideAmongSlaves to
        # distribute the designated power amongst slaves.

        # First, determine if it has been less than 30 seconds since the last
        # policy check. If so, skip for now
        if (self.lastPolicyCheck + self.policyCheckInterval) > time.time():
            return
        else:
            # Update last policy check time
            self.lastPolicyCheck = time.time()

        for policy in self.charge_policy:

            # Check if the policy is within its latching period
            latched = False
            if "__latchTime" in policy:
                if time.time() < policy["__latchTime"]:
                    latched = True
                else:
                    del policy["__latchTime"]

            matched = self.checkConditions(
                policy["match"], policy["condition"], policy["value"]
            )

            if latched or matched:
                # Yes, we will now enforce policy
                logger.log(
                    logging.INFO7,
                    "All policy conditions have matched. Policy chosen is %s",
                    policy["name"],
                    extra={"colored": "red"},
                )
                self.enforcePolicy(policy, matched)

                # Now, finish processing
                return
            else:
                logger.log(logging.INFO8, "Policy conditions were not matched.")
                continue

        # No policy has matched; keep the current policy
        self.enforcePolicy(self.getPolicyByName(self.active_policy))

    def enforcePolicy(self, policy, updateLatch=False):
        if self.active_policy != str(policy["name"]):
            self.fireWebhook("exit")

            logger.info(
                "New policy selected; changing to %s",
                policy["name"],
                extra={"colored": "red"},
            )
            self.active_policy = str(policy["name"])
            self.limitOverride = False
            self.fireWebhook("enter")

        if updateLatch and "latch_period" in policy:
            policy["__latchTime"] = time.time() + policy["latch_period"] * 60

        # Determine which value to set the charging to
        if "charge_amps" in policy:
            if policy["charge_amps"] == "value":
                self.master.setMaxAmpsToDivideAmongSlaves(int(policy["value"]))
                logger.debug("Charge at %.2f" % int(policy["value"]))
            else:
                self.master.setMaxAmpsToDivideAmongSlaves(
                    self.policyValue(policy["charge_amps"])
                )
                logger.debug("Charge at %.2f" % self.policyValue(policy["charge_amps"]))

        # Set flex, if any
        self.master.setAllowedFlex(self.policyValue(policy.get("allowed_flex", 0)))

        # If a background task is defined for this policy, queue it
        bgt = policy.get("background_task", None)
        if bgt:
            self.master.queue_background_task({"cmd": bgt})

        # If a charge limit is defined for this policy, apply it
        limit = limit = self.policyValue(policy.get("charge_limit", -1))
        if self.limitOverride:
            currentCharge = (
                self.master.getModuleByName("TeslaAPI").minBatteryLevelAtHome - 1
            )
            if currentCharge < 50:
                currentCharge = 50
            limit = currentCharge if limit == -1 else min(limit, currentCharge)
        if not (limit >= 50 and limit <= 100):
            limit = -1
        self.master.queue_background_task({"cmd": "applyChargeLimit", "limit": limit})

    def fireWebhook(self, hook):
        policy = self.getPolicyByName(self.active_policy)
        if policy:
            url = policy.get("webhooks", {}).get(hook, None)
            if url:
                self.master.queue_background_task({"cmd": "webhook", "url": url})

    def getPolicyByName(self, name):
        for policy in self.charge_policy:
            if policy["name"] == name:
                return policy
        return None

    def policyValue(self, value):
        # policyValue is a macro to allow charging policy to refer to things
        # such as EMS module values or settings. This allows us to control
        # charging via policy.
        ltNow = time.localtime()

        # Anything other than a string can only be a literal value
        if not isinstance(value, str):
            return value

        # If value is "now", substitute with current timestamp
        if value == "now":
            return time.time()

        # If value is "tm_*", substitute with time component
        if value.startswith("tm_") and hasattr(ltNow, value):
            return getattr(ltNow, value)

        # The remaining checks are case-sensitive!
        #
        # If value refers to a function, execute the function and capture the
        # output
        if value == "getMaxAmpsToDivideGreenEnergy()":
            return self.master.getMaxAmpsToDivideGreenEnergy()
        elif value == "checkScheduledCharging()":
            return self.master.checkScheduledCharging()

        # If value is tiered, split it up
        if value.find(".") != -1:
            pieces = value.split(".")

            # If value refers to a setting, return the setting
            if pieces[0] == "settings":
                return self.master.settings.get(pieces[1], 0)
            elif pieces[0] == "config":
                return self.config["config"].get(pieces[1], 0)
            elif pieces[0] == "modules":
                module = None
                if pieces[1] in self.master.modules:
                    module = self.master.getModuleByName(pieces[1])
                    return getattr(module, pieces[2], value)

        # None of the macro conditions matched, return the value as is
        return value

    def policyIsGreen(self):
        current = self.getPolicyByName(self.active_policy)
        if current:
            return (
                current.get("background_task", "") == "checkGreenEnergy"
                and current.get("charge_amps", None) == None
            )
        return False

    def doesConditionMatch(self, match, condition, value, exitOn):
        matchValue = self.policyValue(match)
        value = self.policyValue(value)

        logger.log(
            logging.INFO8,
            f"Evaluating Policy match (%s [{matchValue}]), condition (%s), value (%s)",
            match,
            condition,
            value,
            extra={"colored": "red"},
        )

        if all([isinstance(a, list) for a in (matchValue, condition, value)]):
            return self.checkConditions(matchValue, condition, value, not exitOn)

        # Perform comparison
        if condition == "gt":
            # Match must be greater than value
            return True if matchValue > value else False
        elif condition == "gte":
            # Match must be greater than or equal to value
            return True if matchValue >= value else False
        elif condition == "lt":
            # Match must be less than value
            return True if matchValue < value else False
        elif condition == "lte":
            # Match must be less than or equal to value
            return True if matchValue <= value else False
        elif condition == "eq":
            # Match must be equal to value
            return True if matchValue == value else False
        elif condition == "ne":
            # Match must not be equal to value
            return True if matchValue != value else False
        elif condition == "false":
            # Condition: false is a method to ensure a policy entry
            # is never matched, possibly for testing purposes
            return False
        elif condition == "none":
            # No condition exists.
            return True
        else:
            raise ValueError("Unknown condition " + condition)

    # exitOn = False returns True if all conditions are True, else False ==> AND
    # exitOn = True returns True if any condition is True, else False ==> OR
    def checkConditions(self, matches, conditions, values, exitOn=False):
        for match, condition, value in zip(matches, conditions, values):
            if self.doesConditionMatch(match, condition, value, exitOn) == exitOn:
                return exitOn
        return not exitOn

    def overrideLimit(self):
        self.limitOverride = True

    def clearOverride(self):
        self.limitOverride = False
