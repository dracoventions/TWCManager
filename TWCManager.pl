#!/usr/bin/perl

########################################################################
# Perl code and TWC protocol reverse engineering by Chris Dragon who
# can be contacted at http://support.dracoventions.com
#
# Additional logs and hints provided by Teslamotorsclub.com users:
# TheNoOne, MITE46, IanAmber, and twc.
# See https://teslamotorsclub.com/tmc/threads/new-wall-connector-load-sharing-protocol.72830
# Thank you!
#
# Source code and protocol knowledge are hereby released to the
# general public free for personal or commercial use.  I hope the
# knowledge will be used to increase the use of green energy sources by
# controlling the time and power level of car charging.

########################################################################
# What's this script good for?
#
# This script (TWCManager) pretends to be a Tesla Wall Charger (TWC) set
# to master mode.  When wired to the IN or OUT pins of real TWC units
# set to slave mode (rotary switch position F), TWCManager can tell them
# to limit car charging to any amp value between 0.01A and 80.00A.
# Tesla vehicles interpret any amp value below 1.00A to mean don't
# charge the car at all.
#
# This level of control is useful for having TWCManager track the
# real-time availability of green energy sources and direct the slave
# TWCs to use the exact amount of energy available.  This saves energy
# compared to sending the green energy off to a battery for later car
# charging or off to the grid where some of it is lost in transmission.
#
# TWCManager can also be set up to only allow charging during certain
# hours, stop charging if a grid overload or "save power day" is
# detected, stop charging on one TWC when a "more important" one is
# plugged in, or whatever else you can think of.
#
# One thing TWCManager does not have direct access to is the battery
# charge percentage of each plugged-in car.  It can tell when a car is
# near full and requesting less power, but not how full it is.  This is
# unfortunate, but if you own a Tesla vehicle being charged, people have
# figured out how to get its charge state by contacting Tesla's servers
# using the same password you use in the Tesla phone app.  Be very
# careful not to expose that password because it allows unlocking and
# starting the car.

########################################################################
# Overview of protocol TWCs use to load share
#
# I'm skipping many details, but the general idea is:
#
# TWC set to slave mode (rotary switch position F) sends a linkready
# message every 10 seconds.
# The message contains a unique 4-byte id that identifies that particular
# slave as the sender of the message.
#
# TWC set to master mode sees a linkready message.  It sends a heartbeat
# message containing the slave's 4-byte id as the intended recipeint of
# the message.
# The master's 4-byte id is included as the sender of the message.
#
# Slave sees a heartbeat message from master directed to its unique 4-byte
# id and responds with its own heartbeat message containing the master's
# 4-byte id as the intended recipient of the message.
# The slave's 4-byte id is included as the sender of the message.
#
# Master sends a heartbeat to a slave around once per second and expects
# a response heartbeat from the slave.
# Slaves do not send heartbeats without seeing one from a master first.
# If heartbeats stop coming from master, slave resumes sending linkready
# every 10 seconds.
# If slaves stop replying to heartbeats from master, master's behavior
# is more complex but it generally keeps trying to contact the slave at
# less frequent intervals and I think it gives up eventually.
#
# Heartbeat messages contain a 7-byte data block used to negotiate the
# amount of power available to each slave and to the master.
# The first byte is a status indicating things like is TWC plugged in,
# does it want power, is there an error, etc.
# Next two bytes indicate the amount of power requested or the amount
# allowed in 0.01 amp increments.
# Next two bytes indicate the amount of power being used by the TWC,
# also in 0.01 amp increments.  TWCs report power use around 0.25A
# when not plugged in to a car.
# Last two bytes seem to be unused and always contain a value of 0.


use Fcntl;
use POSIX;
use Time::HiRes qw(usleep nanosleep);
use warnings;
use strict;

# This makes print output to screen immediately instead of waiting till
# the end of the line is reached.
$| = 1;


##########################
#
# Configuration parameters
#

# Most users will have only one ttyUSB adapter plugged in and default
# value of '/dev/ttyUSB0' below will work.
# If not, run 'dmesg |grep ttyUSB' on the command line to find your
# rs485 adapter and put its ttyUSB# value in the parameter below.
my $rs485Adapter = '/dev/ttyUSB0';

# Choose how much debugging info to output.
# 0 is no output other than errors.
# 1 is just the most useful info.
# 10 is all info.
my $debugLevel = 1;

# Normally we fake being a TWC Master.  Set $fakeMaster = 0 to fake a
# slave instead (only useful for debugging and protocol reversing).
my $fakeMaster = 1;

# TWC's rs485 port runs at 9600 baud which has been verified with an
# oscilloscope.  Don't change this unless something changes in future
# hardware.
my $baud = 9600;

# Original fakeTWCID was "\x0a\x51" which got generated randomly by an
# actual TWC.  Switched to 7777 to make the fake id easier to spot in
# data logs.
my $fakeTWCID = "\x77\x77";

# TWCs send a seemingly-random byte after their 2-byte TWC id in a number
# of messages.  I call this byte their "Sign" for lack of a better term.
# The byte never changes unless the TWC is reset or power cycled.  We
# use hard-coded values for now because I don't know if there are any
# rules to what values can be chosen.  I picked 77 because it's easy to
# recognize when looking at logs.
my $masterSign = "\x77";
my $slaveSign = "\x77";


#
# End configuration parameters
#
##############################


my ($data, $dataLen);
my ($msg, $msgLen) = ('', 0);

# 'raw' and '-echo' options are necessary with the FTDI chipset to avoid
# corrupt output or missing data.
system("stty -F $rs485Adapter raw -echo $baud cs8 -cstopb -parenb");

