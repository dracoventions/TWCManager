#! /usr/bin/python3

class TWCMaster:

  chargeNowAmps       = 0
  chargeNowTimeEnd    = 0
  consumptionValues   = {}
  generationValues    = {}
  subtractChargerLoad = False
  totalAmpsInUse      = 0
  TWCID               = None

  def __init__(self, TWCID, config):
    self.TWCID = TWCID
    self.subtractChargerLoad = config['config']['subtractChargerLoad']

  def checkChargeNowTime(self):
    # Returns the following values:
    # 0 = chargeNowTime has expired, reset chargeNow to 0
    # 1 = chargeNowAmps is set, charge at the specified value
    if (self.chargeNowTimeEnd > 0 and self.chargeNowTimeEnd < now):
      # We're beyond the one-day period where we want to charge at
      # chargeNowAmps, so reset the chargeNow variables.
      return 0
    elif (self.chargeNowTimeEnd > 0 and self.chargeNowAmps > 0):
      return 1

  def getChargeNowAmps(self):
    return (self.chargeNowAmps)

  def getChargerLoad(self):
    # Calculate in watts the load that the charger is generating so
    # that we can exclude it from the consumption if necessary
    return (self.getTotalAmpsInUse() * 240)

  def getConsumption(self):
    consumptionVal = 0

    for key in self.consumptionValues:
      consumptionVal += float(self.consumptionValues[key])

    if (consumptionVal < 0):
      consumptionVal = 0

    return float(consumptionVal)

  def getGeneration(self):
    generationVal = 0

    # Currently, our only logic is to add all of the values together
    for key in self.generationValues:
      generationVal += float(self.generationValues[key])

    if (generationVal < 0):
      generationVal = 0

    return float(generationVal)

  def getGenerationOffset(self):
    # Returns the number of watts to subtract from the solar generation stats
    # This is consumption + charger load if subtractChargerLoad is enabled
    # Or simply consumption if subtractChargerLoad is disabled
    generationOffset = self.getConsumption()
    if (self.subtractChargerLoad):
      generationOffset -= self.getChargerLoad()
    if (generationOffset < 0):
      generationOffset = 0
    return float(generationOffset)

  def getMaxAmpsToDivideAmongSlaves(self):
    # Watts = Volts * Amps
    # Car charges at 240 volts in North America so we figure
    # out how many amps * 240 = solarW and limit the car to
    # that many amps.

    # Calculate our current generation and consumption in watts
    solarW = float(self.getGeneration() - self.getGenerationOffset())

    # Generation may be below zero if consumption is greater than generation
    if solarW < 0:
        solarW = 0

    # Watts = Volts * Amps
    # Car charges at 240 volts in North America so we figure
    # out how many amps * 240 = solarW and limit the car to
    # that many amps.
    maxAmpsToDivideAmongSlaves = (solarW / 240)
    return maxAmpsToDivideAmongSlaves

  def getTotalAmpsInUse(self):
    # Returns the number of amps currently in use by all TWCs
    return self.totalAmpsInUse

  def resetChargeNowAmps(self):
    # Sets chargeNowAmps back to zero, so we follow the green energy
    # tracking again
    self.chargeNowAmps = 0
    self.chargeNowTimeEnd = 0

  def setChargeNowAmps(self, amps):
    # Accepts a number of amps to define the amperage at which we
    # should charge
    self.chargeNowAmps = amps

  def setChargeNowTimeEnd(self, time):
    self.chargeNowTimeEnd = (self.time.time() + time)

  def setConsumption(self, source, value):
    # Accepts consumption values from one or more data sources
    # For now, this gives a sum value of all, but in future we could
    # average across sources perhaps, or do a primary/secondary priority
    self.consumptionValues[source] = value

  def setGeneration(self, source, value):
    self.generationValues[source] = value

  def setTotalAmpsInUse(self, amps):
    self.totalAmpsInUse = amps
