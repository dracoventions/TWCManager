class CarApi:

  import json
  import re
  import requests
  import time

  carApiLastErrorTime = 0
  carApiBearerToken   = ''
  carApiRefreshToken  = ''
  carApiTokenExpireTime = time.time()
  carApiLastStartOrStopChargeTime = 0
  carApiLastChargeLimitApplyTime = 0
  lastChargeLimitApplied = 0
  carApiVehicles      = []
  config              = None
  debugLevel          = 0
  master              = None
  minChargeLevel      = -1

  # Transient errors are ones that usually disappear if we retry the car API
  # command a minute or less later.
  # 'vehicle unavailable:' sounds like it implies the car is out of connection
  # range, but I once saw it returned by drive_state after wake_up returned
  # 'online'. In that case, the car is reachable, but drive_state failed for some
  # reason. Thus we consider it a transient error.
  # Error strings below need only match the start of an error response such as:
  # {'response': None, 'error_description': '',
  # 'error': 'operation_timedout for txid `4853e3ad74de12733f8cc957c9f60040`}'}
  carApiTransientErrors = ['upstream internal error',
                           'operation_timedout',
                           'vehicle unavailable']

  # Define minutes between retrying non-transient errors.
  carApiErrorRetryMins = 10

  def __init__(self, config):
    self.config = config
    try:
        self.debugLevel = config['config']['debugLevel']
        self.minChargeLevel = config['config']['minChargeLevel']
    except KeyError:
        pass

  def addVehicle(self, json):
    self.carApiVehicles.append(CarApiVehicle(json, self, self.config))
    return True

  def car_api_available(self, email = None, password = None, charge = None, applyLimit = None):
    now = self.time.time()
    apiResponseDict = {}

    if(self.getCarApiRetryRemaining()):
        # It's been under carApiErrorRetryMins minutes since the car API
        # generated an error. To keep strain off Tesla's API servers, wait
        # carApiErrorRetryMins mins till we try again. This delay could be
        # reduced if you feel the need. It's mostly here to deal with unexpected
        # errors that are hopefully transient.
        # https://teslamotorsclub.com/tmc/threads/model-s-rest-api.13410/page-114#post-2732052
        # says he tested hammering the servers with requests as fast as possible
        # and was automatically blacklisted after 2 minutes. Waiting 30 mins was
        # enough to clear the blacklist. So at this point it seems Tesla has
        # accepted that third party apps use the API and deals with bad behavior
        # automatically.
        self.debugLog(6, 'Car API disabled for ' + str(self.getCarApiRetryRemaining()) + ' more seconds due to recent error.')
        return False
    else:
        self.debugLog(8, "Entering car_api_available - next step is to query Tesla API")

    # Tesla car API info comes from https://timdorr.docs.apiary.io/
    if(self.getCarApiBearerToken() == '' or self.getCarApiTokenExpireTime() - now < 30*24*60*60):
        req = None
        apiResponse = b''
        client_id = '81527cff06843c8634fdc09e8ac0abefb46ac849f38fe1e431c2ef2106796384'
        client_secret = 'c7257eb71a564034f9419ee651c7d0e5f7aa6bfbd18bafb5c5c033b093bb2fa3'
        url = 'https://owner-api.teslamotors.com/oauth/token'
        headers = None
        data = None

        # If we don't have a bearer token or our refresh token will expire in
        # under 30 days, get a new bearer token.  Refresh tokens expire in 45
        # days when first issued, so we'll get a new token every 15 days.
        if(self.getCarApiRefreshToken() != ''):
            headers = {
              'accept': 'application/json',
              'Content-Type': 'application/json'
            }
            data = {
              'client_id': client_id,
              'client_secret': client_secret,
              'grant_type': 'refresh_token',
              'refresh_token': self.getCarApiRefreshToken()
            }
            self.debugLog(8, "Attempting token refresh")

        elif(email != None and password != None):
            headers = {
              'accept': 'application/json',
              'Content-Type': 'application/json'
            }
            data = {
              'client_id': client_id,
              'client_secret': client_secret,
              'grant_type': 'password',
              'email': email,
              'password': password
            }
            self.debugLog(8, "Attempting password auth")

        if(headers and data):
            try:
                req = self.requests.post(url, headers = headers, json = data)
                self.debugLog(2, 'Car API request' + str(req))
                # Example response:
                # b'{"access_token":"4720d5f980c9969b0ca77ab39399b9103adb63ee832014fe299684201929380","token_type":"bearer","expires_in":3888000,"refresh_token":"110dd4455437ed351649391a3425b411755a213aa815171a2c6bfea8cc1253ae","created_at":1525232970}'

                apiResponseDict = self.json.loads(req.text)
            except:
                pass
        else:
            self.debugLog(2, 'Car API request is empty')


        try:
            self.debugLog(4, 'Car API auth response' + str(apiResponseDict))
            self.setCarApiBearerToken(apiResponseDict['access_token'])
            self.setCarApiRefreshToken(apiResponseDict['refresh_token'])
            self.setCarApiTokenExpireTime(now + apiResponseDict['expires_in'])
        except KeyError:
            self.debugLog(2, "ERROR: Can't access Tesla car via API.  Please log in again via web interface.")
            self.updateCarApiLastErrorTime()
            # Instead of just setting carApiLastErrorTime, erase tokens to
            # prevent further authorization attempts until user enters password
            # on web interface. I feel this is safer than trying to log in every
            # ten minutes with a bad token because Tesla might decide to block
            # remote access to your car after too many authorization errors.
            self.setCarApiBearerToken("")
            self.setCarApiRefreshToken("")

        self.master.saveSettings()

    if(self.getCarApiBearerToken() != ''):
        if(self.getVehicleCount() < 1):
            url = "https://owner-api.teslamotors.com/api/1/vehicles"
            headers = {
              'accept': 'application/json',
              'Authorization': 'Bearer ' + self.getCarApiBearerToken()
            }
            try:
                req = self.requests.get(url, headers = headers)
                self.debugLog(8, 'Car API cmd ' + str(req))
                apiResponseDict = self.json.loads(req.text)
            except:
                self.debugLog(1, "Failed to make API call " + url)
                self.debugLog(6, "Response: " + req.text)
                pass

            try:
                self.debugLog(4, 'Car API vehicle list' + str(apiResponseDict) + '\n')

                for i in range(0, apiResponseDict['count']):
                    self.addVehicle(apiResponseDict['response'][i]['id'])
            except (KeyError, TypeError):
                # This catches cases like trying to access
                # apiResponseDict['response'] when 'response' doesn't exist in
                # apiResponseDict.
                self.debugLog(2, "ERROR: Can't get list of vehicles via Tesla car API.  Will try again in " + str(self.getCarApiErrorRetryMins()) + " minutes.")
                self.updateCarApiLastErrorTime()
                return False

        needSleep = False
        if(self.getVehicleCount() > 0 and (charge or applyLimit)):
            # Wake cars if needed
            for vehicle in self.getCarApiVehicles():
                if(charge == True and vehicle.stopAskingToStartCharging):
                    # Vehicle is in a state (complete or charging) already
                    # which doesn't make sense for us to keep requesting it
                    # to start charging, so we will stop.
                    self.debugLog(11, "Don't repeatedly request API to charge vehicle "
                        + str(vehicle.ID) + ", because vehicle.stopAskingToStartCharging "
                        + " == True - it has already been requested.")
                    continue

                if(applyLimit == True and vehicle.stopTryingToApplyLimit):
                    self.debugLog(8, "Don't wake vehicle " + str(vehicle.ID)
                              + " to set the charge limit - it has already been set")
                    continue

                if(self.getCarApiRetryRemaining()):
                    # It's been under carApiErrorRetryMins minutes since the car
                    # API generated an error on this vehicle. Don't send it more
                    # commands yet.
                    self.debugLog(11, "Don't send commands to vehicle " + str(vehicle.ID)
                              + " because it returned an error in the last "
                              + str(self.getCarApiErrorRetryMins()) + " minutes.")
                    continue

                if(vehicle.ready()):
                    continue

                if(now - vehicle.lastWakeAttemptTime <= vehicle.delayNextWakeAttempt):
                    self.debugLog(10, "car_api_available returning False because we are still delaying "
                              + str(vehicle.delayNextWakeAttempt) + " seconds after the last failed wake attempt.")
                    return False

                # It's been delayNextWakeAttempt seconds since we last failed to
                # wake the car, or it's never been woken. Wake it.
                vehicle.lastWakeAttemptTime = now
                url = "https://owner-api.teslamotors.com/api/1/vehicles/"
                url = url + str(vehicle.ID) + "/wake_up"

                headers = {
                  'accept': 'application/json',
                  'Authorization': 'Bearer ' + self.getCarApiBearerToken()
                }
                try:
                    req = self.requests.post(url, headers = headers)
                    self.debugLog(8, 'Car API cmd' + str(req))
                    apiResponseDict = self.json.loads(req.text)
                except:
                    pass

                state = 'error'
                self.debugLog(4, 'Car API wake car response' + str(apiResponseDict))
                try:
                    state = apiResponseDict['response']['state']

                except (KeyError, TypeError):
                    # This catches unexpected cases like trying to access
                    # apiResponseDict['response'] when 'response' doesn't exist
                    # in apiResponseDict.
                    state = 'error'

                if(state == 'online'):
                    # With max power saving settings, car will almost always
                    # report 'asleep' or 'offline' the first time it's sent
                    # wake_up.  Rarely, it returns 'online' on the first wake_up
                    # even when the car has not been contacted in a long while.
                    # I suspect that happens when we happen to query the car
                    # when it periodically awakens for some reason.
                    vehicle.firstWakeAttemptTime = 0
                    vehicle.delayNextWakeAttempt = 0
                    # Don't alter vehicle.lastWakeAttemptTime because
                    # vehicle.ready() uses it to return True if the last wake
                    # was under 2 mins ago.
                    needSleep = True
                else:
                    if(vehicle.firstWakeAttemptTime == 0):
                        vehicle.firstWakeAttemptTime = now

                    if(state == 'asleep' or state == 'waking'):
                        if(now - vehicle.firstWakeAttemptTime <= 10*60):
                            # http://visibletesla.com has a 'force wakeup' mode
                            # that sends wake_up messages once every 5 seconds
                            # 15 times. This generally manages to wake my car if
                            # it's returning 'asleep' state, but I don't think
                            # there is any reason for 5 seconds and 15 attempts.
                            # The car did wake in two tests with that timing,
                            # but on the third test, it had not entered online
                            # mode by the 15th wake_up and took another 10+
                            # seconds to come online. In general, I hear relays
                            # in the car clicking a few seconds after the first
                            # wake_up but the car does not enter 'waking' or
                            # 'online' state for a random period of time. I've
                            # seen it take over one minute, 20 sec.
                            #
                            # I interpret this to mean a car in 'asleep' mode is
                            # still receiving car API messages and will start
                            # to wake after the first wake_up, but it may take
                            # awhile to finish waking up. Therefore, we try
                            # waking every 30 seconds for the first 10 mins.
                            vehicle.delayNextWakeAttempt = 30;
                        elif(now - vehicle.firstWakeAttemptTime <= 70*60):
                            # Cars in 'asleep' state should wake within a
                            # couple minutes in my experience, so we should
                            # never reach this point. If we do, try every 5
                            # minutes for the next hour.
                            vehicle.delayNextWakeAttempt = 5*60;
                        else:
                            # Car hasn't woken for an hour and 10 mins. Try
                            # again in 15 minutes. We'll show an error about
                            # reaching this point later.
                            vehicle.delayNextWakeAttempt = 15*60;
                    elif(state == 'offline'):
                        if(now - vehicle.firstWakeAttemptTime <= 31*60):
                            # A car in offline state is presumably not connected
                            # wirelessly so our wake_up command will not reach
                            # it. Instead, the car wakes itself every 20-30
                            # minutes and waits some period of time for a
                            # message, then goes back to sleep. I'm not sure
                            # what the period of time is, so I tried sending
                            # wake_up every 55 seconds for 16 minutes but the
                            # car failed to wake.
                            # Next I tried once every 25 seconds for 31 mins.
                            # This worked after 19.5 and 19.75 minutes in 2
                            # tests but I can't be sure the car stays awake for
                            # 30secs or if I just happened to send a command
                            # during a shorter period of wakefulness.
                            vehicle.delayNextWakeAttempt = 25;

                            # I've run tests sending wake_up every 10-30 mins to
                            # a car in offline state and it will go hours
                            # without waking unless you're lucky enough to hit
                            # it in the brief time it's waiting for wireless
                            # commands. I assume cars only enter offline state
                            # when set to max power saving mode, and even then,
                            # they don't always enter the state even after 8
                            # hours of no API contact or other interaction. I've
                            # seen it remain in 'asleep' state when contacted
                            # after 16.5 hours, but I also think I've seen it in
                            # offline state after less than 16 hours, so I'm not
                            # sure what the rules are or if maybe Tesla contacts
                            # the car periodically which resets the offline
                            # countdown.
                            #
                            # I've also seen it enter 'offline' state a few
                            # minutes after finishing charging, then go 'online'
                            # on the third retry every 55 seconds.  I suspect
                            # that might be a case of the car briefly losing
                            # wireless connection rather than actually going
                            # into a deep sleep.
                            # 'offline' may happen almost immediately if you
                            # don't have the charger plugged in.
                    else:
                        # Handle 'error' state.
                        if(now - vehicle.firstWakeAttemptTime <= 60*60):
                            # We've tried to wake the car for less than an
                            # hour.
                            foundKnownError = False
                            if('error' in apiResponseDict):
                                error = apiResponseDict['error']
                                for knownError in self.getCarApiTransientErrors():
                                    if(knownError == error[0:len(knownError)]):
                                        foundKnownError = True
                                        break

                            if(foundKnownError):
                                # I see these errors often enough that I think
                                # it's worth re-trying in 1 minute rather than
                                # waiting 5 minutes for retry in the standard
                                # error handler.
                                vehicle.delayNextWakeAttempt = 60;
                            else:
                                # by the API servers being down, car being out of
                                # range, or by something I can't anticipate. Try
                                # waking the car every 5 mins.
                                vehicle.delayNextWakeAttempt = 5*60;
                        else:
                            # Car hasn't woken for over an hour. Try again
                            # in 15 minutes. We'll show an error about this
                            # later.
                            vehicle.delayNextWakeAttempt = 15*60;

                    if(state == 'error'):
                        self.debugLog(1, "Car API wake car failed with unknown response.  " + "Will try again in " + str(vehicle.delayNextWakeAttempt) + " seconds.")
                    else:
                        self.debugLog(1, "Car API wake car failed.  State remains: '"
                                + state + "'.  Will try again in "
                                + str(vehicle.delayNextWakeAttempt) + " seconds.")

                if(vehicle.firstWakeAttemptTime > 0
                   and now - vehicle.firstWakeAttemptTime > 60*60):
                    # It should never take over an hour to wake a car.  If it
                    # does, ask user to report an error.
                    self.debugLog(1, "ERROR: We have failed to wake a car from '"
                        + state + "' state for %.1f hours.\n" \
                          "Please private message user CDragon at " \
                          "http://teslamotorsclub.com with a copy of this error. " \
                          "Also include this: %s" % (
                          ((now - vehicle.firstWakeAttemptTime) / 60 / 60),
                          str(apiResponseDict)))

    if(now - self.getCarApiLastErrorTime() < (self.getCarApiErrorRetryMins()*60) or self.getCarApiBearerToken() == ''):
        self.debugLog(8, "car_api_available returning False because of recent carApiLasterrorTime "
                + str(now - self.getCarApiLastErrorTime()) + " or empty carApiBearerToken '"
                + self.getCarApiBearerToken() + "'")
        return False

    # We return True to indicate there was no error that prevents running
    # car API commands and that we successfully got a list of vehicles.
    # True does not indicate that any vehicle is actually awake and ready
    # for commands.
    self.debugLog(8, "car_api_available returning True")

    if(needSleep):
        # If you send charge_start/stop less than 1 second after calling
        # update_location(), the charge command usually returns:
        #   {'response': {'result': False, 'reason': 'could_not_wake_buses'}}
        # I'm not sure if the same problem exists when sending commands too
        # quickly after we send wake_up.  I haven't seen a problem sending a
        # command immediately, but it seems safest to sleep 5 seconds after
        # waking before sending a command.
        self.time.sleep(5);

    return True

  def is_location_home(self, lat, lon):

    if(self.master.getHomeLatLon()[0] == 10000):
        self.debugLog(1, "Home location for vehicles has never been set.  " +
                "We'll assume home is where we found the first vehicle currently parked.  " +
                "Home set to lat=" + str(lat) + ", lon=" +
                str(lon))
        self.master.setHomeLat(lat)
        self.master.setHomeLon(lon)
        self.master.saveSettings()
        return True

    # 1 lat or lon = ~364488.888 feet. The exact feet is different depending
    # on the value of latitude, but this value should be close enough for
    # our rough needs.
    # 1/364488.888 * 10560 = 0.0289.
    # So if vehicle is within 0289 lat and lon of homeLat/Lon,
    # it's within ~10560 feet (2 miles) of home and we'll consider it to be
    # at home.
    # I originally tried using 0.00548 (~2000 feet) but one night the car
    # consistently reported being 2839 feet away from home despite being
    # parked in the exact spot I always park it.  This is very odd because
    # GPS is supposed to be accurate to within 12 feet.  Tesla phone app
    # also reports the car is not at its usual address.  I suspect this
    # is another case of a bug that's been causing car GPS to freeze  the
    # last couple months.
    if(abs(self.master.getHomeLatLon()[0] - lat) > 0.0289
       or abs(self.master.getHomeLatLon()[1] - lon) > 0.0289):
        return False

    return True

  def car_api_charge(self, charge):
    # Do not call this function directly.  Call by using background thread:
    # queue_background_task({'cmd':'charge', 'charge':<True/False>})

    now = self.time.time()
    apiResponseDict = {}
    if(not charge):
        # Whenever we are going to tell vehicles to stop charging, set
        # vehicle.stopAskingToStartCharging = False on all vehicles.
        for vehicle in self.getCarApiVehicles():
            vehicle.stopAskingToStartCharging = False

    if(now - self.getLastStartOrStopChargeTime() < 60):
        # Don't start or stop more often than once a minute
        self.debugLog(11, 'car_api_charge return because under 60 sec since last carApiLastStartOrStopChargeTime')
        return 'error'

    if(self.car_api_available(charge = charge) == False):
        self.debugLog(8, 'car_api_charge return because car_api_available() == False')
        return 'error'

    startOrStop = 'start' if charge else 'stop'
    result = 'success'
    self.debugLog(8, "startOrStop is set to " + str(startOrStop))

    for vehicle in self.getCarApiVehicles():
        if(charge and vehicle.stopAskingToStartCharging):
            self.debugLog(8, "Don't charge vehicle " + str(vehicle.ID)
                      + " because vehicle.stopAskingToStartCharging == True")
            continue

        if(vehicle.ready(wake = charge) == False):
            continue

        if(vehicle.update_charge(wake = False) and vehicle.batteryLevel < self.minChargeLevel ):
            # If the vehicle's charge state is lower than the configured minimum,
            #   don't stop it from charging, even if we'd otherwise not charge.
            continue

        # Only update carApiLastStartOrStopChargeTime if car_api_available() managed
        # to wake cars.  Setting this prevents any command below from being sent
        # more than once per minute.
        self.updateLastStartOrStopChargeTime()

        if(self.config['config']['onlyChargeMultiCarsAtHome'] and self.getVehicleCount() > 1):
            # When multiple cars are enrolled in the car API, only start/stop
            # charging cars parked at home.

            if(vehicle.update_location() == False):
                result = 'error'
                continue

            if(not vehicle.atHome):
                # Vehicle is not at home, so don't change its charge state.
                self.debugLog(1, 'Vehicle ID ' + str(vehicle.ID) +
                          ' is not at home.  Do not ' + startOrStop + ' charge.')
                continue

            # If you send charge_start/stop less than 1 second after calling
            # update_location(), the charge command usually returns:
            #   {'response': {'result': False, 'reason': 'could_not_wake_buses'}}
            # Waiting 2 seconds seems to consistently avoid the error, but let's
            # wait 5 seconds in case of hardware differences between cars.
            time.sleep(5)

        url = "https://owner-api.teslamotors.com/api/1/vehicles/"
        url = url + str(vehicle.ID) + "/command/charge_" + startOrStop
        headers = {
          'accept': 'application/json',
          'Authorization': 'Bearer ' + self.getCarApiBearerToken()
        }

        # Retry up to 3 times on certain errors.
        for retryCount in range(0, 3):
            try:
                req = self.requests.post(url, headers = headers)
                self.debugLog(8, 'Car API cmd' + str(req))
                apiResponseDict = self.json.loads(req.text)
            except:
                pass

            try:
                self.debugLog(4, 'Car API TWC ID: ' + str(vehicle.ID) + ": " + startOrStop + ' charge response' + str(apiResponseDict))
                # Responses I've seen in apiResponseDict:
                # Car is done charging:
                #   {'response': {'result': False, 'reason': 'complete'}}
                # Car wants to charge but may not actually be charging. Oddly, this
                # is the state reported when car is not plugged in to a charger!
                # It's also reported when plugged in but charger is not offering
                # power or even when the car is in an error state and refuses to
                # charge.
                #   {'response': {'result': False, 'reason': 'charging'}}
                # Car not reachable:
                #   {'response': None, 'error_description': '', 'error': 'vehicle unavailable: {:error=>"vehicle unavailable:"}'}
                # This weird error seems to happen randomly and re-trying a few
                # seconds later often succeeds:
                #   {'response': {'result': False, 'reason': 'could_not_wake_buses'}}
                # I've seen this a few times on wake_up, charge_start, and drive_state:
                #   {'error': 'upstream internal error', 'response': None, 'error_description': ''}
                # I've seen this once on wake_up:
                #   {'error': 'operation_timedout for txid `4853e3ad74de12733f8cc957c9f60040`}', 'response': None, 'error_description': ''}
                # Start or stop charging success:
                #   {'response': {'result': True, 'reason': ''}}
                if(apiResponseDict['response'] == None):
                    if('error' in apiResponseDict):
                        foundKnownError = False
                        error = apiResponseDict['error']
                        for knownError in self.getCarApiTransientErrors():
                            if(knownError == error[0:len(knownError)]):
                                # I see these errors often enough that I think
                                # it's worth re-trying in 1 minute rather than
                                # waiting carApiErrorRetryMins minutes for retry
                                # in the standard error handler.
                                self.debugLog(1, "Car API returned '"
                                          + error
                                          + "' when trying to start charging.  Try again in 1 minute.")
                                time.sleep(60)
                                foundKnownError = True
                                break
                        if(foundKnownError):
                            continue

                    # This generally indicates a significant error like 'vehicle
                    # unavailable', but it's not something I think the caller can do
                    # anything about, so return generic 'error'.
                    result = 'error'
                    # Don't send another command to this vehicle for
                    # carApiErrorRetryMins mins.
                    vehicle.lastErrorTime = now
                elif(apiResponseDict['response']['result'] == False):
                    if(charge):
                        reason = apiResponseDict['response']['reason']
                        if(reason == 'complete' or reason == 'charging'):
                            # We asked the car to charge, but it responded that
                            # it can't, either because it's reached target
                            # charge state (reason == 'complete'), or it's
                            # already trying to charge (reason == 'charging').
                            # In these cases, it won't help to keep asking it to
                            # charge, so set vehicle.stopAskingToStartCharging =
                            # True.
                            #
                            # Remember, this only means at least one car in the
                            # list wants us to stop asking and we don't know
                            # which car in the list is connected to our TWC.
                            self.debugLog(1, 'Vehicle ' + str(vehicle.ID)
                                      + ' is done charging or already trying to charge.  Stop asking to start charging.')
                            vehicle.stopAskingToStartCharging = True
                        else:
                            # Car was unable to charge for some other reason, such
                            # as 'could_not_wake_buses'.
                            if(reason == 'could_not_wake_buses'):
                                # This error often happens if you call
                                # charge_start too quickly after another command
                                # like drive_state. Even if you delay 5 seconds
                                # between the commands, this error still comes
                                # up occasionally. Retrying often succeeds, so
                                # wait 5 secs and retry.
                                # If all retries fail, we'll try again in a
                                # minute because we set
                                # carApiLastStartOrStopChargeTime = now earlier.
                                time.sleep(5)
                                continue
                            else:
                                # Start or stop charge failed with an error I
                                # haven't seen before, so wait
                                # carApiErrorRetryMins mins before trying again.
                                self.debugLog(1, 'ERROR "' + reason + '" when trying to ' +
                                      startOrStop + ' car charging via Tesla car API.  Will try again later.' +
                                      "\nIf this error persists, please private message user CDragon at http://teslamotorsclub.com with a copy of this error.")
                                result = 'error'
                                vehicle.lastErrorTime = now

            except (KeyError, TypeError):
                # This catches cases like trying to access
                # apiResponseDict['response'] when 'response' doesn't exist in
                # apiResponseDict.
                self.debugLog(1, 'ERROR: Failed to ' + startOrStop
                      + ' car charging via Tesla car API.  Will try again later.')
                vehicle.lastErrorTime = now
            break

    if(self.config['config']['debugLevel'] >= 1 and self.getLastStartOrStopChargeTime() == now):
        print(time_now() + ': Car API ' + startOrStop + ' charge result: ' + result)

    return result

  def applyChargeLimit(self, limit, checkArrival=False, checkDeparture=False):

    if(self.car_api_available() == False):
        self.debugLog(8, 'applyChargeLimit return because car_api_available() == False')
        return 'error'

    now = self.time.time()
    if( not checkArrival and not checkDeparture and
        now - self.carApiLastChargeLimitApplyTime < 60):
        # Don't change limits more often than once a minute
        self.debugLog(11, 'applyChargeLimit return because under 60 sec since last carApiLastChargeLimitApplyTime')
        return 'error'

    # We need to try to apply limits if:
    #   - We think the car is at home and the limit has changed
    #   - We think the car is at home and we've been asked to check for departures
    #   - We think the car is at home and we notice it gone
    #   - We think the car is away from home and we've been asked to check for arrivals
    # 
    # We do NOT opportunistically check for arrivals, because that would be a
    # continuous API poll.
    for vehicle in self.carApiVehicles:
        (found, target) = self.master.getNormalChargeLimit(vehicle.ID)
        if((found and (
                limit != self.lastChargeLimitApplied or
                checkDeparture or
                (vehicle.update_location(wake=False) and not vehicle.atHome))) or
            (not found and limit != -1 and checkArrival)):
            vehicle.stopTryingToApplyLimit = False

    if(self.car_api_available(applyLimit = True) == False):
        self.debugLog(8, 'applyChargeLimit return because car_api_available() == False')
        return 'error'

    self.lastChargeLimitApplied = limit
    self.carApiLastChargeLimitApplyTime = now

    for vehicle in self.carApiVehicles:
        if( vehicle.stopTryingToApplyLimit or not vehicle.ready() ):
            continue

        located = vehicle.update_location()
        (found, target) = self.master.getNormalChargeLimit(vehicle.ID)
        if( limit == -1 or (located and not vehicle.atHome) ):
            # We're removing any applied limit
            if(found):
                if( vehicle.apply_charge_limit(target) ):
                    self.master.removeNormalChargeLimit(vehicle.ID)
                    vehicle.stopTryingToApplyLimit = True
            else:
                vehicle.stopTryingToApplyLimit = True
        else:
            # We're applying a new limit
            if( not found ):
                if( vehicle.update_charge() ):
                    self.master.saveNormalChargeLimit(vehicle.ID, vehicle.chargeLimit)
                else:
                    # We failed to read the "normal" limit; don't risk changing it.
                    continue

            vehicle.stopTryingToApplyLimit = vehicle.apply_charge_limit(limit)

  def debugLog(self, minlevel, message):
    if (self.debugLevel >= minlevel):
      print("TeslaAPI: (" + str(minlevel) + ") " + message)

  def getCarApiBearerToken(self):
    return self.carApiBearerToken

  def getCarApiErrorRetryMins(self):
    return self.carApiErrorRetryMins

  def getCarApiLastErrorTime(self):
    return self.carApiLastErrorTime

  def getCarApiRefreshToken(self):
    return self.carApiRefreshToken

  def getCarApiRetryRemaining(self, vehicleLast = 0):
    # Calculate the amount of time remaining until the API can be queried
    # again. This is the api backoff time minus the difference between now
    # and the last error time

    # The optional vehicleLast parameter allows passing the last error time
    # for an individual vehicle, rather than the entire API.
    lastError = self.getCarApiLastErrorTime()
    if (vehicleLast > 0):
      lastError = vehicleLast

    if (lastError == 0):
      return 0
    else:
      backoff = (self.getCarApiErrorRetryMins()*60)
      lasterrortime = (self.time.time() - lastError)
      if (lasterrortime >= backoff):
        return 0
      else:
        self.debugLog(11, "Backoff is " + str(backoff) + ", lasterror delta is " + str(lasterrortime) + ", last error was " + str(lastError))
        return int(backoff - lasterrortime)

  def getCarApiTransientErrors(self):
    return self.carApiTransientErrors

  def getCarApiTokenExpireTime(self):
    return self.carApiTokenExpireTime

  def getLastStartOrStopChargeTime(self):
    return int(self.carApiLastStartOrStopChargeTime)

  def getVehicleCount(self):
    # Returns the number of currently tracked vehicles
    return int(len(self.carApiVehicles))

  def getCarApiVehicles(self):
    return self.carApiVehicles

  def setCarApiBearerToken(self, token=None):
    if token:
      self.carApiBearerToken = token
      return True
    else:
      return False

  def setCarApiErrorRetryMins(self, mins):
    self.carApiErrorRetryMins = mins
    return True

  def setCarApiLastErrorTime(self, tstamp):
    self.carApiLastErrorTime = tstamp
    return True

  def setCarApiRefreshToken(self, token):
    self.carApiRefreshToken = token
    return True

  def setCarApiTokenExpireTime(self, value):
    self.carApiTokenExpireTime = value
    return True

  def setMaster(self, master):
    self.master = master
    return True

  def updateCarApiLastErrorTime(self):
    timestamp = self.time.time()
    self.debugLog(8, "updateCarApiLastErrorTime() called due to Tesla API Error. Updating timestamp from " + str(self.carApiLastErrorTime) + " to " + str(timestamp))
    self.carApiLastErrorTime = timestamp
    return True

  def updateLastStartOrStopChargeTime(self):
    self.carApiLastStartOrStopChargeTime = self.time.time()
    return True