sysopen(TWC, "$rs485Adapter", O_RDWR | O_NONBLOCK) or die "Can't open $rs485Adapter";
binmode TWC, ":raw";

my @masterStatus = (0x00,0x00,0x00,0x00,0x00,0x00,0x00); # This also works but not as compact: unpack('C*', "\x00\x00\x00\x00\x00\x00\x00");
my @slaveStatus = (0x04,0x00,0x00,0x00,0x19,0x00,0x00);
my $initMsgs = 10;
my $msgRxCount = 0;
my $lastTxTimestamp = 0;
my @slaveTWCIDs = ();
my %slaveLastRxTimestamp;
my $slaveIdxToGetNextStatus = 0;
my $totalAmpsMax = 1;
my $lastGreenEnergyCheckTimestamp = 0;
my $lastHeartbeatDebugOutput = '';
my $lastHeartbeatDebugOutputTimestamp = 0;
#my $testTimer = undef;

printf("TWC Manager starting as fake %s with id %02x%02x and sign %02x\n\n",
    ($fakeMaster ? "Master" : "Slave"),
	vec($fakeTWCID, 0, 8), vec($fakeTWCID, 1, 8),
	vec($slaveSign, 0, 8));


for(;;) {
	# In this area, we always send a linkready message when we first
	# start.
	# Whenever there is no data available from other TWCs to respond to,
	# we'll loop back to this point to send another linkready or
	# heartbeat message.
	# By only sending our periodic messages when no incoming message
	# data is available, we reduce the chance that we will start
	# transmitting a message in the middle of an incoming message, which
	# would corrupt both messages.
	if($fakeMaster) {
		# A real master sends 5 copies of linkready1 and linkready2
		# whenever it starts up, which we do here.
		if($initMsgs > 5) {
			send_master_linkready1();
			usleep(100); # give slave time to respond
			$initMsgs--;
		}
		elsif($initMsgs > 0) {
			send_master_linkready2();
			usleep(100); # give slave time to respond
			$initMsgs--;
		}
		else {
			# After finishing the 5 startup linkready1 and linkready2
			# messages, master will send a heartbeat message to every
			# slave it's received a linkready message from.  Do that here.
			if(time - $lastTxTimestamp > 0) {
				# It's been about a second since our last heartbeat.
				if(@slaveTWCIDs > 0) {
					my $slaveID = $slaveTWCIDs[$slaveIdxToGetNextStatus];
					if(time - $slaveLastRxTimestamp{$slaveID} > 26) {
						# A real master stops sending heartbeats to a
						# slave that hasn't responded for ~26 seconds.
						# It may still send the slave a heartbeat every
						# once in awhile but we're just going to scratch
						# the slave from our little black book and add
						# them again if they ever send us a linkready.
						print("WARNING: We haven't heard from slave "
							. "%02x%02x for over 26 seconds.  "
							. "Stop sending them heartbeat messages.\n\n",
							vec($slaveID, 0, 8), vec($slaveID, 1, 8));
						delete_slave($slaveID);
					}
					else {
						send_heartbeat($slaveID);
					}
					
					$slaveIdxToGetNextStatus++;
					if($slaveIdxToGetNextStatus >= @slaveTWCIDs) {
						$slaveIdxToGetNextStatus = 0;
					}
					usleep(100); # give slave time to respond
				}
			}
			if(time - $lastGreenEnergyCheckTimestamp > 60) {
				# I check my solar panel generation using an API exposed
				# by The Energy Detective (TED).  It's a piece of hardware
				# available at http://www.theenergydetective.com/
				# You may also be able to find a way to query a solar
				# system on the roof using an API provided by your solar
				# installer.  Most of those systems only update the
				# amount of power the system is producing every 15
				# minutes at most, though that's fine for tweaking your
				# car charging.
				#
				# The curl command used below can be used to 
				# communicate with almost any web API, even ones that 
				# require POST values or authentication. -s option 
				# prevents curl from displaying download stats. -m 4 
				# prevents the whole operation from taking over 4 
				# seconds.  If your service regularly takes a long 
				# time to respond, you'll have to query it in a 
				# background process and have the process update a 
				# file that you check here.  If we delay over 9ish 
				# seconds here, slave TWCs will decide we've 
				# disappeared and stop charging or maybe it's more 
				# like 20-30 seconds - I didn't test carefully).
				my $greenEnergyData = `curl -s -m 4 "http://127.0.0.1/history/export.csv?T=1&D=0&M=1&C=1"`;
				
				# In my case, $greenEnergyData will contain something
				# like this:
				#   MTU, Time, Power, Cost, Voltage
				#   Solar,11/11/2017 14:20:43,-2.957,-0.29,124.3
				# The only part we care about is -2.957 which is negative
				# kWh currently being generated.
				if($greenEnergyData =~ m~^Solar,[^,]+,-([^, ]+),~m) {
					my $solarWh = int($1 * 1000);
					
					# Watts = Volts * Amps
					# Car charges at 240 volts in the U.S. so we figure
					# out how many amps * 240 = $solarWh and limit the
					# car to that many amps.
					# Note that $totalAmpsMax is in 0.01A units, so
					# $totalAmpsMax 100 = 1A, 1567 = 15.67A, etc.
					$totalAmpsMax = int(($solarWh / 240) * 100);
					
					print("Solar generating " . $solarWh 
						. "wH so limit car charging to "
						. ($totalAmpsMax / 100) . "A.\n");
				}
				else {
					print("ERROR: Can't determine current solar generation.\n\n");
				}
				$lastGreenEnergyCheckTimestamp = time;
			}
		}
	}
	else {
		# As long as a slave is running, it sends link ready
		# messages every 10 seconds.  They trigger any master on the
		# network to handshake with the slave and the master then
		# sends a status update from the slave every 1-3 seconds.
		# Master's status updates trigger the slave to send back its own
		# status update.
		# As long as master has sent a status update within the
		# last 10 seconds, slaves don't send link ready.
		# I've also verified that masters don't care if we stop sending
		# link ready as long as we send status updates in response
		# to master's status updates.
		if(time - $lastTxTimestamp >= 10) {
			if($debugLevel >= 1) {
				printf("Advertise fake slave %02x%02x with sign %02x is "
					. "ready to link once per 10 seconds as long as master "
					. "hasn't sent a heartbeat in the last 10 seconds.\n",
					vec($fakeTWCID, 0, 8), vec($fakeTWCID, 1, 8),
					vec($slaveSign, 0, 8));
			}
			send_slave_linkready();
		}
	}
	
	for(;;) {
		$dataLen = sysread(TWC, $data, 1);
		if(!defined($dataLen) && $!{EAGAIN}) {
			if($msgLen == 0) {
				# No message data waiting and we haven't received the
				# start of a new message yet.  Break out of inner for(;;)
				# to continue at top of outer for(;;) loop where we may
				# decide to send a periodic message.
				last;
			}
			else {
				# No message data waiting but we've received a partial
				# message that we should wait to finish receiving.
				usleep(10);
				next;
			}
		}
		if($dataLen != 1) {
			# This should never happen
			print("WARNING: No data available.\n");
			next;
		}
		
		if($msgLen == 0 && ord($data) != 0xc0) {
			# If you see this when the program is first started, it
			# means we started listening in the middle of the TWC
			# sending a message so we didn't see the 0xc0 char that
			# starts a message.  That's unavoidable.
			# If you see this any other time, it means there was some
			# corruption in what we received.  It's normal for that to
			# happen every once in awhile.
			if($debugLevel >= 10) {
				printf("Got unexpected byte %02x at start of msg.\n", ord($data));
			}
			next;
		}
		if($msgLen == 1 && ord($data) == 0xfe) {
			# This happens if we receive a message starting in the
			# middle, discard its bytes till the last c0, then find
			# fe on the next pass.  Discard what we've got and
			# expect a new message to start.
			if($debugLevel >= 10) {
				printf("Found end of message before full-length message received.  Discard and wait for new message.\n", ord($data));
			}
			$msgLen = 0;
			next;
		}
		
		vec($msg, $msgLen, 8) = ord($data);
		$msgLen++;
		
		# Messages are at least 17 bytes long and always end with
		# \xc0\xfe.
		#
		# Messages can be over 17 bytes long when special values are
		# "escaped" as two bytes.  See notes in send_msg.
		#
		# Due to corruption caused by lack of termination resistors,
		# messages may end in \xc0\x02\0x00 instead, so we also
		# accept that.  See notes in unescape_msg.
		if($msgLen >= 17
		     &&
		   (
			 vec($msg, $msgLen - 2, 8) == 0xc0
			   &&
		     vec($msg, $msgLen - 1, 8) == 0xfe
		   )
		     ||
		   (
			 vec($msg, $msgLen - 3, 8) == 0xc0
			   &&
		     vec($msg, $msgLen - 2, 8) == 0x02
			   &&
		     vec($msg, $msgLen - 1, 8) == 0x00
		   )
		) {
			$msg = unescape_msg($msg, $msgLen);
			
			# Set msgLen = 0 at start so we don't have to do it on errors
			# below.
			$msgLen = 0;
			
			$msgRxCount++;
			
			if($debugLevel >= 10) {
				print("Rx@" . time_now() . ": " . hex_str($msg) . "\n");
			}
			
			if(length($msg) != 17) {
				# After unescaping special values and removing corruption,
				# a message should always be 17 bytes long.
				printf("ERROR: Ignoring message of unexpected length %d: %s\n",
					length($msg), hex_str($msg));
				next;
			}
			
			my $checksumExpected = vec($msg, 14, 8);
			my $checksum = vec($msg, 2, 8) + vec($msg, 3, 8) + vec($msg, 4, 8)
				+ vec($msg, 5, 8) + vec($msg, 6, 8) + vec($msg, 7, 8)
				+ vec($msg, 8, 8) + vec($msg, 9, 8) + vec($msg, 10, 8)
				+ vec($msg, 11, 8) + vec($msg, 12, 8) + vec($msg, 13, 8);
			if(($checksum & 0xFF) != $checksumExpected) {
				printf("ERROR: Checksum %x does not match %02x.  Ignoring message: %s\n",
					$checksum, $checksumExpected, hex_str($msg));
				next;
			}
			
			if($fakeMaster) {
				############################
				# Pretend to be a master TWC
				
				if($msg =~ /\xc0\xfd\xe2(..)(.)\x1f\x40\x00\x00\x00\x00\x00\x00.\xc0\xfe/s) {
					# Handle linkready message from slave.
					#
					# We expect to see one of these before we start sending
					# our own heartbeat message to slave.
					# Once we start sending our heartbeat to slave once
					# per second, it should no longer send these linkready
					# messages.  If slave doesn't hear master's heartbeat
					# for around 10 seconds, it sends linkready once per
					# 10 seconds and starts flashing its red LED 4 times
					# with the top green light on.  Red LED stops flashing
					# if we start sending heartbeat again.
					my $senderID = $1;
					my $sign = $2;
					if($debugLevel >= 1) {
						printf(time_now() . ": Slave TWC %02x%02x is ready to link.  Sign: %s\n",
							vec($senderID, 0, 8), vec($senderID, 1, 8),
							hex_str($sign));
					}
					
					if($senderID eq $fakeTWCID) {
						print("Slave TWC reports same ID as master: %02x%02x.  Slave should resolve by changing its ID.\n");
						# I tested sending a linkready to a real master
						# with the same ID as master and instead of
						# master sending back its heartbeat message,
						# it sent 5 copies of its linkready1 and linkready2
						# messages.  Those messages will prompt a real
						# slave to pick a new random value for its ID.
						#
						# We mimic that behavior by setting
						# $initMsgs = 10 to make the idle code at the
						# top of the for(;;) loop send 5 copies of
						# linkready1 and linkready2.
						$initMsgs = 10;
						next;
					}

					# We should always get this linkready message at
					# least once and generally no more than once, so
					# this is a good opportunity to add the slave to
					# our known pool of slave devices.
					new_slave($senderID);
					
					send_heartbeat($senderID);
				}
				elsif($msg =~ /\xc0\xfd\xe0(..)(..)(.......).\xc0\xfe/s) {
					# Handle heartbeat message from slave.
					#
					# These messages come in as a direct response to
					# each heartbeat message from master.  Slave does
					# not send its heartbeat until it gets one from
					# master first.
					# A real master sends heartbeat to a slave around
					# once per second, so we do the same near the top of
					# this for(;;) loop.  Thus, we should receive a
					# heartbeat reply from the slave around once per
					# second as well.
					my $senderID = $1;
					my $receiverID = $2;
					my @statusData = unpack('C*', $3);
					
					if(exists($slaveLastRxTimestamp{$senderID})) {
						$slaveLastRxTimestamp{$senderID} = time;
					}
					else {
						# Normally, a slave only sends us a heartbeat
						# message if we send them ours first, so it's
						# not expected we would hear heartbeat from a
						# slave that's not in our list.
						printf("ERROR: Received heartbeat message from "
								. "slave %02x%02x that we've not met before.\n\n",
								vec($senderID, 0, 8), vec($senderID, 1, 8));
						next;
					}
					
					if($fakeTWCID eq $receiverID) {
						my $actualSlaveAmpsMax = ($statusData[1] << 8) + $statusData[2];
						
						# Allocate this slave a fraction of $totalAmpsMax
						# divided by teh number of slave TWCs on the network.
						my $desiredSlaveAmpsMax = int($totalAmpsMax / @slaveTWCIDs);
						
						if($desiredSlaveAmpsMax < 1) {
							# 0 values aren't allowed by the protocol,
							# but don't worry - Tesla won't try to
							# charge when the limit is under 100 (1A).
							$desiredSlaveAmpsMax = 1;
						}
						
						# See notes in send_heartbeat(), fake slave
						# section for how these numbers work.
						if(
						   (
							  (
							    $statusData[0] == 0x04
							      ||
							    $statusData[0] == 0x08
							  ) 
							    &&
						      $actualSlaveAmpsMax == 0
						    )
						      ||
						    (
						      # Slave is not using the power we want it to,
						      # so set it straight.
						      #punish_slave();
						      $actualSlaveAmpsMax != $desiredSlaveAmpsMax
						        &&
						      $actualSlaveAmpsMax > 0
						    )
						) {
							@masterStatus = (0x05,
							  ($desiredSlaveAmpsMax >> 8) & 0xFF,
							  $desiredSlaveAmpsMax & 0xFF,
							  0x00,0x00,0x00,0x00);
							
							# Test code to start the car at 0.01A and after
							# 60 seconds, increase the power by 0.50A every
							# 10 seconds.
							#if(!defined($testTimer)) {
								#$testTimer = time + 60;
							#}
							#elsif($testTimer < time) {
								#if($totalAmpsMax < 4000) {
									#$totalAmpsMax += 50;
								#}
								#$testTimer = time + 10;
							#}
						}
						else {
							@masterStatus = (0x00,0x00,0x00,0x00,0x00,0x00,0x00);
						}

						if($debugLevel >= 1) {
							my $debugOutput =
								sprintf(": S %02x%02x %02.2f/%02.2fA: "
								. "%02x %02x%02x %02x%02x %02x%02x  "
								. "M: %02x %02x%02x %02x%02x %02x%02x\n",
								vec($senderID, 0, 8), vec($senderID, 1, 8),
								((($statusData[3] << 8) + $statusData[4]) / 100),
								((($statusData[1] << 8) + $statusData[2]) / 100),
								$statusData[0], $statusData[1], $statusData[2],
								$statusData[3], $statusData[4], $statusData[5],
								$statusData[6],
								$masterStatus[0], $masterStatus[1], $masterStatus[2],
								$masterStatus[3], $masterStatus[4], $masterStatus[5],
								$masterStatus[6]);

							# Only output once-per-second heartbeat
							# debug info when it's different from the
							# last output, or if it's been 10 mins
							# since the last output or if $debugLevel
							# is turned up to 11.
							if($debugOutput ne $lastHeartbeatDebugOutput
								|| time - $lastHeartbeatDebugOutputTimestamp > 600
								|| $debugLevel >= 11
							) {
								print(time_now() . $debugOutput);
								$lastHeartbeatDebugOutput = $debugOutput;
								$lastHeartbeatDebugOutputTimestamp = time;
							}
						}
					}
					else {
						# I've tried different $fakeTWCID values to verify a
						# slave will send our $fakeTWCID back to us as
						# $receiverID.  However, I once saw it send 
						# $receiverID = 0000.
						# I'm not sure why it sent 0000 and it only happened
						# once so far, so it could have been corruption in
						# the data or an unusual case.
						if($debugLevel >= 1) {
							printf(time_now() . ": Slave TWC %02x%02x status data: %s sent to unknown TWC id %s.\n\n",
								vec($senderID, 0, 8), vec($senderID, 1, 8),
								hex_ary(@statusData), hex_str($receiverID));
						}
					}
				}
				else {
					print(time_now() . ": ***UNKNOWN MESSAGE from slave: " . hex_str($msg) . "\n");
				}
			}
			else {
				###########################
				# Pretend to be a slave TWC
				
				if($msg =~ /\xc0\xfc\xe1(..)(.)\x00\x00\x00\x00\x00\x00\x00\x00.\xc0\xfe/s) {
					# Handle linkready1 from master.
					# See notes in send_master_linkready1() for details.
					my $senderID = $1;
					my $sign = $2;
					
					# This message seems to always contain seven 00 bytes
					# in its data area.  If we ever get this message with
					# non-00 data we'll print it as an unexpected message.
					
					if($debugLevel >= 5) {
						printf(time_now() . ": Master TWC %02x%02x is cruising the streets.  Sign: %ls\n",
							vec($senderID, 0, 8), vec($senderID, 1, 8),
							hex_str($sign));
					}

					if($senderID eq $fakeTWCID) {
						master_id_conflict();
					}
					
					# Other than picking a new fakeTWCID if ours
					# conflicts with master, it doesn't seem that a real
					# slave will make any sort of direct response when
					# sent a master's linkready1.
				}
				elsif($msg =~ /\xc0\xfb\xe2(..)(.)\x00\x00\x00\x00\x00\x00\x00\x00.\xc0\xfe/s) {
					# Handle linkready2 from master.
					# See notes in send_master_linkready2() for details.
					my $senderID = $1;
					my $sign = $2;
					
					# This message seems to always contain seven 00 bytes
					# in its data area.  If we ever get this message with
					# non-00 data we'll print it as an unexpected message.
					
					if($debugLevel >= 1) {
						printf(time_now() . ": Master TWC %02x%02x wants to hook up.  Sign: %s\n",
							vec($senderID, 0, 8), vec($senderID, 1, 8),
							hex_str($sign));
					}
					
					if($senderID eq $fakeTWCID) {
						master_id_conflict();
					}
					
					# I seem to remember that a slave will respond
					# with an immediate linkready when it sees master's
					# linkready2.  In fact, I think a real slave sends 5
					# copies of linkready about a second apart before
					# returning to sending them once per 10 seconds.
					# I don't bother emulating that since master will see
					# one of our 10-second linkreadys eventually.
					send_slave_linkready();
				}
				elsif($msg =~ /\xc0\xfb\xe0(..)(..)(.......).\xc0\xfe/s) {
					# Handle heartbeat message from a master.
					my $senderID = $1;
					my $receiverID = $2;
					my @statusData = unpack('C*', $3);
					
					if($receiverID ne $fakeTWCID) {
						# This message was intended for another slave.
						# Ignore it.
						if($debugLevel >= 1) {
							printf(time_now() . ": Master %02x%02x sent "
								. "heartbeat message %s to receiver %02x%02x "
								. "that isn't our fake slave.\n",
								vec($senderID, 0, 8), vec($senderID, 1, 8),
								hex_ary(@statusData),
								vec($receiverID, 0, 8), vec($receiverID, 1, 8));
						}
						next;
					}
					
					if($debugLevel >= 1) {
						printf(time_now() . ": Master %02x%02x: %s  Slave: %s\n",
							vec($senderID, 0, 8), vec($senderID, 1, 8),
							hex_ary(@statusData), hex_ary(@slaveStatus));
					}
					
					# A real slave mimics master's status bytes [1]-[2]
					# representing max charger power even if the master
					# sends it a crazy value.
					$slaveStatus[1] = $statusData[1];
					$slaveStatus[2] = $statusData[2];
					
					#if(!defined($testTimer)) {
						#$slaveStatus[0] = 0;
						#$testTimer = time + 2;
					#}
					#elsif($testTimer < time) {
						#$slaveStatus[0]++;
						#if($slaveStatus[0] > 255) {
							#$slaveStatus[0] = 0;
						#}
						#$testTimer = time + 2;
					#}
					
					# Slaves always respond to master's heartbeat by
					# sending theirs back.
					send_heartbeat($senderID);
				}
				elsif($msg =~ /\xc0\xfc\x1d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00.\xc0\xfe/s) {
					# Handle 4-hour idle message
					#
					# I haven't verified this, but TheNoOne reports
					# receiving this message from a Master TWC three
					# times in a row every 4 hours:
					#   c0 fc 1d 00 00 00 00 00 00 00 00 00 00 00 1d c0
					# I suspect his logging was corrupted to strip the
					# final fe byte, unless Tesla changed the protocol to
					# 16 bytes just for this one message.
					# I also suspect this message is only sent when the
					# master doesn't see any other TWCs on the network,
					# so I don't bother to have our fake master send
					# these messages being as there's no point in
					# playing a fake master with no slaves around.
					if($debugLevel >= 1) {
						print("Received 4-hour idle message from Master.\n");
					}
				}
				else {
					print(time_now() . ": ***UNKNOWN MESSAGE from master: " . hex_str($msg) . "\n");
				}
			}
		}
	}
}

