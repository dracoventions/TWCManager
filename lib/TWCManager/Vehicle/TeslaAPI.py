import base64
import hashlib
import json
import logging
import os
import re
import requests
from threading import Thread
import time
from urllib.parse import parse_qs

logger = logging.getLogger("\U0001F697 TeslaAPI")


class TeslaAPI:

    __apiCaptcha = None
    __apiCaptchaCode = None
    __apiCaptchaInterface = None
    __authURL = "https://auth.tesla.com/oauth2/v3/authorize"
    callbackURL = "https://auth.tesla.com/void/callback"
    captchaURL = "https://auth.tesla.com/captcha"
    carApiLastErrorTime = 0
    carApiBearerToken = ""
    carApiRefreshToken = ""
    carApiTokenExpireTime = time.time()
    carApiLastStartOrStopChargeTime = 0
    carApiLastChargeLimitApplyTime = 0
    clientID = "81527cff06843c8634fdc09e8ac0abefb46ac849f38fe1e431c2ef2106796384"
    clientSecret = "c7257eb71a564034f9419ee651c7d0e5f7aa6bfbd18bafb5c5c033b093bb2fa3"
    lastChargeLimitApplied = 0
    lastChargeCheck = 0
    chargeUpdateInterval = 1800
    carApiVehicles = []
    config = None
    master = None
    __email = None
    errorCount = 0
    maxLoginRetries = 10
    minChargeLevel = -1
    params = None
    __password = None
    refreshURL = "https://auth.tesla.com/oauth2/v3/token"
    __resp = None
    session = None
    verifier = ""

    # Transient errors are ones that usually disappear if we retry the car API
    # command a minute or less later.
    # 'vehicle unavailable:' sounds like it implies the car is out of connection
    # range, but I once saw it returned by drive_state after wake_up returned
    # 'online'. In that case, the car is reachable, but drive_state failed for some
    # reason. Thus we consider it a transient error.
    # Error strings below need only match the start of an error response such as:
    # {'response': None, 'error_description': '',
    # 'error': 'operation_timedout for txid `4853e3ad74de12733f8cc957c9f60040`}'}
    carApiTransientErrors = [
        "upstream internal error",
        "operation_timedout",
        "vehicle unavailable",
    ]

    def __init__(self, master):
        self.master = master
        try:
            self.config = master.config
            self.minChargeLevel = self.config["config"].get("minChargeLevel", -1)
            self.chargeUpdateInterval = self.config["config"].get(
                "cloudUpdateInterval", 1800
            )
        except KeyError:
            pass

    def addVehicle(self, json):
        self.carApiVehicles.append(CarApiVehicle(json, self, self.config))
        return True

    def apiDebugInterface(self, command, vehicleID, parameters):

        # Provides an interface from the Web UI to allow commands to be run interactively

        # Map vehicle ID back to vehicle object
        vehicle = self.getVehicleByID(int(vehicleID))

        # Get parameters
        params = {}
        try:
            params = json.loads(parameters)
        except json.decoder.JSONDecodeError:
            pass

        # Execute specified command
        if command == "setChargeRate":
            charge_rate = params.get("charge_rate", 0)
            self.setChargeRate(charge_rate, vehicle)
            return True
        elif command == "wakeVehicle":
            self.wakeVehicle(vehicle)
            return True

        # If we make it here, we did not execute a command
        return False

    def apiLogin(self, email, password):

        # Populate auth details for Phase 1
        self.__email = email
        self.__password = password

        for attempt in range(self.maxLoginRetries):

            self.verifier = base64.urlsafe_b64encode(os.urandom(86)).rstrip(b"=")
            challenge = base64.urlsafe_b64encode(
                hashlib.sha256(self.verifier).digest()
            ).rstrip(b"=")
            state = (
                base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode("utf-8")
            )

            self.params = (
                ("client_id", "ownerapi"),
                ("code_challenge", challenge),
                ("code_challenge_method", "S256"),
                ("redirect_uri", self.callbackURL),
                ("response_type", "code"),
                ("scope", "openid email offline_access"),
                ("state", state),
            )

            self.session = requests.Session()
            self.__resp = self.session.get(self.__authURL, params=self.params)

            if self.__resp.ok and "<title>" in self.__resp.text:
                logger.log(
                    logging.INFO6,
                    "Tesla Auth form fetch success, attempt: " + str(attempt),
                )

                if 'img data-id="captcha"' in self.__resp.text:
                    logger.log(
                        logging.INFO6,
                        "Tesla Auth form challenged us for Captcha. Redirecting.",
                    )
                    self.getApiCaptcha()
                    return "Phase1Captcha"
                elif "g-recaptcha" in self.__resp.text:
                    logger.log(
                        logging.INFO6,
                        "Tesla Auth form challenged us for Google Recaptcha. Redirecting.",
                    )
                    return "Phase1Recaptcha"
                else:
                    return self.apiLoginPhaseOne()
            else:
                logger.log(
                    logging.INFO6,
                    "Tesla auth form fetch failed, attempt: " + str(attempt),
                )

            time.sleep(3)
        else:
            logger.log(
                logging.INFO2,
                "Wasn't able to find authentication form after "
                + str(attempt)
                + " attempts",
            )
            return "Phase1Error"

    def apiLoginPhaseOne(self):

        # Picks up on the first phase of authentication, after redirecting to
        # handle Captcha if this was requested, or directly if we were lucky
        # enough not to be challenged.

        csrf = re.search(r'name="_csrf".+value="([^"]+)"', self.__resp.text).group(1)
        transaction_id = re.search(
            r'name="transaction_id".+value="([^"]+)"', self.__resp.text
        ).group(1)

        if not csrf or not transaction_id:
            # These two parameters are required for Phase 1 (Authentication) auth
            # If they are missing, we raise an appropriate error to the user's attention
            return "Phase1Error"

        data = {
            "_csrf": csrf,
            "_phase": "authenticate",
            "_process": "1",
            "transaction_id": transaction_id,
            "cancel": "",
            "identity": self.__email,
            "credential": self.__password,
        }

        # If a captcha code is stored, inject it into the data parameter
        if self.__apiCaptchaCode and self.__apiCaptchaInterface == "captcha":
            data["captcha"] = self.__apiCaptchaCode

            # Clear captcha data
            self.__apiCaptcha = None

        elif self.__apiCaptchaCode and self.__apiCaptchaInterface == "recaptcha":
            data["recaptcha"] = self.__apiCaptchaCode
            data["g-recaptcha-response"] = self.__apiCaptchaCode

        # Clear stored credentials
        self.__email = None
        self.__password = None

        # Call login Phase 2
        return self.apiLoginPhaseTwo(data)

    def apiLoginPhaseTwo(self, data):

        for attempt in range(self.maxLoginRetries):
            resp = self.session.post(
                self.__authURL, params=self.params, data=data, allow_redirects=False
            )
            if resp.ok and (resp.status_code == 302 or "<title>" in resp.text):
                logger.log(
                    logging.INFO2,
                    "Posted auth form successfully after " + str(attempt) + " attempts",
                )
                break
            time.sleep(3)
        else:
            logger.log(
                logging.INFO2,
                "Wasn't able to post authentication form after "
                + str(attempt)
                + " attempts",
            )
            return "Phase2Error"

        if resp.status_code == 200 and "/mfa/verify" in resp.text:
            # This account is using MFA, redirect to MFA code entry page
            return "MFA/" + str(data["transaction_id"])

        try:
            code = parse_qs(resp.headers["location"])[self.callbackURL + "?code"]
        except KeyError:
            return "Phase2ErrorTip"

        data = {
            "grant_type": "authorization_code",
            "client_id": "ownerapi",
            "code_verifier": self.verifier.decode("utf-8"),
            "code": code,
            "redirect_uri": self.callbackURL,
        }

        resp = self.session.post("https://auth.tesla.com/oauth2/v3/token", json=data)
        access_token = resp.json()["access_token"]

        headers = {"authorization": "bearer " + access_token}

        data = {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "client_id": self.clientID,
        }
        resp = self.session.post(
            "https://owner-api.teslamotors.com/oauth/token", headers=headers, json=data
        )
        try:
            self.setCarApiBearerToken(resp.json()["access_token"])
            self.setCarApiRefreshToken(resp.json()["refresh_token"])
            self.setCarApiTokenExpireTime(time.time() + resp.json()["expires_in"])
            self.master.queue_background_task({"cmd": "saveSettings"})
            return True

        except KeyError:
            logger.log(
                logging.INFO2,
                "ERROR: Can't access Tesla car via API.  Please log in again via web interface.",
            )
            self.updateCarApiLastErrorTime()
            # In addition to setting carApiLastErrorTime, erase tokens to
            # prevent further authorization attempts until user enters password
            # on web interface. I feel this is safer than trying to log in every
            # ten minutes with a bad token because Tesla might decide to block
            # remote access to your car after too many authorization errors.
            self.setCarApiBearerToken("")
            self.setCarApiRefreshToken("")
            self.master.queue_background_task({"cmd": "saveSettings"})
            return False

    def apiRefresh(self):
        # Refresh tokens expire in 45
        # days when first issued, so we'll get a new token every 15 days.
        headers = {"accept": "application/json", "Content-Type": "application/json"}
        data = {
            "client_id": "ownerapi",
            "grant_type": "refresh_token",
            "refresh_token": self.getCarApiRefreshToken(),
            "scope": "openid email offline_access",
        }
        req = None
        now = time.time()
        try:
            req = requests.post(self.refreshURL, headers=headers, json=data)
            logger.log(logging.INFO2, "Car API request" + str(req))
            apiResponseDict = json.loads(req.text)
        except requests.exceptions.RequestException:
            pass
        except ValueError:
            pass
        except json.decoder.JSONDecodeError:
            pass

        try:
            logger.log(logging.INFO4, "Car API auth response" + str(apiResponseDict))
            self.setCarApiBearerToken(apiResponseDict["access_token"])
            self.setCarApiRefreshToken(apiResponseDict["refresh_token"])
            self.setCarApiTokenExpireTime(now + apiResponseDict["expires_in"])
            self.master.queue_background_task({"cmd": "saveSettings"})

        except KeyError:
            logger.log(
                logging.INFO2,
                "TeslaAPI",
                "ERROR: Can't access Tesla car via API.  Please log in again via web interface.",
            )
            self.updateCarApiLastErrorTime()
            # Instead of just setting carApiLastErrorTime, erase tokens to
            # prevent further authorization attempts until user enters password
            # on web interface. I feel this is safer than trying to log in every
            # ten minutes with a bad token because Tesla might decide to block
            # remote access to your car after too many authorization errors.
            self.setCarApiBearerToken("")
            self.setCarApiRefreshToken("")
            self.master.queue_background_task({"cmd": "saveSettings"})

    def car_api_available(
        self, email=None, password=None, charge=None, applyLimit=None
    ):
        now = time.time()
        needSleep = False
        apiResponseDict = {}

        if self.getCarApiRetryRemaining():
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
            logger.log(
                logging.INFO6,
                "Car API disabled for "
                + str(self.getCarApiRetryRemaining())
                + " more seconds due to recent error.",
            )
            return False
        else:
            logger.log(
                logging.INFO8,
                "Entering car_api_available - next step is to query Tesla API",
            )

        # Authentiate to Tesla API
        if not self.master.tokenSyncEnabled() and (
            self.getCarApiBearerToken() == ""
            or self.getCarApiTokenExpireTime() - now < 60 * 60
        ):
            if self.getCarApiRefreshToken() != "":
                headers = {
                    "accept": "application/json",
                    "Content-Type": "application/json",
                }
                data = {
                    "client_id": self.clientID,
                    "client_secret": self.clientSecret,
                    "grant_type": "refresh_token",
                    "refresh_token": self.getCarApiRefreshToken(),
                }
                logger.log(logging.INFO8, "Attempting token refresh")
                self.apiRefresh()

            elif email is not None and password is not None:
                logger.log(logging.INFO8, "Attempting password auth")
                ret = self.apiLogin(email, password)

                # If any string is returned, we redirect to it. This helps with MFA login flow
                if (
                    str(ret) != "True"
                    and str(ret) != "False"
                    and str(ret) != ""
                    and str(ret) != "None"
                ):
                    return ret

        if self.getCarApiBearerToken() != "":
            if self.getVehicleCount() < 1:
                url = "https://owner-api.teslamotors.com/api/1/vehicles"
                headers = {
                    "accept": "application/json",
                    "Authorization": "Bearer " + self.getCarApiBearerToken(),
                }
                try:
                    req = requests.get(url, headers=headers)
                    logger.log(logging.INFO8, "Car API cmd vehicles " + str(req))
                    apiResponseDict = json.loads(req.text)
                except requests.exceptions.RequestException:
                    logger.info("Failed to make API call " + url)
                    logger.log(logging.INFO6, "Response: " + req.text)
                    pass
                except json.decoder.JSONDecodeError:
                    logger.info("Could not parse JSON result from " + url)
                    logger.log(logging.INFO6, "Response: " + req.text)
                    pass

                try:
                    logger.debug("Car API vehicle list" + str(apiResponseDict) + "\n")

                    for i in range(0, apiResponseDict["count"]):
                        self.addVehicle(apiResponseDict["response"][i])
                    self.resetCarApiLastErrorTime()
                except (KeyError, TypeError):
                    # This catches cases like trying to access
                    # apiResponseDict['response'] when 'response' doesn't exist in
                    # apiResponseDict.
                    logger.log(
                        logging.INFO2,
                        "ERROR: Can't get list of vehicles via Tesla car API.  Will try again in "
                        + str(self.getCarApiErrorRetryMins())
                        + " minutes.",
                    )
                    self.updateCarApiLastErrorTime()
                    return False

            if self.getVehicleCount() > 0 and (charge or applyLimit):
                # Wake cars if needed
                for vehicle in self.getCarApiVehicles():
                    if charge is True and vehicle.stopAskingToStartCharging:
                        # Vehicle is in a state (complete or charging) already
                        # which doesn't make sense for us to keep requesting it
                        # to start charging, so we will stop.
                        logger.log(
                            logging.DEBUG2,
                            "Don't repeatedly request API to charge "
                            + vehicle.name
                            + ", because vehicle.stopAskingToStartCharging "
                            + " == True - it has already been requested.",
                        )
                        continue

                    if applyLimit is True and vehicle.stopTryingToApplyLimit:
                        logger.log(
                            logging.DEBUG2,
                            "Don't wake "
                            + vehicle.name
                            + " to set the charge limit - it has already been set",
                        )
                        continue

                    if self.getCarApiRetryRemaining():
                        # It's been under carApiErrorRetryMins minutes since the car
                        # API generated an error on this vehicle. Don't send it more
                        # commands yet.
                        logger.log(
                            logging.DEBUG2,
                            "Don't send commands to "
                            + vehicle.name
                            + " because it returned an error in the last "
                            + str(self.getCarApiErrorRetryMins())
                            + " minutes.",
                        )
                        continue

                    if vehicle.ready():
                        continue

                    if now - vehicle.lastAPIAccessTime <= vehicle.delayNextWakeAttempt:
                        logger.debug(
                            "car_api_available returning False because we are still delaying "
                            + str(vehicle.delayNextWakeAttempt)
                            + " seconds after the last failed wake attempt."
                        )
                        return False

                    # It's been delayNextWakeAttempt seconds since we last failed to
                    # wake the car, or it's never been woken. Wake it.
                    apiResponseDict = self.wakeVehicle(vehicle)

                    state = "error"
                    logger.debug("Car API wake car response" + str(apiResponseDict))
                    try:
                        state = apiResponseDict["response"]["state"]
                        self.resetCarApiLastErrorTime()

                    except (KeyError, TypeError):
                        # This catches unexpected cases like trying to access
                        # apiResponseDict['response'] when 'response' doesn't exist
                        # in apiResponseDict.
                        state = "error"

                    if state == "online":
                        # With max power saving settings, car will almost always
                        # report 'asleep' or 'offline' the first time it's sent
                        # wake_up.  Rarely, it returns 'online' on the first wake_up
                        # even when the car has not been contacted in a long while.
                        # I suspect that happens when we happen to query the car
                        # when it periodically awakens for some reason.
                        vehicle.firstWakeAttemptTime = 0
                        vehicle.delayNextWakeAttempt = 0
                        # Don't alter vehicle.lastAPIAccessTime because
                        # vehicle.ready() uses it to return True if the last wake
                        # was under 2 mins ago.
                        needSleep = True
                    else:
                        if vehicle.firstWakeAttemptTime == 0:
                            vehicle.firstWakeAttemptTime = now

                        if state == "asleep" or state == "waking":
                            self.resetCarApiLastErrorTime()
                            if now - vehicle.firstWakeAttemptTime <= 10 * 60:
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
                                vehicle.delayNextWakeAttempt = 30
                            elif now - vehicle.firstWakeAttemptTime <= 70 * 60:
                                # Cars in 'asleep' state should wake within a
                                # couple minutes in my experience, so we should
                                # never reach this point. If we do, try every 5
                                # minutes for the next hour.
                                vehicle.delayNextWakeAttempt = 5 * 60
                            else:
                                # Car hasn't woken for an hour and 10 mins. Try
                                # again in 15 minutes. We'll show an error about
                                # reaching this point later.
                                vehicle.delayNextWakeAttempt = 15 * 60
                        elif state == "offline":
                            self.resetCarApiLastErrorTime()
                            # In any case it can make sense to wait 5 seconds here.
                            # I had the issue, that the next command was sent too
                            # fast and only a reboot of the Raspberry resultet in
                            # possible reconnect to the API (even the Tesla App
                            # couldn't connect anymore).
                            time.sleep(5)
                            if now - vehicle.firstWakeAttemptTime <= 31 * 60:
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
                                vehicle.delayNextWakeAttempt = 25

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
                            self.updateCarApiLastErrorTime()
                            if now - vehicle.firstWakeAttemptTime >= 60 * 60:
                                # Car hasn't woken for over an hour. Try again
                                # in 15 minutes. We'll show an error about this
                                # later.
                                vehicle.delayNextWakeAttempt = 15 * 60

                        if state == "error":
                            logger.info(
                                "Car API wake car failed with unknown response.  "
                                + "Will try again in "
                                + str(vehicle.delayNextWakeAttempt)
                                + " seconds."
                            )
                        else:
                            logger.info(
                                "Car API wake car failed.  State remains: '"
                                + state
                                + "'.  Will try again in "
                                + str(vehicle.delayNextWakeAttempt)
                                + " seconds."
                            )

                    if (
                        vehicle.firstWakeAttemptTime > 0
                        and now - vehicle.firstWakeAttemptTime > 60 * 60
                    ):
                        # It should never take over an hour to wake a car.  If it
                        # does, ask user to report an error.
                        logger.info(
                            "ERROR: We have failed to wake a car from '"
                            + state
                            + "' state for %.1f hours.\n"
                            "Please file an issue at https://github.com/ngardiner/TWCManager/. "
                            "Also include this: %s"
                            % (
                                ((now - vehicle.firstWakeAttemptTime) / 60 / 60),
                                str(apiResponseDict),
                            )
                        )

        if (
            now - self.getCarApiLastErrorTime() < (self.getCarApiErrorRetryMins() * 60)
            or self.getCarApiBearerToken() == ""
        ):
            logger.log(
                logging.INFO8,
                "car_api_available returning False because of recent carApiLasterrorTime "
                + str(now - self.getCarApiLastErrorTime())
                + " or empty carApiBearerToken '"
                + self.getCarApiBearerToken()
                + "'",
            )
            return False

        # We return True to indicate there was no error that prevents running
        # car API commands and that we successfully got a list of vehicles.
        # True does not indicate that any vehicle is actually awake and ready
        # for commands.
        logger.log(logging.INFO8, "car_api_available returning True")

        if needSleep:
            # If you send charge_start/stop less than 1 second after calling
            # update_location(), the charge command usually returns:
            #   {'response': {'result': False, 'reason': 'could_not_wake_buses'}}
            # I'm not sure if the same problem exists when sending commands too
            # quickly after we send wake_up.  I haven't seen a problem sending a
            # command immediately, but it seems safest to sleep 5 seconds after
            # waking before sending a command.
            time.sleep(5)

        return True

    def is_location_home(self, lat, lon):

        if self.master.getHomeLatLon()[0] == 10000:
            logger.info(
                "Home location for vehicles has never been set.  "
                + "We'll assume home is where we found the first vehicle currently parked.  "
                + "Home set to lat="
                + str(lat)
                + ", lon="
                + str(lon)
            )
            self.master.setHomeLat(lat)
            self.master.setHomeLon(lon)
            self.master.queue_background_task({"cmd": "saveSettings"})
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
        if (
            abs(self.master.getHomeLatLon()[0] - lat) > 0.0289
            or abs(self.master.getHomeLatLon()[1] - lon) > 0.0289
        ):
            return False

        return True

    def car_api_charge(self, charge):
        # Do not call this function directly.  Call by using background thread:
        # queue_background_task({'cmd':'charge', 'charge':<True/False>})

        now = time.time()
        apiResponseDict = {}
        if not charge:
            # Whenever we are going to tell vehicles to stop charging, set
            # vehicle.stopAskingToStartCharging = False on all vehicles.
            for vehicle in self.getCarApiVehicles():
                vehicle.stopAskingToStartCharging = False

        if now - self.getLastStartOrStopChargeTime() < 60:

            # Don't start or stop more often than once a minute
            logger.log(
                logging.DEBUG2,
                "car_api_charge return because not long enough since last carApiLastStartOrStopChargeTime",
            )
            return "error"

        if self.car_api_available(charge=charge) is False:
            logger.log(
                logging.INFO8,
                "car_api_charge return because car_api_available() == False",
            )
            return "error"

        startOrStop = "start" if charge else "stop"
        result = "success"
        logger.log(logging.INFO8, "startOrStop is set to " + str(startOrStop))

        for vehicle in self.getCarApiVehicles():
            if charge and vehicle.stopAskingToStartCharging:
                logger.log(
                    logging.INFO8,
                    "Don't charge "
                    + vehicle.name
                    + " because vehicle.stopAskingToStartCharging == True",
                )
                continue

            if not vehicle.ready():
                continue

            if (
                vehicle.update_charge()
                and vehicle.batteryLevel < self.minChargeLevel
                and not charge
            ):
                # If the vehicle's charge state is lower than the configured minimum,
                #   don't stop it from charging, even if we'd otherwise not charge.
                continue

            # Only update carApiLastStartOrStopChargeTime if car_api_available() managed
            # to wake cars.  Setting this prevents any command below from being sent
            # more than once per minute.
            self.updateLastStartOrStopChargeTime()

            if (
                self.config["config"]["onlyChargeMultiCarsAtHome"]
                and self.getVehicleCount() > 1
            ):
                # When multiple cars are enrolled in the car API, only start/stop
                # charging cars parked at home.

                if vehicle.update_location() is False:
                    result = "error"
                    continue

                if not vehicle.atHome:
                    # Vehicle is not at home, so don't change its charge state.
                    logger.info(
                        vehicle.name
                        + " is not at home.  Do not "
                        + startOrStop
                        + " charge."
                    )
                    continue

                # If you send charge_start/stop less than 1 second after calling
                # update_location(), the charge command usually returns:
                #   {'response': {'result': False, 'reason': 'could_not_wake_buses'}}
                # Waiting 2 seconds seems to consistently avoid the error, but let's
                # wait 5 seconds in case of hardware differences between cars.
                time.sleep(5)

            if charge:
                self.applyChargeLimit(self.lastChargeLimitApplied, checkArrival=True)

            url = "https://owner-api.teslamotors.com/api/1/vehicles/"
            url = url + str(vehicle.ID) + "/command/charge_" + startOrStop
            headers = {
                "accept": "application/json",
                "Authorization": "Bearer " + self.getCarApiBearerToken(),
            }

            # Retry up to 3 times on certain errors.
            for _ in range(0, 3):
                try:
                    req = requests.post(url, headers=headers)
                    logger.log(
                        logging.INFO8,
                        "Car API cmd charge_" + startOrStop + " " + str(req),
                    )
                    apiResponseDict = json.loads(req.text)
                except requests.exceptions.RequestException:
                    pass
                except json.decoder.JSONDecodeError:
                    pass

                try:
                    logger.log(
                        logging.INFO4,
                        vehicle.name
                        + ": "
                        + startOrStop
                        + " charge response"
                        + str(apiResponseDict),
                    )
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
                    if apiResponseDict["response"] is None:
                        # This generally indicates an error like 'vehicle
                        # unavailable', but it's not something I think the caller can do
                        # anything about, so return generic 'error'.
                        result = "error"
                        # Don't send another command to this vehicle for
                        # carApiErrorRetryMins mins.
                        self.updateCarApiLastErrorTime(vehicle)
                    else:
                        if apiResponseDict["response"]["result"] == True:
                            self.resetCarApiLastErrorTime(vehicle)
                        elif charge:
                            reason = apiResponseDict["response"]["reason"]
                            if reason == "complete" or reason == "charging":
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
                                logger.info(
                                    vehicle.name
                                    + " is done charging or already trying to charge.  Stop asking to start charging."
                                )
                                vehicle.stopAskingToStartCharging = True
                                self.resetCarApiLastErrorTime(vehicle)
                            elif reason == "could_not_wake_buses":
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
                                # Start charge failed with an error I
                                # haven't seen before, so wait
                                # carApiErrorRetryMins mins before trying again.
                                logger.info(
                                    'ERROR "'
                                    + reason
                                    + '" when trying to '
                                    + startOrStop
                                    + " car charging via Tesla car API.  Will try again later."
                                    + "\nIf this error persists, please file an issue at https://github.com/ngardiner/TWCManager/ with a copy of this error.",
                                )
                                result = "error"
                                self.updateCarApiLastErrorTime(vehicle)
                        else:
                            # Stop charge failed with an error I
                            # haven't seen before, so wait
                            # carApiErrorRetryMins mins before trying again.
                            reason = apiResponseDict["response"]["reason"]
                            logger.info(
                                'ERROR "'
                                + reason
                                + '" when trying to '
                                + startOrStop
                                + " car charging via Tesla car API.  Will try again later."
                                + "\nIf this error persists, please file an issue at https://github.com/ngardiner/TWCManager/ with a copy of this error.",
                            )
                            result = "error"
                            self.updateCarApiLastErrorTime(vehicle)

                except (KeyError, TypeError):
                    # This catches cases like trying to access
                    # apiResponseDict['response'] when 'response' doesn't exist in
                    # apiResponseDict.
                    logger.info(
                        "ERROR: Failed to "
                        + startOrStop
                        + " car charging via Tesla car API.  Will try again later."
                    )
                    self.updateCarApiLastErrorTime(vehicle)
                break

        if self.getLastStartOrStopChargeTime() == now:
            logger.info("Car API " + startOrStop + " charge result: " + result)

        return result

    def applyChargeLimit(self, limit, checkArrival=False, checkDeparture=False):

        if limit != -1 and (limit < 50 or limit > 100):
            logger.log(logging.INFO8, "applyChargeLimit skipped")
            return "error"

        if not self.car_api_available():
            logger.log(
                logging.INFO8,
                "applyChargeLimit return because car_api_available() == False",
            )
            return "error"

        now = time.time()
        if (
            not checkArrival
            and not checkDeparture
            and now - self.carApiLastChargeLimitApplyTime < 60
        ):
            # Don't change limits more often than once a minute
            logger.log(
                logging.DEBUG2,
                "applyChargeLimit return because under 60 sec since last carApiLastChargeLimitApplyTime",
            )
            return "error"

        # We need to try to apply limits if:
        #   - We think the car is at home and the limit has changed
        #   - We think the car is at home and we've been asked to check for departures
        #   - We think the car is at home and we notice it gone
        #   - We think the car is away from home and we've been asked to check for arrivals
        #
        # We do NOT opportunistically check for arrivals, because that would be a
        # continuous API poll.
        needToWake = False
        for vehicle in self.carApiVehicles:
            (wasAtHome, outside, lastApplied) = self.master.getNormalChargeLimit(
                vehicle.ID
            )
            # Don't wake cars to tell them about reduced limits;
            # only wake if they might be able to charge further now
            if wasAtHome and (limit > (lastApplied if lastApplied != -1 else outside)):
                needToWake = True
                vehicle.stopAskingToStartCharging = False
            if (
                wasAtHome
                and (
                    limit != lastApplied
                    or checkDeparture
                    or (vehicle.update_location(cacheTime=3600) and not vehicle.atHome)
                )
            ) or (not wasAtHome and checkArrival):
                vehicle.stopTryingToApplyLimit = False

        if needToWake and self.car_api_available(applyLimit=True) is False:
            logger.log(
                logging.INFO8,
                "applyChargeLimit return because car_api_available() == False",
            )
            return "error"

        if self.lastChargeLimitApplied != limit:
            if limit != -1:
                logger.log(
                    logging.INFO2,
                    "Attempting to apply limit of "
                    + str(limit)
                    + "% to all vehicles at home",
                )
            else:
                logger.log(
                    logging.INFO2,
                    "Attempting to restore charge limits for all vehicles at home",
                )
            self.lastChargeLimitApplied = limit

        self.carApiLastChargeLimitApplyTime = now

        needSleep = False
        for vehicle in self.carApiVehicles:
            if vehicle.stopTryingToApplyLimit or not vehicle.ready():
                continue

            located = vehicle.update_location()
            (wasAtHome, outside, lastApplied) = self.master.getNormalChargeLimit(
                vehicle.ID
            )
            forgetVehicle = False
            if not vehicle.update_charge():
                # We failed to read the "normal" limit; don't risk changing it.
                continue

            if not wasAtHome and located and vehicle.atHome:
                logger.log(logging.INFO2, vehicle.name + " has arrived")
                outside = vehicle.chargeLimit
            elif wasAtHome and located and not vehicle.atHome:
                logger.log(logging.INFO2, vehicle.name + " has departed")
                forgetVehicle = True

            if limit == -1 or (located and not vehicle.atHome):
                # We're removing any applied limit, provided it hasn't been manually changed
                #
                # If lastApplied == -1, the manual-change path is always selected.
                if wasAtHome and vehicle.chargeLimit == lastApplied:
                    if vehicle.apply_charge_limit(outside):
                        logger.log(
                            logging.INFO2,
                            "Restoring "
                            + vehicle.name
                            + " to charge limit "
                            + str(outside)
                            + "%",
                        )
                        vehicle.stopTryingToApplyLimit = True
                else:
                    # If the charge limit has been manually changed, user action overrides the
                    # saved charge limit.  Leave it alone.
                    vehicle.stopTryingToApplyLimit = True
                    outside = vehicle.chargeLimit

                if vehicle.stopTryingToApplyLimit:
                    if forgetVehicle:
                        self.master.removeNormalChargeLimit(vehicle.ID)
                    else:
                        self.master.saveNormalChargeLimit(vehicle.ID, outside, -1)
            else:
                if vehicle.chargeLimit != limit:
                    if vehicle.apply_charge_limit(limit):
                        logger.log(
                            logging.INFO2,
                            "Set "
                            + vehicle.name
                            + " to charge limit of "
                            + str(limit)
                            + "%",
                        )
                        vehicle.stopTryingToApplyLimit = True
                else:
                    vehicle.stopTryingToApplyLimit = True

                if vehicle.stopTryingToApplyLimit:
                    self.master.saveNormalChargeLimit(vehicle.ID, outside, limit)

            if vehicle.atHome and vehicle.stopTryingToApplyLimit:
                needSleep = True

        if needSleep:
            # If you start charging too quickly after setting the charge limit,
            # the vehicle sometimes refuses the start command because it's
            # "fully charged" under the old limit, but then continues to say
            # charging was stopped once the new limit is in place.
            time.sleep(5)

        if checkArrival:
            self.updateChargeAtHome()

    def getApiCaptcha(self):
        # This will fetch the current Captcha image displayed by Tesla's auth
        # website, and store it in memory

        self.__apiCaptcha = self.session.get(self.captchaURL)

    def getCaptchaImage(self):
        # This will serve the Tesla Captcha image

        if self.__apiCaptcha:
            return self.__apiCaptcha.content
        else:
            logger.log(
                logging.INFO2,
                "ERROR: Captcha image requested, but we have none buffered. This is likely due to a stale login session, but if you see it regularly, please report it.",
            )
            return ""

    def getCarApiBearerToken(self):
        return self.carApiBearerToken

    def getCarApiErrorRetryMins(self, vehicle=None):
        errorCount = self.errorCount
        if vehicle:
            errorCount = max(vehicle.errorCount, errorCount)
        errorCount = max(errorCount - 1, 0)
        return min(errorCount, 10)

    def getCarApiLastErrorTime(self):
        return self.carApiLastErrorTime

    def getCarApiRefreshToken(self):
        return self.carApiRefreshToken

    def getCarApiRetryRemaining(self, vehicle=None):
        # Calculate the amount of time remaining until the API can be queried
        # again. This is the api backoff time minus the difference between now
        # and the last error time

        # The optional vehicleLast parameter allows passing the last error time
        # for an individual vehicle, rather than the entire API.
        lastError = self.getCarApiLastErrorTime()
        if vehicle:
            lastError = max(vehicle.lastErrorTime, lastError)

        if lastError == 0:
            return 0
        else:
            backoff = self.getCarApiErrorRetryMins(vehicle) * 60
            lasterrortime = time.time() - lastError
            if lasterrortime >= backoff:
                return 0
            else:
                logger.log(
                    logging.DEBUG2,
                    "Backoff is "
                    + str(backoff)
                    + ", lasterror delta is "
                    + str(lasterrortime)
                    + ", last error was "
                    + str(lastError),
                )
                return int(backoff - lasterrortime)

    def getCarApiTokenExpireTime(self):
        return self.carApiTokenExpireTime

    def getLastStartOrStopChargeTime(self):
        return int(self.carApiLastStartOrStopChargeTime)

    def getVehicleByID(self, vehicleID):
        # Returns the vehicle object identified by the given ID
        for vehicle in self.getCarApiVehicles():
            if vehicle.ID == vehicleID:
                return vehicle
        return False

    def getVehicleCount(self):
        # Returns the number of currently tracked vehicles
        return int(len(self.carApiVehicles))

    def getCarApiVehicles(self):
        return self.carApiVehicles

    def getMFADevices(self, transaction_id):
        # Requests a list of devices we can use for MFA
        url = f"https://auth.tesla.com/oauth2/v3/authorize/mfa/factors?transaction_id={transaction_id}"
        resp = self.session.get(url)
        try:
            content = json.loads(resp.text)
        except ValueError:
            return False
        except json.decoder.JSONDecodeError:
            return False

        if resp.status_code == 200:
            return content["data"]
        elif resp.status_code == 400:
            logger.error(
                "The following error was returned when attempting to fetch MFA devices for Tesla Login:"
                + str(content.get("error", ""))
            )
        else:
            logger.error(
                "An unexpected error code ("
                + str(resp.status)
                + ") was returned when attempting to fetch MFA devices for Tesla Login"
            )

    def mfaLogin(self, transactionID, mfaDevice, mfaCode):
        data = {
            "transaction_id": transactionID,
            "factor_id": mfaDevice,
            "passcode": str(mfaCode).rjust(6, "0"),
        }
        url = "https://auth.tesla.com/oauth2/v3/authorize/mfa/verify"
        resp = self.session.post(url, json=data)

        try:
            jsonData = json.loads(resp.text)
        except ValueError:
            return False
        except json.decoder.JSONDecodeError:
            return False

        if (
            "error" in resp.text
            or not jsonData.get("data", None)
            or not jsonData["data"].get("approved", None)
            or not jsonData["data"].get("valid", None)
        ):
            if (
                jsonData.get("error", {}).get("message", None)
                == "Invalid Attributes: Your passcode should be six digits."
            ):
                return "TokenLengthError"
            else:
                return "TokenFail"
        else:
            data = {"transaction_id": transactionID}
            return self.apiLoginPhaseTwo(data)

    def resetCarApiLastErrorTime(self, vehicle=None):
        self.carApiLastErrorTime = 0
        if vehicle:
            vehicle.lastErrorTime = 0
            vehicle.errorCount = 0
        self.errorCount = 0
        return True

    def setCarApiBearerToken(self, token=None):
        if token:
            # TODO: Should not be hardcoded
            tokenSync = False
            if self.master.tokenSyncEnabled():
                # We won't accept tokens if Token Sync is already in place
                return False
            else:
                self.carApiBearerToken = token
                return True
        else:
            return False

    def setCarApiRefreshToken(self, token):
        self.carApiRefreshToken = token
        return True

    def setCarApiTokenExpireTime(self, value):
        self.carApiTokenExpireTime = value
        return True

    def setChargeRate(self, charge_rate, vehicle=None):

        # As a fallback to allow initial implementation of the charge rate functionality for single car installs,
        # If no vehcle is specified, we take the first returned to us.

        if not vehicle:
            vehicle = self.getCarApiVehicles()[0]

        vehicle.lastAPIAccessTime = time.time()

        url = "https://owner-api.teslamotors.com/api/1/vehicles/"
        url = url + str(vehicle.ID) + "/command/set_charging_amps"

        headers = {
            "accept": "application/json",
            "Authorization": "Bearer " + self.getCarApiBearerToken(),
        }

        body = {"charging_amps": charge_rate}

        try:
            req = requests.post(url, headers=headers, json=body)
            logger.log(logging.INFO8, "Car API cmd set_charging_amps" + str(req))
            apiResponseDict = json.loads(req.text)
        except requests.exceptions.RequestException:
            return False
        except json.decoder.JSONDecodeError:
            return False

        return apiResponseDict

    def submitCaptchaCode(self, code, interface):
        self.__apiCaptchaCode = code
        self.__apiCaptchaInterface = interface
        return self.apiLoginPhaseOne()

    def updateCarApiLastErrorTime(self, vehicle=None):
        timestamp = time.time()
        logger.log(
            logging.INFO8,
            "updateCarApiLastErrorTime() called due to Tesla API Error. Updating timestamp from "
            + str(self.carApiLastErrorTime)
            + " to "
            + str(timestamp),
        )
        if vehicle:
            vehicle.lastErrorTime = timestamp
            vehicle.errorCount += 1
        else:
            self.carApiLastErrorTime = timestamp
            self.errorCount += 1

        return True

    def updateLastStartOrStopChargeTime(self):
        self.carApiLastStartOrStopChargeTime = time.time()
        return True

    def updateChargeAtHome(self):
        for car in self.carApiVehicles:
            if car.atHome:
                car.update_charge()
        self.lastChargeCheck = time.time()

    def wakeVehicle(self, vehicle):
        apiResponseDict = None
        vehicle.lastAPIAccessTime = time.time()

        url = "https://owner-api.teslamotors.com/api/1/vehicles/"
        url = url + str(vehicle.ID) + "/wake_up"

        headers = {
            "accept": "application/json",
            "Authorization": "Bearer " + self.getCarApiBearerToken(),
        }
        try:
            req = requests.post(url, headers=headers)
            logger.log(logging.INFO8, "Car API cmd wake_up" + str(req))
            apiResponseDict = json.loads(req.text)
        except requests.exceptions.RequestException:
            return False
        except json.decoder.JSONDecodeError:
            return False

        return apiResponseDict

    @property
    def numCarsAtHome(self):
        return len([car for car in self.carApiVehicles if car.atHome])

    @property
    def minBatteryLevelAtHome(self):
        if time.time() - self.lastChargeCheck > self.chargeUpdateInterval:
            self.master.queue_background_task({"cmd": "checkCharge"})
        return min(
            [car.batteryLevel for car in self.carApiVehicles if car.atHome],
            default=10000,
        )