class CarApiVehicle:

    import time
    import requests
    import json

    carapi     = None
    config     = None
    debuglevel = 0
    ID         = None

    firstWakeAttemptTime = 0
    lastWakeAttemptTime = 0
    delayNextWakeAttempt = 0
    lastLimitAttemptTime = 0

    lastErrorTime = 0
    lastDriveStatusTime = 0
    lastChargeStatusTime = 0
    stopAskingToStartCharging = False
    stopTryingToApplyLimit = False

    batteryLevel = -1
    chargeLimit  = -1
    lat = 10000
    lon = 10000
    atHome = False

    def __init__(self, ID, carapi, config):
        self.carapi     = carapi
        self.config     = config
        self.debugLevel = config['config']['debugLevel']
        self.ID         = ID

    def debugLog(self, minlevel, message):
      if (self.debugLevel >= minlevel):
        print("TeslaAPIVehicle: (" + str(minlevel) + ") " + message)

    def ready(self, wake=True):
        if(self.carapi.getCarApiRetryRemaining(self.lastErrorTime)):
            # It's been under carApiErrorRetryMins minutes since the car API
            # generated an error on this vehicle. Return that car is not ready.
            self.debugLog(8, ': Vehicle ' + str(self.ID)
                    + ' not ready because of recent lastErrorTime '
                    + str(self.lastErrorTime))
            return False

        if(wake == False or
           (self.firstWakeAttemptTime == 0 and
            self.time.time() - self.lastWakeAttemptTime < 2*60)):
            # If we need to wake the car, it's been
            # less than 2 minutes since we successfully woke this car, so it
            # should still be awake.  Tests on my car in energy saver mode show
            # it returns to sleep state about two minutes after the last command
            # was issued.  Times I've tested: 1:35, 1:57, 2:30
            return True

        self.debugLog(8, 'Vehicle ' + str(self.ID) + " not ready because it wasn't woken in the last 2 minutes.")
        return False

    def get_car_api(self, url, wake=True):
        if(self.ready(wake) == False):
            return (False, None)

        apiResponseDict = {}

        headers = {
          'accept': 'application/json',
          'Authorization': 'Bearer ' + self.carapi.getCarApiBearerToken()
        }

        # Retry up to 3 times on certain errors.
        for retryCount in range(0, 3):
            try:
                req = self.requests.get(url, headers = headers)
                self.debugLog(8, 'Car API cmd' + str(req))
                apiResponseDict = self.json.loads(req.text)
                # This error can happen here as well:
                #   {'response': {'reason': 'could_not_wake_buses', 'result': False}}
                # This one is somewhat common:
                #   {'response': None, 'error': 'vehicle unavailable: {:error=>"vehicle unavailable:"}', 'error_description': ''}
            except:
                pass

            try:
                self.debugLog(4, 'Car API vehicle status' + str(apiResponseDict) + '\n')

                if('error' in apiResponseDict):
                    foundKnownError = False
                    error = apiResponseDict['error']

                    # If we opted not to wake the vehicle, unavailable is expected.
                    # Don't keep trying if that happens.
                    unavailable = 'vehicle unavailable'
                    if(wake == False and unavailable == error[0:len(unavailable)]):
                        return (False, None)
                    for knownError in self.carapi.getCarApiTransientErrors():
                        if(knownError == error[0:len(knownError)]):
                            # I see these errors often enough that I think
                            # it's worth re-trying in 1 minute rather than
                            # waiting carApiErrorRetryMins minutes for retry
                            # in the standard error handler.
                            self.debugLog(1, "Car API returned '" + error
                                      + "' when trying to get status.  Try again in 1 minute.")
                            self.time.sleep(60)
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
                    self.time.sleep(5)
                    continue
            except (KeyError, TypeError):
                # This catches cases like trying to access
                # apiResponseDict['response'] when 'response' doesn't exist in
                # apiResponseDict.
                self.debugLog(1, ": ERROR: Can't access vehicle status " + str(self.ID) + \
                          ".  Will try again later.")
                self.lastErrorTime = self.time.time()
                return (False, None)

            return (True, response)

    def update_location(self, wake=True):

        url = "https://owner-api.teslamotors.com/api/1/vehicles/"
        url = url + str(self.ID) + "/data_request/drive_state"

        now = self.time.time()

        if (now - self.lastDriveStatusTime < (60 if wake else 3600)):
            return True

        (result, response) = self.get_car_api(url, wake)

        if result:
            self.lastDriveStatusTime = self.time.time()
            self.lat = response['latitude']
            self.lon = response['longitude']
            self.atHome = self.carapi.is_location_home(self.lat, self.lon)

        return result

    def update_charge(self, wake = True):
        url = "https://owner-api.teslamotors.com/api/1/vehicles/"
        url = url + str(self.ID) + "/data_request/charge_state"

        now = self.time.time()

        if (now - self.lastChargeStatusTime < 60):
            return True

        (result, response) = self.get_car_api(url, wake=wake)

        if result:
            self.lastChargeStatusTime = self.time.time()
            self.chargeLimit = response['charge_limit_soc']
            self.batteryLevel = response['battery_level']

        return result

    def apply_charge_limit(self, limit):
        if(self.stopTryingToApplyLimit):
            return True

        now = self.time.time()

        if( now - self.lastLimitAttemptTime <= 300
            or self.carapi.getCarApiRetryRemaining(self.lastErrorTime)):
            return False

        if( self.ready() == False):
            return False

        self.lastLimitAttemptTime = now

        url = "https://owner-api.teslamotors.com/api/1/vehicles/"
        url = url + str(self.ID) + "/command/set_charge_limit"

        headers = {
            'accept': 'application/json',
            'Authorization': 'Bearer ' + self.carapi.getCarApiBearerToken()
        }
        body = {
            'percent': limit
        }

        for retryCount in range(0, 3):
            try:
                req = self.requests.post(url, headers = headers, json = body)
                self.debugLog(8, 'Car API cmd' + str(req))

                apiResponseDict = self.json.loads(req.text)
            except:
                pass

            result = False
            reason = ''
            try:
                result = apiResponseDict['response']['result']
                reason = apiResponseDict['response']['reason']
            except (KeyError, TypeError):
                # This catches unexpected cases like trying to access
                # apiResponseDict['response'] when 'response' doesn't exist
                # in apiResponseDict.
                result = False

            if(result == True or reason == 'already_set'):
                self.stopTryingToApplyLimit = True
                return True
            elif(reason == 'could_not_wake_buses'):
                time.sleep(5)
                continue
            elif(apiResponseDict['response'] == None):
                if('error' in apiResponseDict):
                    foundKnownError = False
                    error = apiResponseDict['error']
                    for knownError in self.carapi.getCarApiTransientErrors():
                        if(knownError == error[0:len(knownError)]):
                            # I see these errors often enough that I think
                            # it's worth re-trying in 1 minute rather than
                            # waiting carApiErrorRetryMins minutes for retry
                            # in the standard error handler.
                            self.debugLog(1, "Car API returned '"
                                        + error
                                        + "' when trying to start charging.  Try again in 1 minute.")
                            time.sleep(60)
                            foundKnownError = True
                            break
                    if(foundKnownError):
                        continue
            else:
                self.lastErrorTime = now


        return False