close TWC;

sub new_slave
{
	my $newSlaveID = $_[0];
	foreach(@slaveTWCIDs) {
		if($_ eq $newSlaveID) {
			# We already know about this slave.
			return;
		}
	}
	push @slaveTWCIDs, $newSlaveID;
	$slaveLastRxTimestamp{$newSlaveID} = time;
	
	if(@slaveTWCIDs > 3) {
		print("WARNING: More than 3 slave TWCs seen on network.  "
			. "Dropping oldest: " . $slaveTWCIDs[0] . ".\n\n");
		delete_slave($slaveTWCIDs[0]);
	}
}

sub delete_slave
{
	my $deleteSlaveID = $_[0];
	
	# Line from https://stackoverflow.com/questions/17216966/delete-elements-from-array-if-they-contain-some-string
	@slaveTWCIDs = grep !/$deleteSlaveID/, @slaveTWCIDs;
	
	delete $slaveLastRxTimestamp{$deleteSlaveID};
	
}

sub master_id_conflict
{
	# Master's ID matches our ID, which means we must
	# change our ID because master will not.
	vec($fakeTWCID, 0, 8) = int(rand(256));
	vec($fakeTWCID, 1, 8) = int(rand(256));

	# Slaves also seem to change their sign during a conflict.
	vec($slaveSign, 0, 8) = int(rand(256));

	printf("Master's ID matches our fake slave's ID.  "
		. "Picked new random ID %02x%02x with sign %02x\n",
		vec($fakeTWCID, 0, 8), vec($fakeTWCID, 1, 8),
		vec($slaveSign, 0, 8));
}

