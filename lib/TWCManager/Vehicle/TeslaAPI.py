class CarApiVehicle:
    config = None
    ID     = None

    firstWakeAttemptTime = 0
    lastWakeAttemptTime = 0
    delayNextWakeAttempt = 0

    lastErrorTime = 0
    stopAskingToStartCharging = False
    lat = 10000
    lon = 10000

    def __init__(self, ID, config):
        self.config     = config
        self.debugLevel = config['config']['debugLevel']
        self.ID         = ID

    def debugLog(self, minlevel, message):
      if (self.debugLevel >= minlevel):
        print("TeslaAPI: (" + str(minlevel) + ") " + message)

    def ready(self):
        global carApiLastErrorTime, carApiErrorRetryMins

        if(time.time() - self.lastErrorTime < carApiErrorRetryMins*60):
            # It's been under carApiErrorRetryMins minutes since the car API
            # generated an error on this vehicle. Return that car is not ready.
            debugLog(8, ': Vehicle ' + str(self.ID)
                    + ' not ready because of recent lastErrorTime '
                    + str(self.lastErrorTime))
            return False

        if(self.firstWakeAttemptTime == 0 and time.time() - self.lastWakeAttemptTime < 2*60):
            # Less than 2 minutes since we successfully woke this car, so it
            # should still be awake.  Tests on my car in energy saver mode show
            # it returns to sleep state about two minutes after the last command
            # was issued.  Times I've tested: 1:35, 1:57, 2:30
            return True

        debugLog(8, ': Vehicle ' + str(self.ID) + " not ready because it wasn't woken in the last 2 minutes.")
        return False

    def update_location(self):
        global carApiLastErrorTime, carApiTransientErrors

        if(self.ready() == False):
            return False

        apiResponseDict = {}

        cmd = 'curl -s -m 60 -H "accept: application/json" -H "Authorization:Bearer ' + \
              carApiBearerToken + \
              '" "https://owner-api.teslamotors.com/api/1/vehicles/' + \
              str(self.ID) + '/data_request/drive_state"'

        # Retry up to 3 times on certain errors.
        for retryCount in range(0, 3):
            debugLog(8, ': Car API cmd' + cmd)
            try:
                apiResponseDict = json.loads(run_process(cmd).decode('ascii'))
                # This error can happen here as well:
                #   {'response': {'reason': 'could_not_wake_buses', 'result': False}}
                # This one is somewhat common:
                #   {'response': None, 'error': 'vehicle unavailable: {:error=>"vehicle unavailable:"}', 'error_description': ''}
            except json.decoder.JSONDecodeError:
                pass

            try:
                debugLog(4, ': Car API vehicle GPS location' + apiResponseDict + '\n')

                if('error' in apiResponseDict):
                    foundKnownError = False
                    error = apiResponseDict['error']
                    for knownError in carApiTransientErrors:
                        if(knownError == error[0:len(knownError)]):
                            # I see these errors often enough that I think
                            # it's worth re-trying in 1 minute rather than
                            # waiting carApiErrorRetryMins minutes for retry
                            # in the standard error handler.
                            debugLog(1, "Car API returned '" + error
                                      + "' when trying to get GPS location.  Try again in 1 minute.")
                            time.sleep(60)
                            foundKnownError = True
                            break
                    if(foundKnownError):
                        continue

                response = apiResponseDict['response']

                # A successful call to drive_state will not contain a
                # response['reason'], so we check if the 'reason' key exists.
                if('reason' in response and response['reason'] == 'could_not_wake_buses'):
                    # Retry after 5 seconds.  See notes in car_api_charge where
                    # 'could_not_wake_buses' is handled.
                    time.sleep(5)
                    continue
                self.lat = response['latitude']
                self.lon = response['longitude']
            except (KeyError, TypeError):
                # This catches cases like trying to access
                # apiResponseDict['response'] when 'response' doesn't exist in
                # apiResponseDict.
                debugLog(1, ": ERROR: Can't get GPS location of vehicle " + str(self.ID) + \
                          ".  Will try again later.")
                self.lastErrorTime = time.time()
                return False

            return True