class CarApiVehicle:

    carapi = None
    __config = None
    debuglevel = 0
    ID = None
    name = ""
    syncSource = "TeslaAPI"
    VIN = ""

    firstWakeAttemptTime = 0
    lastAPIAccessTime = 0
    delayNextWakeAttempt = 0
    lastLimitAttemptTime = 0

    errorCount = 0
    lastErrorTime = 0
    lastDriveStatusTime = 0
    lastChargeStatusTime = 0
    stopAskingToStartCharging = False
    stopTryingToApplyLimit = False

    batteryLevel = 10000
    chargeLimit = -1
    lat = 10000
    lon = 10000
    atHome = False
    timeToFullCharge = 0.0

    # Sync values are updated by an external module such as TeslaMate
    syncTimestamp = 0
    syncTimeout = 60 * 60
    syncLat = 10000
    syncLon = 10000
    syncState = "asleep"

    def __init__(self, json, carapi, config):
        self.carapi = carapi
        self.__config = config
        self.ID = json["id"]
        self.VIN = json["vin"]
        self.name = json["display_name"]

        # Launch sync monitoring thread
        Thread(target=self.checkSyncNotStale).start()

    def checkSyncNotStale(self):
        # Once an external system begins providing sync functionality to defer
        # Tesla API queries and provide already fetched information, there is a
        # potential condition which may occur in which the external system goes
        # away and leaves us with stale data.

        # To guard against this, this threaded function will loop every x minutes
        # and check the last sync timestamp. If it has not updated in that interval,
        # we switch back to using the API

        while True:
            if (
                self.syncSource != "TeslaAPI"
                and self.self.is_awake()
                and (self.syncTimestamp < (time.time() - self.syncTimeout))
            ):
                logger.error(
                    "Data from "
                    + self.syncSource
                    + " for "
                    + self.name
                    + " is stale. Switching back to TeslaAPI"
                )
                self.syncSource = "TeslaAPI"
            time.sleep(self.syncTimeout)

    def ready(self):
        if self.carapi.getCarApiRetryRemaining(self):
            # It's been under carApiErrorRetryMins minutes since the car API
            # generated an error on this vehicle. Return that car is not ready.
            logger.log(
                logging.INFO8,
                self.name
                + " not ready because of recent lastErrorTime "
                + str(self.lastErrorTime),
            )
            return False

        if (
            self.firstWakeAttemptTime == 0
            and time.time() - self.lastAPIAccessTime < 2 * 60
        ):
            # If it's been less than 2 minutes since we successfully woke this car, it
            # should still be awake.  No need to check.  It returns to sleep state about
            # two minutes after the last command was issued.
            return True

        # This can check whether the car is online; if so, it will likely stay online for
        # two minutes.
        if self.is_awake():
            self.firstWakeAttemptTime = 0
            return True

        logger.log(
            logging.INFO8,
            self.name + " not ready because it wasn't woken in the last 2 minutes.",
        )
        return False

    # Permits opportunistic API requests
    def is_awake(self):
        if self.syncSource == "TeslaAPI":
            url = "https://owner-api.teslamotors.com/api/1/vehicles/" + str(self.ID)
            (result, response) = self.get_car_api(
                url, checkReady=False, provesOnline=False
            )
            return result and response.get("state", "") == "online"
        else:
            return (
                self.syncState == "online"
                or self.syncState == "charging"
                or self.syncState == "updating"
                or self.syncState == "driving"
            )

    def get_car_api(self, url, checkReady=True, provesOnline=True):
        if checkReady and not self.ready():
            return False, None

        apiResponseDict = {}

        headers = {
            "accept": "application/json",
            "Authorization": "Bearer " + self.carapi.getCarApiBearerToken(),
        }

        # Retry up to 3 times on certain errors.
        for _ in range(0, 3):
            try:
                req = requests.get(url, headers=headers)
                logger.log(logging.INFO8, "Car API cmd " + url + " " + str(req))
                apiResponseDict = json.loads(req.text)
                # This error can happen here as well:
                #   {'response': {'reason': 'could_not_wake_buses', 'result': False}}
                # This one is somewhat common:
                #   {'response': None, 'error': 'vehicle unavailable: {:error=>"vehicle unavailable:"}', 'error_description': ''}
            except requests.exceptions.RequestException:
                pass
            except json.decoder.JSONDecodeError:
                pass

            try:
                logger.debug("Car API vehicle status" + str(apiResponseDict))

                response = apiResponseDict["response"]

                # A successful call to drive_state will not contain a
                # response['reason'], so we check if the 'reason' key exists.
                if (
                    "reason" in response
                    and response["reason"] == "could_not_wake_buses"
                ):
                    # Retry after 5 seconds.  See notes in car_api_charge where
                    # 'could_not_wake_buses' is handled.
                    time.sleep(5)
                    continue
            except (KeyError, TypeError):
                # This catches cases like trying to access
                # apiResponseDict['response'] when 'response' doesn't exist in
                # apiResponseDict.
                logger.info(
                    "ERROR: Can't access vehicle status for "
                    + self.name
                    + ".  Will try again later."
                )
                self.carapi.updateCarApiLastErrorTime(self)
                return False, None

            if provesOnline:
                self.lastAPIAccessTime = time.time()

            return (True, response)
        else:
            self.carapi.updateCarApiLastErrorTime(self)
            return (False, None)

    def update_location(self, cacheTime=60):

        if self.syncSource == "TeslaAPI":
            url = "https://owner-api.teslamotors.com/api/1/vehicles/"
            url = url + str(self.ID) + "/data_request/drive_state"

            now = time.time()

            if now - self.lastDriveStatusTime < cacheTime:
                return True

            try:
                (result, response) = self.get_car_api(url)
            except TypeError:
                logger.log(logging.error, "Got None response from get_car_api()")
                return False

            if result:
                self.lastDriveStatusTime = now
                self.lat = response["latitude"]
                self.lon = response["longitude"]
                self.atHome = self.carapi.is_location_home(self.lat, self.lon)

            return result

        else:

            self.lat = self.syncLat
            self.lon = self.syncLon
            self.atHome = self.carapi.is_location_home(self.lat, self.lon)

            return True

    def update_charge(self):

        if self.syncSource == "TeslaAPI":

            url = "https://owner-api.teslamotors.com/api/1/vehicles/"
            url = url + str(self.ID) + "/data_request/charge_state"

            now = time.time()

            if now - self.lastChargeStatusTime < 60:
                return True

            try:
                (result, response) = self.get_car_api(url)
            except TypeError:
                logger.log(logging.error, "Got None response from get_car_api()")
                return False

            if result:
                self.lastChargeStatusTime = time.time()
                self.chargeLimit = response["charge_limit_soc"]
                self.batteryLevel = response["battery_level"]
                self.timeToFullCharge = response["time_to_full_charge"]

            return result

        else:

            return True

    def apply_charge_limit(self, limit):
        if self.stopTryingToApplyLimit:
            return True

        now = time.time()

        if (
            now - self.lastLimitAttemptTime <= 300
            or self.carapi.getCarApiRetryRemaining(self)
        ):
            return False

        if self.ready() is False:
            return False

        self.lastLimitAttemptTime = now

        url = "https://owner-api.teslamotors.com/api/1/vehicles/"
        url = url + str(self.ID) + "/command/set_charge_limit"

        headers = {
            "accept": "application/json",
            "Authorization": "Bearer " + self.carapi.getCarApiBearerToken(),
        }
        body = {"percent": limit}

        for _ in range(0, 3):
            try:
                req = requests.post(url, headers=headers, json=body)
                logger.log(logging.INFO8, "Car API cmd set_charge_limit " + str(req))

                apiResponseDict = json.loads(req.text)
            except requests.exceptions.RequestException:
                pass
            except json.decoder.JSONDecodeError:
                pass

            result = False
            reason = ""
            try:
                result = apiResponseDict["response"]["result"]
                reason = apiResponseDict["response"]["reason"]
            except (KeyError, TypeError):
                # This catches unexpected cases like trying to access
                # apiResponseDict['response'] when 'response' doesn't exist
                # in apiResponseDict.
                result = False

            if result is True or reason == "already_set":
                self.stopTryingToApplyLimit = True
                self.lastAPIAccessTime = now
                self.carapi.resetCarApiLastErrorTime(self)
                return True
            elif reason == "could_not_wake_buses":
                time.sleep(5)
                continue
            else:
                self.carapi.updateCarApiLastErrorTime(self)

        return False