sub send_msg
{
	my $msg = $_[0];
	my $checksum = vec($msg, 1, 8) + vec($msg, 2, 8) + vec($msg, 3, 8)
				+ vec($msg, 4, 8) + vec($msg, 5, 8) + vec($msg, 6, 8)
				+ vec($msg, 7, 8) + vec($msg, 8, 8) + vec($msg, 9, 8)
				+ vec($msg, 10, 8) + vec($msg, 11, 8) + vec($msg, 12, 8);
	$msg .= chr($checksum & 0xFF);
	
	# The protocol uses c0 to mark the next byte as having special
	# meaning:
	#   c0 fb, c0 fc, and c0 fd mark the start of messages.
	#   c0 fe marks the end of a message.
	# Therefore, c0 can not appear within a message.  They could have
	# just used c0 c0 to mean an actual c0 byte (doubling a special
	# character is commonly used to escape it), but instead some insane
	# person decided that an actual c0 byte would be represented by
	# db dc!
	# Ok, so what about an actual db byte in a message?  Why, it's
	# represented by db dd of course!  Certainly wouldn't want to
	# escape db using db db (by doubling it) because that's just too
	# obvious.  *facepalm*
	# Maybe they had some good reason for this crazy method of escaping
	# special values but it makes no sense to me.
	# I've confirmed fb, fc, fd, and fe are not special values and I
	# hope there aren't others lurking.
	for(my $i = 0; $i < length($msg); $i++) {
		if(vec($msg, $i, 8) == 0xc0) {
			substr($msg, $i, 1, "\xdb\xdc");
			$i++;
		}
		elsif(vec($msg, $i, 8) == 0xdb) {
			substr($msg, $i, 1, "\xdb\xdd");
			$i++;
		}
	}
	
	$msg = "\xc0" . $msg . "\xc0\xfe";
	
	if($debugLevel >= 10) {
		print("Tx@" . time_now() . ": " . hex_str($msg) . "\n");
	}
	syswrite(TWC, $msg, length($msg));
	
	$lastTxTimestamp = time;
}

sub unescape_msg
{
	my ($msg, $msgLen) = @_;
	$msg = substr($msg, 0, $msgLen);
	
	# When you don't have a 120ohm resistor in parallel with the D+ and D-
	# pins, you may see corruption in the data.
	# This explains where terminators should be added:
	#   https://www.ni.com/support/serial/resinfo.htm
	# This explains what happens without terminators:
	#   https://e2e.ti.com/blogs_/b/analogwire/archive/2016/07/28/rs-485-basics-when-termination-is-necessary-and-how-to-do-it-properly
	#
	# I don't understand why, but it seems like lack of termination
	# only corrupts the last byte of a message, and only sometimes.
	# In my system, lack of termination causes messages to periodically
	# end in \xc0\x02\0x00 instead of \xc0\xfe.  This is easy to correct,
	# so I do it here.  I have no idea if other systems will see this
	# exact same pattern of corruption.
	if(
		vec($msg, $msgLen - 3, 8) == 0xc0
		   &&
	     vec($msg, $msgLen - 2, 8) == 0x02
		   &&
	     vec($msg, $msgLen - 1, 8) == 0x00
	) {
		if($debugLevel >= 1) {
			print("Fixed corruption at end of message likely caused by "
			  . "lack of termination.  See notes in source code.\n");
		}
		substr($msg, $msgLen -2, 2, "\xfe");
	}
	
	# See notes in send_msg() for the crazy way certain bytes in messages
	# are escaped.
	# We basically want to change \xdb\xdc into \xc0 and \xdb\xdd
	# into \xdb.  Only scan to one less than the length of the string
	# to avoid running off the end looking at $i+1.
	for(my $i = 0; $i < length($msg) - 1; $i++) {
		if(vec($msg, $i, 8) == 0xdb) {
			if(vec($msg, $i+1, 8) == 0xdc) {
				substr($msg, $i, 2, "\xc0");
			}
			elsif(vec($msg, $i+1, 8) == 0xdd) {
				substr($msg, $i, 2, "\xdb");
			}
			else {
				printf("ERROR: Special character 0xdb in message is "
				  . "followed by unknown value %02x.  "
				  . "Message may be corrupted.\n\n",
				  vec($msg, $i+1, 8));
				  
				# Replace the character with something even though it's
				# probably not the right thing.
				substr($msg, $i, 2, "\xdb");
			}
		}
	}
	
	return $msg;
}


sub send_master_linkready1
{
	# When master is powered on or reset, it sends 5 to 7 copies
	# of this linkready1 message followed by 5 copies of linkready2
	# I've never seen more or less than 5 of linkready2).
	#
	# This linkready1 message advertises master's ID to other slaves on
	# the network.
	# If a slave happend to have the same id as master, it will pick a
	# new random ID.  Other than that, slaves don't seem to respond to
	# linkready1.
	
	# linkready1 and linkready2 are identical except fc e1 is replaced
	# by fb e2 in bytes 2-3.  Both messages will cause a slave to pick
	# a new id if the slave's id conflicts with master.  Only linkready2
	# will cause a slave to respond immediately with its own linkready
	# message (though I'm not absolutely sure about that).
	# If a slave stops sending heartbeats for awhile, master may send
	# a series of linkready1 and linkready2 messages in seemingly random
	# order, which means they don't indicate any sort of startup state.
	
	# linkready1 is not sent again after boot/reset unless a slave sends
	# its ready_to_link message.
	# At that point, linkready1 message may start sending every 1-5
	# seconds, or it may not be sent at all.
	# Behaviors I've seen:
	#   Not sent at all as long as slave keeps responding to
	#   heartbeat messages right from the start.
	#   If slave stops responding, then re-appears, linkready1
	#   gets sent frequently.
	
	# One other possible purpose of linkready1 and/or linkready2
	# is to trigger an error condition if two TWCs on the network
	# transmit those messages.  That means two TWCs have rotary
	# switches setting them to master mode and I believe they will
	# both flash their red LED 4 times with top green light on if
	# that happens.
	
	# Also note that linkready1 starts with fc e1 which is similar to
	# the fc d1 message that masters send out every 4 hours when idle.
	# Oddly, the fc d1 message contains all zeros instead of the master's
	# id, so it seems pointless.

	# I don't understand the purpose of having both linkready1 and
	# linkready2 but it doesn't seem to matter.  If anyone figures
	# it out, contact http://support.dracoventions.com because I'm
	# curious.
	send_msg("\xFC\xE1$fakeTWCID$masterSign\x00\x00\x00\x00\x00\x00\x00\x00");
}

sub send_master_linkready2
{
	# This linkready2 message is also sent 5 times when master is
	# booted/reset and then not sent again if no other TWCs are heard
	# from on the network.
	# If the master has ever seen a slave on the network, linkready2 is
	# sent at long intervals.
	# I need to double check this, but I've seen some evidence
	# that a slave will send 5 copies of its link ready
	# message, once per second, in response to this master's linkready2.
	#
	# It may be that this linkready2 message that sends fb e2 and the
	# master heartbeat that sends fb e0
	# message are really the same, (same fb byte which I
	# think is message type) except the e0 version includes
	# the TWC ID of the slave the message is intended for whereas
	# the e2 version has no recipient TWC ID and is asking all slaves
	# on the network to report immediately.  The problem with that
	# theory is if all slaves try to report immediately, all their
	# responses will corrupt eachother.  Could the random slave id
	# or slave sign contain a timeslot that prevents that?
	#
	# Once master starts sending heartbeat messages to a slave, it
	# no longer sends the global linkready2 message (or if it does,
	# they're quite rare so I haven't seen them).
	send_msg("\xFB\xE2$fakeTWCID$masterSign\x00\x00\x00\x00\x00\x00\x00\x00");
}

sub send_slave_linkready
{
	# I accidentally changed \x1f\x40 to \x2e\x69 at one point,
	# which makes the master TWC immediately start blinking
	# its red LED 6 times with top green LED on.  Manual says
	# this means "The networked Wall Connectors have different
	# maximum current capabilities".  Therefore, I theorize	0x1f40
	# (8000 in base 10) refers to this being a max 80.00Amp charger
	# model.
	send_msg("\xFD\xE2$fakeTWCID$slaveSign\x1F\x40\x00\x00\x00\x00\x00\x00");
}

sub send_heartbeat
{
	my $senderID = $_[0];
	
	if($fakeMaster) {
		# Send master heartbeat
		#
		# Heartbeat includes 7 bytes of data we store in @masterStatus.
		# Meaning of 7 bytes:
		#
		# Byte 1 values I've seen with guesses at meaning:
		#   00 Idle/all is well
		#   02 Error (I've only seen this when a master TWC is blinking its red LED)
		#   05 Tell slave charger to limit power
		# I haven't spent much time trying to discover if other values
		# are possible.  00 and 05 are enough to fully control a slave
		# TWC's power output.
		#
		# Byte 2-3 is the max current a slave TWC can charge at.
		# For example, if bytes 2-3 are 0f a0, combine them as 0x0fa0 hex
		# which is 4000 in base 10.  Move the decimal point two places
		# left and you get 40.00Amps max.
		#
		# Byte 4: Usually 00 but became 01 when a master TWC was plugged
		# in to a car.
		#
		# Byte 5-7 are always 00 and may be unused.
		#
		# Example 7-byte data that real masters have sent:
		#   00 00 00 00 00 00 00  (Idle)
		#   02 04 00 00 00 00 00  (Error.  04 is probably an error code because interpretting 04 00 as an amp value gets us an odd 10.24A)
		#   05 0f a0 00 00 00 00  (Master telling slave to limit power to 0f a0 (40.00A))
		#   05 07 d0 01 00 00 00  (Master plugged in to a car and presumably telling slaves to limit power to 07 d0 (20.00A).  01 byte might indicate master is plugged in?  Master would not charge its car because I didn't have the fake slave issue the correct response.)

		send_msg("\xFB\xE0$fakeTWCID$senderID" 
				 . pack('C*', @masterStatus));
	}
	else {
		# Send slave heartbeat
		#
		# Heartbeat includes 7 bytes of data we store in @slaveStatus.
		# Meaning of 7 bytes:
		#
		# Byte 1 values I've seen with guesses at meaning:
		#   00 Ready (may or may not be plugged in)
		#   01 Plugged in, charging
		#   02 Lost communication with master (usually see this status briefly if I stop fake master script for awhile, then start it)
		#   03 Plugged in, do not charge (I've seen this state briefly when plug is first inserted, and I've seen this state remain indefinitely after pressing stop charge on car's screen.  It may also remain indefinitely if TWCManager script is stopped for too long while car is charging even after TWCManager is restarted.  In that case, car will not charge even when start charge on screen is pressed - only re-plugging in charge cable fixes it.)
		#   04 Plugged in, ready to charge (I've seen this state even when car is set to charge at a future time)
		#   05 Only seen it hit this state for 1 second at a time and it can seemingly happen during any other state.  Maybe it means wait, I'm busy?  Communicating with car?  When Master sends 05, slave takes it as permission to continue, but I can't say for sure the value means the same thing in slave vs master use.
		#   08 Lost communication with master while plugged in (Saw this consistently each time I stopped my fake master script with car scheduled to charge, plugged in, charge port blue.  If the car is actually charging and you stop TWCManager, after 20-30 seconds the charbe port turns solid red, steering wheel display says "charge cable fault", and main screen says "check charger power".  When TWCManager is started, it sees this 08 status again.  If we start TWCManager and send the slave a new max power value, 08 becomes 00 and car starts charging again.)
		#
		# Byte 2-3 is the max current available as provided by bytes 2-3
		# in our fake master status.
		# For example, if bytes 2-3 are 0f a0, combine them as 0x0fa0 hex
		# which is 4000 in base 10.  Move the decimal point two places
		# left and you get 40.00Amps max.
		# Note that once bytes 2-3 are greater than 0, Byte 1 changes
		# from 04 to 01 or 00 during charging.
		#
		# Byte 4-5 represents the power being drawn by the charger.
		# When a car is charging at 18A you may see a value like 07 28
		# which is 0x728 hex or 1832 in base 10.  Move the decimal point
		# two places left and you see the charger is using 18.32A.
		# When unplugged, my charger reports 00 19 (0.25A) but very
		# occasionally changes to 00 11 (0.17A) or 00 21 (0.33A).
		# Your charger may differ in its exact power use.
		#
		# Byte 6-7 are always 00 00 from what I've seen and could be
		# reserved for future use or may be used in a situation I've not
		# observed.
		
		###############################
		# How was the above determined?
		#
		# An unplugged slave sends a status like this:
		#   00 00 00 00 19 00 00
		#
		# A real master always sends all 00 status data to a slave 
		# reporting the above status.  $slaveStatus[0] is the main 
		# driver of how master responds, but whether $slaveStatus[1] 
		# and [2] have 00 or non-00 values also matters.
		#
		# I did a test with fake slave sending $slaveStatus[0]
		# values from 00 to ff along with $slaveStatus[1-2]
		# of 00 and whatever value Master last responded
		# with.  I found:
		#   Slave sends:     04 00 00 00 19 00 00
		#   Master responds: 05 12 c0 00 00 00 00
		#
		#   Slave sends:     04 12 c0 00 19 00 00
		#   Master responds: 00 00 00 00 00 00 00
		#
		#   Slave sends:     08 00 00 00 19 00 00
		#   Master responds: 08 12 c0 00 00 00 00
		#
		#   Slave sends:     08 12 c0 00 19 00 00
		#   Master responds: 00 00 00 00 00 00 00
		#
		# In other words, master always sends all 00 unless slave 
		# sends $slaveStatus[0] 04 or 08 with $slaveStatus[1-2] both 
		# 00.
		# 
		# I interpret all this to mean that when slave sends 
		# $slaveStatus[1-2] both 00, it's requesting a max power from 
		# master.  Master responds by telling the slave how much power 
		# it can use. Once the slave is saying how much max power it's 
		# going to use ($slaveStatus[1-2] = 12 c0 = 32.00A), master 
		# indicates that's fine by sending 00 00.
		#
		# However, if the master wants to set a lower limit on the 
		# slave, all it has to do is send any $statusData[1-2] value 
		# greater than 00 00 at any time and slave will respond by
		# setting its $slaveStatus[1-2] to the same value.
		#					  
		# I thought slave might be able to negotiate a lower value if,
		# say, the car reported 40A was its max capability or if the slave
		# itself could only handle 80A, but the slave dutifully responds
		# with the same value master sends it even if that value is
		# an insane 655.35A.  I tested these values on my car which has
		# a 40A limit when AC charging:
		#   0f aa (40.10A)
		#   1f 40 (80.00A)
		#   1f 41 (80.01A)
		#   ff ff (655.35A)
		
		send_msg("\xFD\xE0$fakeTWCID$senderID"
				 . pack('C*', @slaveStatus));
	}
}

		
sub time_now
{
	return strftime("%H:%M:%S", localtime);
}

sub hex_ary
{
	my $result = '';
	
	foreach(@_){
		$result .= sprintf("%02x ", $_);;
	}
	
	return substr($result, 0, length($result) - 1);
}

sub hex_str
{
	my $buf = $_[0];
	my $result = '';
	
	foreach(unpack('C*', $buf)) { # unpack is supposedly more efficient than split(//, $buf)).  Unpack produces an array of integers instead of an array of single-character strings.
		$result .= sprintf("%02x ", $_);;
	}
	
	return substr($result, 0, length($result) - 1);
}

sub punish_slave
{
	# Sadly, this sub is unused.
	print "Slave punished.";
}
