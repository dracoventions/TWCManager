#!/usr/bin/perl

################################################################################
# Perl code and TWC protocol reverse engineering by Chris Dragon.
#
# Additional logs and hints provided by Teslamotorsclub.com users:
#   TheNoOne, IanAmber, and twc.
# Thank you!
#
# For support and information, please read through this thread:
# https://teslamotorsclub.com/tmc/threads/new-wall-connector-load-sharing-protocol.72830
#
# Report bugs at https://github.com/cdragon/TWCManager/issues
#
# A Python project based on TWCManager is available here:
# https://github.com/wido/smarthpwc
#
# This software is released under the "Unlicense" model: http://unlicense.org
# This means source code and TWC protocol knowledge are released to the general
# public free for personal or commercial use. I hope the knowledge will be used
# to increase the use of green energy sources by controlling the time and power
# level of car charging.
#
# WARNING:
# Misuse of the protocol described in this software can direct a Tesla Wall
# Charger to supply more current to a car than the charger wiring was designed
# for. This will trip a circuit breaker or may start a fire in the unlikely
# event that the circuit breaker fails.
# This software was not written or designed with the benefit of information from
# Tesla and there is always a small possibility that some unforeseen aspect of
# its operation could damage a Tesla vehicle or a Tesla Wall Charger. All
# efforts have been made to avoid such damage and this software is in active use
# on the author's own vehicle and TWC.
#
# In short, USE THIS SOFTWARE AT YOUR OWN RISK.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# For more information, please visit http://unlicense.org

################################################################################
# What's TWCManager good for?
#
# This script (TWCManager) pretends to be a Tesla Wall Charger (TWC) set to
# master mode. When wired to the IN or OUT pins of real TWC units set to slave
# mode (rotary switch position F), TWCManager can tell them to limit car
# charging to any whole amp value between 5A and the max rating of the charger.
# Charging can also be stopped so the car goes to sleep.
#
# This level of control is useful for having TWCManager track the real-time
# availability of green energy sources and direct the slave TWCs to use near the
# exact amount of energy available. This saves energy compared to sending the
# green energy off to a battery for later car charging or off to the grid where
# some of it is lost in transmission.
#
# TWCManager can also be set up to only allow charging during certain hours,
# stop charging if a grid overload or "save power day" is detected, reduce
# charging on one TWC when a "more important" one is plugged in, or whatever
# else you might want to do.
#
# One thing TWCManager does not have direct access to is the battery charge
# percentage of each plugged-in car. There are hints on forums that some TWCs
# do report battery state, but we have yet to see a TWC send such a message.
# It's possible the feature exists in TWCs with newer firmware.
# This is unfortunate, but if you own a Tesla vehicle being charged, people have
# figured out how to get its charge state by contacting Tesla's servers using
# the same password you use in the Tesla phone app. Be very careful not to
# expose that password because it allows unlocking and starting the car.

################################################################################
# Overview of protocol TWCs use to load share
#
# A TWC set to slave mode (rotary switch position F) sends a linkready message
# every 10 seconds.
# The message contains a unique 4-byte id that identifies that particular slave
# as the sender of the message.
#
# A TWC set to master mode sees a linkready message. In response, it sends a
# heartbeat message containing the slave's 4-byte id as the intended recipient
# of the message.
# The master's 4-byte id is included as the sender of the message.
#
# Slave sees a heartbeat message from master directed to its unique 4-byte id
# and responds with its own heartbeat message containing the master's 4-byte id
# as the intended recipient of the message.
# The slave's 4-byte id is included as the sender of the message.
#
# Master sends a heartbeat to a slave around once per second and expects a
# response heartbeat from the slave.
# Slaves do not send heartbeats without seeing one from a master first. If
# heartbeats stop coming from master, slave resumes sending linkready every 10
# seconds.
# If slaves stop replying to heartbeats from master, master's behavior is more
# complex but it generally keeps trying to contact the slave at less frequent
# intervals and I think it gives up eventually.
#
# Heartbeat messages contain a 7-byte data block used to negotiate the amount of
# power available to each slave and to the master.
# The first byte is a status indicating things like is TWC plugged in, does it
# want power, is there an error, etc.
# Next two bytes indicate the amount of power requested or the amount allowed in
# 0.01 amp increments.
# Next two bytes indicate the amount of power being used to charge the car, also in
# 0.01 amp increments.
# Last two bytes seem to be unused and always contain a value of 0.


use Fcntl;
use POSIX;
use Time::HiRes qw(usleep nanosleep);
use IPC::SysV qw(ftok IPC_PRIVATE IPC_RMID IPC_CREAT MSG_NOERROR IPC_NOWAIT);
use warnings;
use strict;


# This makes print output to screen immediately instead of waiting till
# the end of the line is reached.
$| = 1;


##########################
#
# Configuration parameters
#

# Most users will have only one ttyUSB adapter plugged in and the default value
# of '/dev/ttyUSB0' below will work. If not, run 'dmesg |grep ttyUSB' on the
# command line to find your rs485 adapter and put its ttyUSB# value in the
# parameter below.
# If you're using a non-USB adapter like an RS485 shield, the value may need to
# be something like '/dev/serial0'.
my $rs485Adapter = '/dev/ttyUSB0';

# Set $wiringMaxAmpsAllTWCs to the maximum number of amps your charger wiring
# can handle. I default this to a low 6A which should be safe with the minimum
# standard of wiring in the areas of the world that I'm aware of.
# Most U.S. chargers will be wired to handle at least 40A and sometimes 80A,
# whereas EU chargers will handle at most 32A (using 3 AC lines instead of 2 so
# the total power they deliver is similar).
# Setting $wiringMaxAmpsAllTWCs too high will trip the circuit breaker on your
# charger at best or START A FIRE if the circuit breaker malfunctions.
# Keep in mind that circuit breakers are designed to handle only 80% of their
# max power rating continuously, so if your charger has a 50A circuit breaker,
# put 50 * 0.8 = 40 here.
# 40 amp breaker * 0.8 = 32 here.
# 30 amp breaker * 0.8 = 24 here.
# 100 amp breaker * 0.8 = 80 here.
# IF YOU'RE NOT SURE WHAT TO PUT HERE, ASK THE ELECTRICIAN WHO INSTALLED YOUR
# CHARGER.
my $wiringMaxAmpsAllTWCs = 6;

# If all your chargers share a single circuit breaker, set $wiringMaxAmpsPerTWC
# to the same value as $wiringMaxAmpsAllTWCs.
# Rarely, each TWC will be wired to its own circuit breaker. If you're
# absolutely sure your chargers each have a separate breaker, put the value of
# that breaker * 0.8 here, and put the sum of all breakers * 0.8 as the value of
# $wiringMaxAmpsAllTWCs.
# For example, if you have two TWCs each with a 50A breaker, set
# $wiringMaxAmpsPerTWC = 50 * 0.8 = 40 and $wiringMaxAmpsAllTWCs = 40 + 40 = 80.
my $wiringMaxAmpsPerTWC = 6;

# Choose how much debugging info to output.
# 0 is no output other than errors.
# 1 is just the most useful info.
# 10 is all info.
# 11 is more than all info.
my $debugLevel = 1;

# Normally we fake being a TWC Master. Set $fakeMaster = 0 to fake being a TWC
# Slave instead (only useful for debugging and protocol reversing).
my $fakeMaster = 1;

# TWC's rs485 port runs at 9600 baud which has been verified with an
# oscilloscope. Don't change this unless something changes in future hardware.
my $baud = 9600;

# All TWCs ship with a random two-byte ID. We default to using 0x7777 as our
# fake TWC ID. There is a 1 in 64535 chance that this ID will match each real
# TWC on the network, in which case you should pick a different random id below.
# This isn't really too important because even if this ID matches another TWC on
# the network, that TWC will pick its own new random ID as soon as it sees ours
# conflicts.
my $fakeTWCID = "\x77\x77";

# TWCs send a seemingly-random byte after their 2-byte TWC id in a number of
# messages. I call this byte their "Sign" for lack of a better term. The byte
# never changes unless the TWC is reset or power cycled. We use hard-coded
# values for now because I don't know if there are any rules to what values can
# be chosen. I picked 77 because it's easy to recognize when looking at logs.
# These shouldn't need to be changed.
my $masterSign = "\x77";
my $slaveSign = "\x77";


#
# End configuration parameters
#
##############################


my ($data, $dataLen);
my ($msg, $msgLen) = ('', 0);

# Set options to make the $rs485Adapter work correctly, then open it for reading
# and writing.
# 'raw' and '-echo' options are necessary with the FTDI chipset to avoid corrupt
# output or missing data.
system("stty -F $rs485Adapter raw -echo $baud cs8 -cstopb -parenb");
sysopen(TWC, "$rs485Adapter", O_RDWR | O_NONBLOCK) or die "Can't open $rs485Adapter";
binmode TWC, ":raw";

my @slaveHeartbeatData = (0x04,0x00,0x00,0x00,0x19,0x00,0x00);
my $numInitMsgsToSend = 10;
my $msgRxCount = 0;
my $timeLastTx = 0;

my %slaveTWCs;
my @slaveTWCRoundRobin = ();
my $idxSlaveToSendNextHeartbeat = 0;

my $maxAmpsToDivideAmongSlaves = 0;
my $scheduledAmpsMax = 0;
my $scheduledAmpsStartHour = -1;
my $scheduledAmpsEndHour = -1;

my $spikeAmpsToCancel6ALimit = 16;
my $timeLastGreenEnergyCheck = 0;
my $hourResumeTrackGreenEnergy = -1;

# __FILE__ contains the path to the running script. Replace the script name with
# TWCManagerSettings.txt. This gives us a path that will always locate
# TWCManagerSettings.txt in the same directory as the script even when pwd does
# not match the script directory.
my $settingsFileName = __FILE__ =~ s|/[^/]+$|/TWCManagerSettings.txt|r;
my $nonScheduledAmpsMax = -1;
my $timeLastHeartbeatDebugOutput = 0;

my $webMsgPacked = '';
my $webMsgMaxSize = 300;
my $webMsgResult;

load_settings();

################################################################################
# Create an IPC (Interprocess Communication) message queue that we can
# periodically check to respond to queries from the TWCManager web interface.
#
# These messages will contain commands like "start charging at 10A" or may ask
# for information like "how many amps is the solar array putting out".
#
# The message queue is identified by a numeric key. This script and the web
# interface must both use the same key. The "ftok" function facilitates creating
# such a key based on a shared piece of information that is not likely to
# conflict with keys chosen by any other process in the system.
#
# ftok reads the inode number of the file or directory pointed to by its first
# parameter. This file or dir must already exist and the permissions on it don't
# seem to matter. The inode of a particular file or dir is fairly unique but
# doesn't change often so it makes a decent choice for a key.  We use the parent
# directory of the TWCManager script.
#
# The second parameter to ftok is a single byte that adds some additional
# uniqueness and lets you create multiple queues linked to the file or dir in
# the first param. We use 'T' for Tesla.
#
# If you can't get this to work, you can also set $key = <some arbitrary number>
# and in the web interface, use the same arbitrary number. While that could
# conflict with another process, it's very unlikely to.
my $webIPCkey = ftok(__FILE__ =~ s|/[^/]+$|/|r, ord('T'));

# Use the key to create a message queue with read/write access for all users.
my $webIPCqueue = msgget($webIPCkey, IPC_CREAT | S_IRUSR | S_IWUSR | S_IRGRP | S_IWGRP | S_IROTH | S_IWOTH);
if(! defined $webIPCqueue) {
    die("ERROR: Can't create Interprocess Communication message queue to communicate with web interface.\n");
};

# After the IPC message queue is created, if you type 'sudo ipcs -q' on the
# command like, you should see something like:
# ------ Message Queues --------
# key        msqid      owner      perms      used-bytes   messages
# 0x5402ed16 491520     pi         666        0            0
#
# Notice that we've created the only IPC message queue in the system. Apparently
# default software on the pi doesn't use IPC or if it does, it creates and
# deletes its message queues quickly.
#
# If you want to get rid of all queues because you created extras accidentally,
# reboot or type 'sudo ipcrm -a msg'.  Don't get rid of all queues if you see
# ones you didn't create or you may crash another process.
# Find more details in IPC here:
# http://www.onlamp.com/pub/a/php/2004/05/13/shared_memory.html
################################################################################


printf("TWC Manager starting as fake %s with id %02x%02x and sign %02x\n\n",
    ($fakeMaster ? "Master" : "Slave"),
    vec($fakeTWCID, 0, 8), vec($fakeTWCID, 1, 8),
    vec($slaveSign, 0, 8));


for(;;) {
    # In this area, we always send a linkready message when we first start.
    # Whenever there is no data available from other TWCs to respond to, we'll
    # loop back to this point to send another linkready or heartbeat message.
    # By only sending our periodic messages when no incoming message data is
    # available, we reduce the chance that we will start transmitting a message
    # in the middle of an incoming message, which would corrupt both messages.

    # Add a small sleep to prevent pegging pi's CPU at 100% which slows the UI
    # (though even with the sleep the UI gets somewhat slow).
    # Lower CPU also means less power user and less waste heat.
    usleep(500);

    if($fakeMaster) {
        # A real master sends 5 copies of linkready1 and linkready2 whenever it
        # starts up, which we do here.
        # It doesn't seem to matter if we send these once per second or once per
        # 100ms so I do once per 100ms to get them over with.
        if($numInitMsgsToSend > 5) {
            send_master_linkready1();
            usleep(100); # give slave time to respond
            $numInitMsgsToSend--;
        }
        elsif($numInitMsgsToSend > 0) {
            send_master_linkready2();
            usleep(100); # give slave time to respond
            $numInitMsgsToSend--;
        }
        else {
            # After finishing the 5 startup linkready1 and linkready2 messages,
            # master will send a heartbeat message to every slave it's received
            # a linkready message from. Do that here.
            if(time - $timeLastTx > 0) {
                # It's been about a second since our last heartbeat.
                if(@slaveTWCRoundRobin > 0) {
                    my $slaveTWC = $slaveTWCRoundRobin[$idxSlaveToSendNextHeartbeat];
                    if(time - $slaveTWC->{timeLastRx} > 26) {
                        # A real master stops sending heartbeats to a slave that
                        # hasn't responded for ~26 seconds. It may still send
                        # the slave a heartbeat every once in awhile but we're
                        # just going to scratch the slave from our little black
                        # book and add them again if they ever send us a
                        # linkready.
                        printf("WARNING: We haven't heard from slave "
                            . "%02x%02x for over 26 seconds.  "
                            . "Stop sending them heartbeat messages.\n\n",
                            vec($slaveTWC->{ID}, 0, 8), vec($slaveTWC->{ID}, 1, 8));
                        delete_slave($slaveTWC->{ID});
                    }
                    else {
                        $slaveTWC->send_master_heartbeat();
                    }

                    $idxSlaveToSendNextHeartbeat++;
                    if($idxSlaveToSendNextHeartbeat >= @slaveTWCRoundRobin) {
                        $idxSlaveToSendNextHeartbeat = 0;
                    }
                    usleep(100); # give slave time to respond
                }
            }

            if($nonScheduledAmpsMax > -1) {
                $maxAmpsToDivideAmongSlaves = $nonScheduledAmpsMax;
            }
            elsif(time - $timeLastGreenEnergyCheck > 60) {
                my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) =
                                                localtime(time);
                # Don't bother to check solar generation before 6am or after
                # 8pm. Sunrise in most U.S. areas varies from a little before
                # 6am in Jun to almost 7:30am in Nov before the clocks get set
                # back an hour. Sunset can be ~4:30pm to just after 8pm.
                if($hour < 6 || $hour >= 20) {
                    $maxAmpsToDivideAmongSlaves = 0;
                }
                else {
                    # I check my solar panel generation using an API exposed by
                    # The Energy Detective (TED). It's a piece of hardware
                    # available at http://www. theenergydetective.com/ You may
                    # also be able to find a way to query a solar system on the
                    # roof using an API provided by your solar installer. Most
                    # of those systems only update the amount of power the
                    # system is producing every 15 minutes at most, though
                    # that's fine for tweaking your car charging.
                    #
                    # In the worst case, you could skip finding realtime green
                    # energy data and simply direct the car to charge at certain
                    # rates at certain times of day that typically have certain
                    # levels of solar or wind generation. To do so, use the
                    # $hour and $min variables above.
                    #
                    # The curl command used below can be used to communicate
                    # with almost any web API, even ones that require POST
                    # values or authentication. -s option prevents curl from
                    # displaying download stats. -m 4 prevents the whole
                    # operation from taking over 4 seconds. If your service
                    # regularly takes a long time to respond, you'll have to
                    # query it in a background process and have the process
                    # update a file that you check here. If we delay over 9ish
                    # seconds here, slave TWCs will decide we've disappeared and
                    # stop charging or maybe it's more like 20-30 seconds - I
                    # didn't test carefully).
                    my $greenEnergyData = `curl -s -m 4 "http://127.0.0.1/history/export.csv?T=1&D=0&M=1&C=1"`;

                    # In my case, $greenEnergyData will contain something like
                    # this:
                    #   MTU, Time, Power, Cost, Voltage
                    #   Solar,11/11/2017 14:20:43,-2.957,-0.29,124.3
                    # The only part we care about is -2.957 which is negative
                    # kWh currently being generated.
                    # When 0kWh is generated, the negative disappears so we make
                    # it optional.
                    if($greenEnergyData =~ m~^Solar,[^,]+,-?([^, ]+),~m) {
                        my $solarWh = int($1 * 1000);

                        # Watts = Volts * Amps
                        # Car charges at 240 volts in the U.S. so we figure out
                        # how many amps * 240 = $solarWh and limit the car to
                        # that many amps.
                        $maxAmpsToDivideAmongSlaves = $solarWh / 240;

                        printf("%s: Solar generating %dWh so limit car charging to %.2fA.\n",
                            time_now(), $solarWh, $maxAmpsToDivideAmongSlaves);
                    }
                    else {
                        print(time_now() . " ERROR: Can't determine current solar generation from:\n$greenEnergyData$\n\n");
                    }
                }
                $timeLastGreenEnergyCheck = time;
            }
        }
    }
    else {
        # As long as a slave is running, it sends link ready messages every 10
        # seconds. They trigger any master on the network to handshake with the
        # slave and the master then sends a status update from the slave every
        # 1-3 seconds. Master's status updates trigger the slave to send back
        # its own status update.
        # As long as master has sent a status update within the last 10 seconds,
        # slaves don't send link ready.
        # I've also verified that masters don't care if we stop sending link
        # ready as long as we send status updates in response to master's status
        # updates.
        if(time - $timeLastTx >= 10) {
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


    ############################################################################
    # See if there's any message from the web interface.
    # If the message is longer than $msgMaxSize, MSG_NOERROR tells it to return
    # what it can of the message and discard the rest.
    # When no message is available, IPC_NOWAIT tells msgrcv to return $msgResult
    # = 0 and $! = 42 with description 'No message of desired type'.
    # If there is an actual error, $webMsgResult will be -1.
    # On success, $webMsgResult is the length of $webMsgPacked.
    $webMsgResult = msgrcv($webIPCqueue, $webMsgPacked, $webMsgMaxSize, 2, MSG_NOERROR | IPC_NOWAIT );
    if($webMsgResult < 1 && int($!) != 42) {
        print(time_now() . ": Error " . int($!) . ": $! with msgrcv result $webMsgResult\n");
    }
    elsif($webMsgResult > 0) {
        my ($webMsgType, $webMsgTime, $webMsgID, $webMsg) = unpack("lLSa*", $webMsgPacked);
        if($debugLevel >= 1) {
            print time_now() . ": Web query: '" . $webMsg . "', id " . $webMsgID
                             . ", time " . $webMsgTime . ", type " . $webMsgType
                             . ", length " . $webMsgResult . "\n";
        }

        my $webResponseMsg = '';
        if($webMsg eq 'getStatus') {
            $webResponseMsg =
                sprintf("%.2f", $maxAmpsToDivideAmongSlaves)
                . '`' . $nonScheduledAmpsMax
                . '`' . $scheduledAmpsMax
                . '`' . sprintf("%02d:%02d",
                                floor($scheduledAmpsStartHour),
                                floor(($scheduledAmpsStartHour % 1) * 60))
                . '`' . sprintf("%02d:%02d",
                                floor($scheduledAmpsEndHour),
                                floor(($scheduledAmpsEndHour % 1) * 60))
                . '`' . sprintf("%02d:%02d",
                                floor($hourResumeTrackGreenEnergy),
                                floor(($hourResumeTrackGreenEnergy % 1) * 60))
                . '`' . @slaveTWCRoundRobin;
            for(my $i = 0; $i < @slaveTWCRoundRobin; $i++) {
                $webResponseMsg .= '`' . sprintf("%02X%02X",
                                           vec($slaveTWCRoundRobin[$i]->{ID}, 0, 8),
                                           vec($slaveTWCRoundRobin[$i]->{ID}, 1, 8))
                    . '~' . $slaveTWCRoundRobin[$i]->{maxAmps}
                    . '~' . sprintf("%.2f", $slaveTWCRoundRobin[$i]->{reportedAmpsActual})
                    . '~' . $slaveTWCRoundRobin[$i]->{reportedAmpsMax}
                    . '~' . $slaveTWCRoundRobin[$i]->{reportedState};
            }
        }
        elsif($webMsg =~ m/setNonScheduledAmps=([-0-9]+)/) {
            $nonScheduledAmpsMax = $1;

            # Save $nonScheduledAmpsMax to SD card so the setting isn't lost on
            # power failure or script restart.
            save_settings();

            # $nonScheduledAmpsMax = -1 means track green energy source.  If given
            # any other value, set $maxAmpsToDivideAmongSlaves to that value.
            if($nonScheduledAmpsMax > -1) {
                $maxAmpsToDivideAmongSlaves = $nonScheduledAmpsMax;
            }
        }
        elsif($webMsg =~ m/setScheduledAmps=([-0-9]+)\nstartTime=([-0-9]+):([0-9]+)\nendTime=([-0-9]+):([0-9]+)/m) {
            $scheduledAmpsMax = $1;
            $scheduledAmpsStartHour = $2 + ($3 / 60);
            $scheduledAmpsEndHour = $4 + ($5 / 60);
            save_settings();
        }
        elsif($webMsg =~ m/setResumeTrackGreenEnergyTime=([-0-9]+):([0-9]+)/m) {
            $hourResumeTrackGreenEnergy = $1 + ($2 / 60);
            save_settings();
        }

        if($webResponseMsg ne '') {
            if($debugLevel >= 10) {
                print(time_now() . ": Web query response: '$webResponseMsg'\n");
            }

            # In this case, IPC_NOWAIT prevents blocking if the message queue is too
            # full for our message to fit.  Instead, an error is returned.
            if(!msgsnd($webIPCqueue, pack("lLSa*", 1, $webMsgTime, $webMsgID,
                       $webResponseMsg), IPC_NOWAIT)
            ) {
                print(time_now() . ": Error " . int($!) . ": $! trying to send response to web interface.\n");
            }
        }
    }


    ############################################################################
    # See if there's an incoming message on the RS485 interface.
    for(;;) {
        $dataLen = sysread(TWC, $data, 1);
        if(!defined($dataLen) && $!{EAGAIN}) {
            if($msgLen == 0) {
                # No message data waiting and we haven't received the start of a
                # new message yet. Break out of inner for(;;) to continue at top
                # of outer for(;;) loop where we may decide to send a periodic
                # message.
                last;
            }
            else {
                # No message data waiting but we've received a partial message
                # that we should wait to finish receiving.
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
            # We expect to find these non-c0 bytes between messages, so we don't
            # print any warning at standard debug levels.
            if($debugLevel >= 11) {
                printf("Ignoring byte %02x between messages.\n", ord($data));
            }
            next;
        }
        elsif($msgLen > 0 && $msgLen < 15 && ord($data) == 0xc0) {
            # If you see this when the program is first started, it means we
            # started listening in the middle of the TWC sending a message so we
            # didn't see the whole message and must discard it. That's
            # unavoidable.
            # If you see this any other time, it means there was some corruption
            # in what we received. It's normal for that to happen every once in
            # awhile but there may be a problem such as incorrect termination
            # or bias resistors on the rs485 wiring if you see it frequently.
            if($debugLevel >= 10) {
                printf("Found end of message before full-length message received.  Discard and wait for new message.\n", ord($data));
            }
            vec($msg, 0, 8) = ord($data);
            $msgLen = 1;
            next;
        }

        vec($msg, $msgLen, 8) = ord($data);
        $msgLen++;

        # Messages are properly 17 bytes long and end with \xc0\xfe. However,
        # when the network lacks termination and bias resistors, the last byte
        # (\xfe) may be corrupted or even missing, and you may receive
        # additional garbage bytes between messages.
        #
        # TWCs seem to account for corruption at the end and between messages by
        # simply ignoring anything after the final \xc0 in a message, so we use
        # the same tactic. If c0 happens to be within the corrupt noise between
        # messages, we ignore it by starting a new message whenever we see a c0
        # before 15 or more bytes are received.
        #
        # Uncorrupted messages can be over 17 bytes long when special values are
        # "escaped" as two bytes. See notes in send_msg.
        #
        # To prevent most noise between messages, add a 120ohm "termination"
        # resistor in parallel to the D+ and D- lines. Also add a 680ohm "bias"
        # resistor between the D+ line and +5V and a second 680ohm "bias"
        # resistor between the D- line and ground. See here for more
        # information:
        #   https://www.ni.com/support/serial/resinfo.htm
        #   http://www.ti.com/lit/an/slyt514/slyt514.pdf
        # This explains what happens without "termination" resistors:
        #   https://e2e.ti.com/blogs_/b/analogwire/archive/2016/07/28/rs-485-basics-when-termination-is-necessary-and-how-to-do-it-properly
        if($msgLen >= 16 && ord($data) == 0xc0) {
            $msg = unescape_msg($msg, $msgLen);

            # Set msgLen = 0 at start so we don't have to do it on errors below.
            # length($msg) now contains the unescaped message length.
            $msgLen = 0;

            $msgRxCount++;

            if($debugLevel >= 10) {
                print("Rx@" . time_now() . ": " . hex_str($msg) . "\n");
            }

            if(length($msg) != 16) {
                # After unescaping special values and cutting off the trailing
                # \xfe that ends an uncorrupted message, the message should
                # always be 16 bytes long.
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

                if($msg =~ /\xc0\xfd\xe2(..)(.)(..)\x00\x00\x00\x00\x00\x00.\xc0/s) {
                    # Handle linkready message from slave.
                    #
                    # We expect to see one of these before we start sending our
                    # own heartbeat message to slave.
                    # Once we start sending our heartbeat to slave once per
                    # second, it should no longer send these linkready messages.
                    # If slave doesn't hear master's heartbeat for around 10
                    # seconds, it sends linkready once per 10 seconds and starts
                    # flashing its red LED 4 times with the top green light on.
                    # Red LED stops flashing if we start sending heartbeat
                    # again.
                    my $senderID = $1;
                    my $sign = $2;
                    my $maxAmps = ((vec($3, 0, 8) << 8) + vec($3, 1, 8)) / 100;
                    if($debugLevel >= 1) {
                        printf(time_now() . ": %.2f amp slave TWC %02x%02x is ready to link.  Sign: %s\n",
                            $maxAmps, vec($senderID, 0, 8), vec($senderID, 1, 8),
                            hex_str($sign));
                    }

                    if($maxAmps >= 80) {
                        # U.S. chargers need a spike to 21A to cancel a 6A
                        # charging limit imposed in an Oct 2017 Tesla car
                        # firmware update. See notes where
                        # $spikeAmpsToCancel6ALimit is used.
                        $spikeAmpsToCancel6ALimit = 21;
                    }
                    else {
                        # EU chargers need a spike to only 16A.  This value
                        # comes from a forum post and has not been directly
                        # tested.
                        $spikeAmpsToCancel6ALimit = 16;
                    }

                    if($senderID eq $fakeTWCID) {
                        print("Slave TWC reports same ID as master: %02x%02x.  Slave should resolve by changing its ID.\n");
                        # I tested sending a linkready to a real master with the
                        # same ID as master and instead of master sending back
                        # its heartbeat message, it sent 5 copies of its
                        # linkready1 and linkready2 messages. Those messages
                        # will prompt a real slave to pick a new random value
                        # for its ID.
                        #
                        # We mimic that behavior by setting $numInitMsgsToSend =
                        # 10 to make the idle code at the top of the for(;;)
                        # loop send 5 copies of linkready1 and linkready2.
                        $numInitMsgsToSend = 10;
                        next;
                    }

                    # We should always get this linkready message at least once
                    # and generally no more than once, so this is a good
                    # opportunity to add the slave to our known pool of slave
                    # devices.
                    my $slaveTWC = new_slave($senderID, $maxAmps);

                    # We expect $maxAmps to be 80 on U.S. chargers and 32 on EU
                    # chargers. Either way, don't allow
                    # $slaveTWC->{wiringMaxAmps} to be greater than $maxAmps.
                    if($slaveTWC->{wiringMaxAmps} > $maxAmps) {
                        print("\n\n!!! DANGER DANGER !!!\nYou have set \$wiringMaxAmpsPerTWC to "
                              . $wiringMaxAmpsPerTWC
                              . " which is greater than the max "
                              . $maxAmps . " amps your charger says it can handle.  "
                              . "Please review instructions in the source code and consult an "
                              . "electrician if you don't know what to do.\n\n");
                        $slaveTWC->{wiringMaxAmps} = $maxAmps / 4;
                    }

                    $slaveTWC->send_master_heartbeat();
                }
                elsif($msg =~ /\xc0\xfd\xe0(..)(..)(.......).\xc0/s) {
                    # Handle heartbeat message from slave.
                    #
                    # These messages come in as a direct response to each
                    # heartbeat message from master. Slave does not send its
                    # heartbeat until it gets one from master first.
                    # A real master sends heartbeat to a slave around once per
                    # second, so we do the same near the top of this for(;;)
                    # loop. Thus, we should receive a heartbeat reply from the
                    # slave around once per second as well.
                    my $senderID = $1;
                    my $receiverID = $2;
                    my @heartbeatData = unpack('C*', $3);

                    my $slaveTWC = $slaveTWCs{$senderID};
                    if(!defined($slaveTWC)) {
                        # Normally, a slave only sends us a heartbeat message if
                        # we send them ours first, so it's not expected we would
                        # hear heartbeat from a slave that's not in our list.
                        printf("ERROR: Received heartbeat message from "
                                . "slave %02x%02x that we've not met before.\n\n",
                                vec($senderID, 0, 8), vec($senderID, 1, 8));
                        next;
                    }

                    if($fakeTWCID eq $receiverID) {
                        $slaveTWC->receive_slave_heartbeat(@heartbeatData);
                    }
                    else {
                        # I've tried different $fakeTWCID values to verify a
                        # slave will send our $fakeTWCID back to us as
                        # $receiverID. However, I once saw it send $receiverID =
                        # 0000.
                        # I'm not sure why it sent 0000 and it only happened
                        # once so far, so it could have been corruption in the
                        # data or an unusual case.
                        if($debugLevel >= 1) {
                            printf(time_now() . ": WARNING: Slave TWC %02x%02x status data: %s sent to unknown TWC id %s.\n\n",
                                vec($senderID, 0, 8), vec($senderID, 1, 8),
                                hex_ary(@heartbeatData), hex_str($receiverID));
                        }
                    }
                }
                else {
                    print(time_now() . ": *** UNKNOWN MESSAGE FROM SLAVE:\n" . hex_str($msg)
                          . "\nPlease private message user CDragon at http://teslamotorsclub.com\n"
                          . "with a copy of this error.\n\n");
                }
            }
            else {
                ###########################
                # Pretend to be a slave TWC

                if($msg =~ /\xc0\xfc\xe1(..)(.)\x00\x00\x00\x00\x00\x00\x00\x00.\xc0/s) {
                    # Handle linkready1 from master.
                    # See notes in send_master_linkready1() for details.
                    my $senderID = $1;
                    my $sign = $2;

                    # This message seems to always contain seven 00 bytes in its
                    # data area. If we ever get this message with non-00 data
                    # we'll print it as an unexpected message.

                    if($debugLevel >= 5) {
                        printf(time_now() . ": Master TWC %02x%02x is cruising the streets.  Sign: %ls\n",
                            vec($senderID, 0, 8), vec($senderID, 1, 8),
                            hex_str($sign));
                    }

                    if($senderID eq $fakeTWCID) {
                        master_id_conflict();
                    }

                    # Other than picking a new fakeTWCID if ours conflicts with
                    # master, it doesn't seem that a real slave will make any
                    # sort of direct response when sent a master's linkready1.
                }
                elsif($msg =~ /\xc0\xfb\xe2(..)(.)\x00\x00\x00\x00\x00\x00\x00\x00.\xc0/s) {
                    # Handle linkready2 from master.
                    # See notes in send_master_linkready2() for details.
                    my $senderID = $1;
                    my $sign = $2;

                    # This message seems to always contain seven 00 bytes in its
                    # data area. If we ever get this message with non-00 data
                    # we'll print it as an unexpected message.

                    if($debugLevel >= 1) {
                        printf(time_now() . ": Master TWC %02x%02x wants to hook up.  Sign: %s\n",
                            vec($senderID, 0, 8), vec($senderID, 1, 8),
                            hex_str($sign));
                    }

                    if($senderID eq $fakeTWCID) {
                        master_id_conflict();
                    }

                    # I seem to remember that a slave will respond with an
                    # immediate linkready when it sees master's linkready2. In
                    # fact, I think a real slave sends 5 copies of linkready
                    # about a second apart before returning to sending them once
                    # per 10 seconds. I don't bother emulating that since master
                    # will see one of our 10-second linkreadys eventually.
                    send_slave_linkready();
                }
                elsif($msg =~ /\xc0\xfb\xe0(..)(..)(.......).\xc0/s) {
                    # Handle heartbeat message from a master.
                    my $senderID = $1;
                    my $receiverID = $2;
                    my @heartbeatData = unpack('C*', $3);

                    if($receiverID ne $fakeTWCID) {
                        # This message was intended for another slave.
                        # Ignore it.
                        if($debugLevel >= 1) {
                            printf(time_now() . ": Master %02x%02x sent "
                                . "heartbeat message %s to receiver %02x%02x "
                                . "that isn't our fake slave.\n",
                                vec($senderID, 0, 8), vec($senderID, 1, 8),
                                hex_ary(@heartbeatData),
                                vec($receiverID, 0, 8), vec($receiverID, 1, 8));
                        }
                        next;
                    }

                    if($debugLevel >= 1) {
                        printf(time_now() . ": Master %02x%02x: %s  Slave: %s\n",
                            vec($senderID, 0, 8), vec($senderID, 1, 8),
                            hex_ary(@heartbeatData), hex_ary(@slaveHeartbeatData));
                    }

                    # A real slave mimics master's status bytes [1]-[2]
                    # representing max charger power even if the master sends it
                    # a crazy value.
                    $slaveHeartbeatData[1] = $heartbeatData[1];
                    $slaveHeartbeatData[2] = $heartbeatData[2];

                    # Slaves always respond to master's heartbeat by sending
                    # theirs back.
                    send_slave_heartbeat($senderID);
                }
                elsif($msg =~ /\xc0\xfc\x1d\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00.\xc0/s) {
                    # Handle 4-hour idle message
                    #
                    # I haven't verified this, but TheNoOne reports receiving
                    # this message from a Master TWC three times in a row every
                    # 4 hours:
                    #   c0 fc 1d 00 00 00 00 00 00 00 00 00 00 00 1d c0
                    # I suspect his logging was corrupted to strip the final fe
                    # byte, unless Tesla changed the protocol to 16 bytes just
                    # for this one message.
                    # I also suspect this message is only sent when the master
                    # doesn't see any other TWCs on the network, so I don't
                    # bother to have our fake master send these messages being
                    # as there's no point in playing a fake master with no
                    # slaves around.
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


################################################################################
# Begin subs

sub load_settings
{
   if(open(my $fh, '<', $settingsFileName)) {
        while(my $line = <$fh>) {
            if($line =~ m/^\s*nonScheduledAmpsMax\s*=\s*([-0-9.]+)/m) {
                $nonScheduledAmpsMax = $1;
                if($debugLevel >= 10) {
                    print("load_settings: \$nonScheduledAmpsMax set to $nonScheduledAmpsMax\n");
                }
            }
            if($line =~ m/^\s*scheduledAmpsMax\s*=\s*([-0-9.]+)/m) {
                $scheduledAmpsMax = $1;
                if($debugLevel >= 10) {
                    print("load_settings: \$scheduledAmpsMax set to $scheduledAmpsMax\n");
                }
            }
            if($line =~ m/^\s*scheduledAmpsStartHour\s*=\s*([-0-9.]+)/m) {
                $scheduledAmpsStartHour = $1;
                if($debugLevel >= 10) {
                    print("load_settings: \$scheduledAmpsStartHour set to $scheduledAmpsStartHour\n");
                }
            }
            if($line =~ m/^\s*scheduledAmpsEndHour\s*=\s*([-0-9.]+)/m) {
                $scheduledAmpsEndHour = $1;
                if($debugLevel >= 10) {
                    print("load_settings: \$scheduledAmpsEndHour set to $scheduledAmpsEndHour\n");
                }
            }
            if($line =~ m/^\s*hourResumeTrackGreenEnergy\s*=\s*([-0-9.]+)/m) {
                $hourResumeTrackGreenEnergy = $1;
                if($debugLevel >= 10) {
                    print("load_settings: \$hourResumeTrackGreenEnergy set to $hourResumeTrackGreenEnergy\n");
                }
            }
        }
        close $fh;
    }
}

sub save_settings
{
    if(open(my $fh, '>', $settingsFileName)) {
        print $fh "nonScheduledAmpsMax=$nonScheduledAmpsMax\n"
                . "scheduledAmpsMax=$scheduledAmpsMax\n"
                . "scheduledAmpsStartHour=$scheduledAmpsStartHour\n"
                . "scheduledAmpsEndHour=$scheduledAmpsEndHour\n"
                . "hourResumeTrackGreenEnergy=$hourResumeTrackGreenEnergy\n";
        close($fh);
    }
}

sub new_slave
{
    my ($newSlaveID, $maxAmps) = @_;
    my $slaveTWC = $slaveTWCs{$newSlaveID};

    if(defined($slaveTWC)) {
        # We already know about this slave.
        return $slaveTWC;
    }

    $slaveTWC = TWCSlave->new('ID' => $newSlaveID, 'maxAmps' => $maxAmps);
    $slaveTWCs{$newSlaveID} = $slaveTWC;
    push @slaveTWCRoundRobin, $slaveTWC;

    if(@slaveTWCRoundRobin > 3) {
        print("WARNING: More than 3 slave TWCs seen on network.  "
            . "Dropping oldest: " . hex_str($slaveTWCRoundRobin[0]->{ID}) . ".\n\n");
        delete_slave($slaveTWCRoundRobin[0]->{ID});
    }

    return $slaveTWC;
}

sub delete_slave
{
    my $deleteSlaveID = $_[0];

    for(my $i = 0; $i < @slaveTWCRoundRobin; $i++) {
        if($slaveTWCRoundRobin[$i]->{ID} eq $deleteSlaveID) {
            splice(@slaveTWCRoundRobin, $i, 1);
            last;
        }
    }

    delete $slaveTWCs{$deleteSlaveID};
}

sub master_id_conflict
{
    # Master's ID matches our ID, which means we must change our ID because
    # master will not.
    vec($fakeTWCID, 0, 8) = int(rand(256));
    vec($fakeTWCID, 1, 8) = int(rand(256));

    # Slaves also seem to change their sign during a conflict.
    vec($slaveSign, 0, 8) = int(rand(256));

    printf("Master's ID matches our fake slave's ID.  "
        . "Picked new random ID %02x%02x with sign %02x\n",
        vec($fakeTWCID, 0, 8), vec($fakeTWCID, 1, 8),
        vec($slaveSign, 0, 8));
}

sub is_slave_total_power_unsafe
{
    my $totalAmps = 0;
    foreach(@slaveTWCRoundRobin) {
        $totalAmps += $_->{lastAmpsMax};
    }
    if($debugLevel >= 10) {
        print "Total amps of all slaves: " . $totalAmps . "\n";
    }
    if($totalAmps > $wiringMaxAmpsAllTWCs) {
        return 1;
    }
    return 0;
}


sub send_msg
{
    my $msg = $_[0];
    my $checksum = vec($msg, 1, 8) + vec($msg, 2, 8) + vec($msg, 3, 8)
                + vec($msg, 4, 8) + vec($msg, 5, 8) + vec($msg, 6, 8)
                + vec($msg, 7, 8) + vec($msg, 8, 8) + vec($msg, 9, 8)
                + vec($msg, 10, 8) + vec($msg, 11, 8) + vec($msg, 12, 8);
    $msg .= chr($checksum & 0xFF);

    # The protocol uses c0 to mark the next byte as having special meaning:
    #   c0 fb, c0 fc, and c0 fd mark the start of messages.
    #   c0 fe marks the end of a message.
    # Therefore, c0 can not appear within a message. They could have just used
    # c0 c0 to mean an actual c0 byte (doubling a special character is commonly
    # used to escape it), but instead some insane person decided that an actual
    # c0 byte would be represented by db dc!
    # Ok, so what about an actual db byte in a message? Why, it's represented by
    # db dd of course! Certainly wouldn't want to escape db using db db (by
    # doubling it) because that's just too obvious. *facepalm*
    # Maybe they had some good reason for this crazy method of escaping special
    # values but it makes no sense to me.
    # I've confirmed fb, fc, fd, and fe are not special values and I hope there
    # aren't others lurking.
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

    $timeLastTx = time;
}

sub unescape_msg
{
    my ($msg, $msgLen) = @_;
    $msg = substr($msg, 0, $msgLen);

    # See notes in send_msg() for the crazy way certain bytes in messages are
    # escaped.
    # We basically want to change \xdb\xdc into \xc0 and \xdb\xdd into \xdb.
    # Only scan to one less than the length of the string to avoid running off
    # the end looking at $i+1.
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

                # Replace the character with something even though it's probably
                # not the right thing.
                substr($msg, $i, 2, "\xdb");
            }
        }
    }

    return $msg;
}


sub send_master_linkready1
{
    if($debugLevel >= 1) {
        print(time_now() . ": Send master linkready1\n");
    }
    # When master is powered on or reset, it sends 5 to 7 copies of this
    # linkready1 message followed by 5 copies of linkready2 (I've never seen
    # more or less than 5 of linkready2).
    #
    # This linkready1 message advertises master's ID to other slaves on the
    # network.
    # If a slave happens to have the same id as master, it will pick a new
    # random ID. Other than that, slaves don't seem to respond to linkready1.

    # linkready1 and linkready2 are identical except fc e1 is replaced by fb e2
    # in bytes 2-3. Both messages will cause a slave to pick a new id if the
    # slave's id conflicts with master. Only linkready2 will cause a slave to
    # respond immediately with its own linkready message (though I'm not
    # absolutely sure about that).
    # If a slave stops sending heartbeats for awhile, master may send a series
    # of linkready1 and linkready2 messages in seemingly random order, which
    # means they don't indicate any sort of startup state.

    # linkready1 is not sent again after boot/reset unless a slave sends its
    # ready_to_link message.
    # At that point, linkready1 message may start sending every 1-5 seconds, or
    # it may not be sent at all.
    # Behaviors I've seen:
    #   Not sent at all as long as slave keeps responding to heartbeat messages
    #   right from the start.
    #   If slave stops responding, then re-appears, linkready1 gets sent
    #   frequently.

    # One other possible purpose of linkready1 and/or linkready2 is to trigger
    # an error condition if two TWCs on the network transmit those messages.
    # That means two TWCs have rotary switches setting them to master mode and I
    # believe they will both flash their red LED 4 times with top green light on
    # if that happens.

    # Also note that linkready1 starts with fc e1 which is similar to the fc d1
    # message that masters send out every 4 hours when idle. Oddly, the fc d1
    # message contains all zeros instead of the master's id, so it seems
    # pointless.

    # I don't understand the purpose of having both linkready1 and linkready2
    # but it doesn't seem to matter. If anyone figures it out, contact
    # user CDragon at teslamotorsclub.com because I'm curious.
    send_msg("\xFC\xE1$fakeTWCID$masterSign\x00\x00\x00\x00\x00\x00\x00\x00");
}

sub send_master_linkready2
{
    if($debugLevel >= 1) {
        print(time_now() . ": Send master linkready2\n");
    }
    # This linkready2 message is also sent 5 times when master is booted/reset
    # and then not sent again if no other TWCs are heard from on the network.
    # If the master has ever seen a slave on the network, linkready2 is sent at
    # long intervals.
    # Slaves do not seem to respond to linkready1 or linkready2.
    #
    # It may be that this linkready2 message that sends fb e2 and the master
    # heartbeat that sends fb e0 message are really the same, (same fb byte
    # which I think is message type) except the e0 version includes the TWC ID
    # of the slave the message is intended for whereas the e2 version has no
    # recipient TWC ID.
    #
    # Once a master starts sending heartbeat messages to a slave, it
    # no longer sends the global linkready2 message (or if it does,
    # they're quite rare so I haven't seen them).
    send_msg("\xFB\xE2$fakeTWCID$masterSign\x00\x00\x00\x00\x00\x00\x00\x00");
}

sub send_slave_linkready
{
    # In the message below, \x1F\x40 (hex 0x1f40 or 8000 in base 10) refers to
    # this being a max 80.00Amp charger model.
    # EU chargers are 32A and send 0x0c80 (3200 in base 10).
    #
    # I accidentally changed \x1f\x40 to \x2e\x69 at one point, which makes the
    # master TWC immediately start blinking its red LED 6 times with top green
    # LED on. Manual says this means "The networked Wall Connectors have
    # different maximum current capabilities".
    send_msg("\xFD\xE2$fakeTWCID$slaveSign\x1F\x40\x00\x00\x00\x00\x00\x00");
}

sub send_slave_heartbeat
{
    my $masterID = $_[0];

    # Send slave heartbeat
    #
    # Heartbeat includes 7 bytes of data we store in @slaveHeartbeatData.
    # Meaning of 7 bytes:
    #
    # Byte 1 values I've seen with guesses at meaning:
    #   00 Ready (may or may not be plugged in)
    #   01 Plugged in, charging
    #   02 Lost communication with master
    #      I usually see this status briefly if I stop fake master script for
    #      awhile, then start it.  This value may also indicate other error
    #      conditions.
    #   03 Plugged in, do not charge
    #      I've seen this state briefly when plug is first inserted, and I've
    #      seen this state remain indefinitely after pressing stop charge on
    #      car's screen or when the car reaches its target charge percentage. It
    #      may also remain indefinitely if TWCManager script is stopped for too
    #      long while car is charging even after TWCManager is restarted. In
    #      that case, car will not charge even when start charge on screen is
    #      pressed - only re-plugging in charge cable fixes it.
    #   04 Plugged in, ready to charge or charge scheduled
    #      I've seen this state even when car is set to charge at a future time
    #      via its UI.  In that case, it won't accept power offered to it.
    #   05 Busy?
    #      I've only seen it hit this state for 1 second at a time and it can
    #      seemingly happen during any other state. Maybe it means wait, I'm
    #      busy? Communicating with car? When Master sends 05, slave takes it as
    #      meaning the next four bytes contain a max charging amps value, but it
    #      doesn't seem that slave uses it in the same way.
    #   08 Starting to charge?
    #      This state may remain for a few seconds while car ramps up from 0A
    #      to 1.3A, then state usually changes to 01. Sometimes car skips 08
    #      and goes directly to 01.
    #      I saw 08 consistently each time I stopped my fake master script with
    #      car scheduled to charge, plugged in, charge port blue. If the car is
    #      actually charging and you stop TWCManager, after 20-30 seconds the
    #      charge port turns solid red, steering wheel display says "charge
    #      cable fault", and main screen says "check charger power". When
    #      TWCManager is started, it sees this 08 status again. If we start
    #      TWCManager and send the slave a new max power value, 08 becomes 00
    #      and car starts charging again.
    #
    # Byte 2-3 is the max current available as provided by bytes 2-3 in our
    # fake master status.
    # For example, if bytes 2-3 are 0f a0, combine them as 0x0fa0 hex which
    # is 4000 in base 10. Move the decimal point two places left and you get
    # 40.00Amps max.
    # Note that once bytes 2-3 are greater than 0, Byte 1 changes from 04 to
    # 01 or 00 during charging.
    #
    # Byte 4-5 represents the power the car is actually drawing for charging.
    # When a car is told to charge at 19A you may see a value like 07 28 which is
    # 0x728 hex or 1832 in base 10. Move the decimal point two places left
    # and you see the charger is using 18.32A.
    # Some TWCs report 0A when a car is not charging while others may report
    # small values such as 0.25A. I suspect 0A is what should be reported and
    # any small value indicates a minor calibration error.
    #
    # Byte 6-7 are always 00 00 from what I've seen and could be reserved
    # for future use or may be used in a situation I've not observed.

    ###############################
    # How was the above determined?
    #
    # An unplugged slave sends a status like this:
    #   00 00 00 00 19 00 00
    #
    # A real master always sends all 00 status data to a slave reporting the
    # above status. $slaveHeartbeatData[0] is the main driver of how master
    # responds, but whether $slaveHeartbeatData[1] and [2] have 00 or non-00
    # values also matters.
    #
    # I did a test with fake slave sending $slaveHeartbeatData[0] values
    # from 00 to ff along with $slaveHeartbeatData[1-2] of 00 and whatever
    # value Master last responded with. I found:
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
    # In other words, master always sends all 00 unless slave sends
    # $slaveHeartbeatData[0] 04 or 08 with $slaveHeartbeatData[1-2] both 00.
    #
    # I interpret all this to mean that when slave sends
    # $slaveHeartbeatData[1-2] both 00, it's requesting a max power from
    # master. Master responds by telling the slave how much power it can
    # use. Once the slave is saying how much max power it's going to use
    # ($slaveHeartbeatData[1-2] = 12 c0 = 32.00A), master indicates that's
    # fine by sending 00 00.
    #
    # However, if the master wants to set a lower limit on the slave, all it
    # has to do is send any $heartbeatData[1-2] value greater than 00 00 at
    # any time and slave will respond by setting its
    # $slaveHeartbeatData[1-2] to the same value.
    #
    # I thought slave might be able to negotiate a lower value if, say, the
    # car reported 40A was its max capability or if the slave itself could
    # only handle 80A, but the slave dutifully responds with the same value
    # master sends it even if that value is an insane 655.35A. I tested
    # these values on my car which has a 40A limit when AC charging and
    # slave accepts them all:
    #   0f aa (40.10A)
    #   1f 40 (80.00A)
    #   1f 41 (80.01A)
    #   ff ff (655.35A)

    send_msg("\xFD\xE0$fakeTWCID$masterID"
             . pack('C*', @slaveHeartbeatData));
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
        $result .= sprintf("%02x ", $_);
    }

    return substr($result, 0, length($result) - 1);
}


################################################################################
# Begin TWCSlave object methods

package TWCSlave;

sub new
{
    my $class = shift;

    # This line will set $self->{ID}.
    my $self = { @_ };

    $self->{masterHeartbeatData} = [0x00,0x00,0x00,0x00,0x00,0x00,0x00]; # Square brackets make an array reference instead of an array.
    $self->{timeLastRx} = time;
    $self->{lastAmpsMax} = -1;
    $self->{lastAmpsActual} = -1;
    $self->{reportedAmpsMax} = 0;
    $self->{reportedAmpsActual} = 0;
    $self->{reportedState} = 0;
    $self->{timeLastAmpsMaxChanged} = time;
    $self->{timeLastAmpsActualChanged} = time;
    $self->{lastHeartbeatDebugOutput} = '';
    $self->{wiringMaxAmps} = $wiringMaxAmpsPerTWC;

    return bless $self, $class;
}

sub send_master_heartbeat
{
    # Send our fake master's heartbeat to this TWCSlave.
    #
    # Heartbeat includes 7 bytes of data we store in @masterHeartbeatData.
    # Meaning of 7 bytes:
    #
    # Byte 1 values I've seen with guesses at meaning:
    #   00 Idle/all is well
    #   02 Error
    #     I saw this from a real master TWC when I caused it to blink its
    #     red LED 6 times by sending a bad command. If you send 02 to a
    #     slave TWC it responds with 02 in its heartbeat, then stops sending
    #     heartbeat and refuses further communication. It blinks its red LED
    #     3 times (which oddly means "Incorrect rotary switch setting") and
    #     must be reset with the red button on its side.
    #   05 Tell slave charger to limit power to number of amps in bytes 2-3.
    # I haven't spent much time trying to discover if other values are
    # possible. 00 and 05 are enough to fully control a slave TWC's power
    # output.
    #
    # Byte 2-3 is the max current a slave TWC can charge at.
    # For example, if bytes 2-3 are 0f a0, combine them as 0x0fa0 hex which
    # is 4000 in base 10. Move the decimal point two places left and you get
    # 40.00Amps max.
    #
    # Byte 4: Usually 00 but became 01 when a master TWC was plugged
    # in to a car.
    #
    # Byte 5-7 are always 00 and may be unused.
    #
    # Example 7-byte data that real masters have sent:
    #   00 00 00 00 00 00 00  (Idle)
    #   02 04 00 00 00 00 00  (Error.  04 is probably an error code because
    #                          interpretting 04 00 as an amp value gets us an
    #                          odd 10.24A)
    #   05 0f a0 00 00 00 00  (Master telling slave to limit power to 0f a0
    #                         (40.00A))
    #   05 07 d0 01 00 00 00  (Master plugged in to a car and presumably telling
    #                          slaves to limit power to 07 d0 (20.00A). 01 byte
    #                          might indicate master is plugged in? Master would
    #                          not charge its car because I didn't have the fake
    #                          slave issue the correct response.)
    my $self = shift @_;

    main::send_msg("\xFB\xE0$fakeTWCID" . $self->{ID}
             . pack('C*', @{$self->{masterHeartbeatData}}));
}

sub receive_slave_heartbeat
{
    # Handle heartbeat message received from real slave TWC.
    my ($self, @heartbeatData) = @_;

    $self->{timeLastRx} = time;

    $self->{reportedAmpsMax} = (($heartbeatData[1] << 8) + $heartbeatData[2]) / 100;
    $self->{reportedAmpsActual} = (($heartbeatData[3] << 8) + $heartbeatData[4]) / 100;
    $self->{reportedState} = $heartbeatData[0];

    # $self->{lastAmpsMax} is initialized to -1.
    # If we find it at that value, set it to the current value reported by the
    # TWC.
    if($self->{lastAmpsMax} < 0) {
        $self->{lastAmpsMax} = $self->{reportedAmpsMax};
    }

    # Keep track of the amps the slave is actually using and the last time it
    # changed by more than 0.8A.
    # Also update $self->{lastAmpsActual} if it's still set to its initial
    # value of -1.
    if($self->{lastAmpsActual} < 0
       || abs($self->{reportedAmpsActual} - $self->{lastAmpsActual}) > 0.8
    ) {
        $self->{timeLastAmpsActualChanged} = time;
        $self->{lastAmpsActual} = $self->{reportedAmpsActual};
    }

    my ($sec,$min,$hour,$mday,$mon,$year,$wday,$yday,$isdst) =
                                                localtime(time);
    my $hourNow = $hour + ($min / 60);

    # Check if it's time to resume tracking green energy.
    if($nonScheduledAmpsMax != -1 && $hourResumeTrackGreenEnergy > -1
       && $hourResumeTrackGreenEnergy == $hourNow
    ) {
        $nonScheduledAmpsMax = -1;
        main::save_settings();
    }

    # Check if we're within the hours we must use $scheduledAmpsMax instead of
    # $nonScheduledAmpsMax
    if($scheduledAmpsMax > 0
         &&
       $scheduledAmpsStartHour > -1
         &&
       $scheduledAmpsEndHour > -1
    ) {
        my $blnUseScheduledAmps = 0;
        if($scheduledAmpsStartHour > $scheduledAmpsEndHour) {
            # We have a time like 8am to 7am which we must interpret as the
            # 23-hour period after 8am or before 7am.
            if($hourNow >= $scheduledAmpsStartHour
               || $hourNow < $scheduledAmpsEndHour
            ) {
               $blnUseScheduledAmps = 1;
            }
        }
        else {
            # We have a time like 7am to 8am which we must interpret as the
            # 1-hour period between 7am and 8am.
            if($hourNow >= $scheduledAmpsStartHour
               && $hourNow < $scheduledAmpsEndHour
            ) {
               $blnUseScheduledAmps = 1;
            }
        }

        if($blnUseScheduledAmps) {
            # We're within the scheduled hours that we need to provide a set
            # number of amps.
            $maxAmpsToDivideAmongSlaves = $scheduledAmpsMax;
        }
        else {
            if($nonScheduledAmpsMax > -1) {
                $maxAmpsToDivideAmongSlaves = $nonScheduledAmpsMax;
            }
        }
    }


    if($maxAmpsToDivideAmongSlaves > $wiringMaxAmpsAllTWCs) {
        # Never tell the slaves to draw more amps than the physical charger
        # wiring can handle.
        if($debugLevel >= 1) {
            print("ERROR: \$maxAmpsToDivideAmongSlaves $maxAmpsToDivideAmongSlaves > "
                . "\$wiringMaxAmpsAllTWCs $wiringMaxAmpsAllTWCs.  "
                . "See notes above \$wiringMaxAmpsAllTWCs.\n");
        }
        $maxAmpsToDivideAmongSlaves = $wiringMaxAmpsAllTWCs;
    }

    # Allocate this slave a fraction of $maxAmpsToDivideAmongSlaves divided by
    # the number of slave TWCs on the network.
    my $desiredAmpsMax =
        int($maxAmpsToDivideAmongSlaves / @slaveTWCRoundRobin);

    if($desiredAmpsMax < 5.0) {
        # To avoid errors, don't charge the car under 5.0A. 5A is the lowest
        # value you can set using the Tesla car's main screen, so lower values
        # might have some adverse affect on the car. I actually tried lower
        # values when the sun was providing under 5A of power and found the car
        # would occasionally set itself to state 03 and refuse to charge until
        # you re-plugged the charger cable. Clicking "Start charging" in the
        # car's UI or in the phone app would not start charging.
        #
        # A 5A charge only delivers ~3 miles of range to the car per hour, but
        # it forces the car to remain "on" at a level that it wastes some power
        # while it's charging. The lower the amps, the more power is wasted.
        # This is another reason not to go below 5A.
        #
        # So if there isn't at least 5A of power available, pass 0A as the
        # desired value. This tells the car to stop charging and it will enter
        # state 03 and go to sleep. You will hear the power relay in the TWC
        # turn off. When $desiredAmpsMax trends above 6A again, it tells the car
        # there's power.
        # If a car is set to energy saver mode in the car's UI, the car seems to
        # wake every 15 mins or so (unlocking or using phone app also wakes it)
        # and next time it wakes, it will see there's power and start charging.
        # Without energy saver mode, the car should begin charging within about
        # 10 seconds of changing this value.
        $desiredAmpsMax = 0;

        if(
           $self->{lastAmpsMax} > 0
             &&
           (
             time - $self->{timeLastAmpsMaxChanged} < 60
               ||
             time - $self->{timeLastAmpsActualChanged} < 60
               ||
             $self->{reportedAmpsActual} < 4.0
           )
        ) {
            # We were previously telling the car to charge but now we want to
            # tell it to stop. However, it's been less than a minute since we
            # told it to charge or since the last significant change in the
            # car's actual power draw or the car has not yet started to draw at
            # least 5 amps (telling it 5A makes it actually draw around
            # 4.18-4.27A so we check for $self->{reportedAmpsActual} < 4.0).
            #
            # Once we tell the car to charge, we want to keep it going for at
            # least a minute before turning it off again. My concern is that
            # yanking the power at just the wrong time during the start-charge
            # negotiation could put the car into an error state where it won't
            # charge again without being re-plugged. This concern is
            # hypothetical and most likely could not happen to a real car, but
            # I'd rather not take any chances with getting someone's car into a
            # non-charging state so they're stranded when they need to get
            # somewhere. Note that non-Tesla cars using third-party adapters to
            # plug in are at a higher risk of encountering this sort of
            # hypothetical problem.
            #
            # The other reason for this tactic is that in the minute we wait,
            # $desiredAmpsMax might rise above 5A in which case we won't have to
            # turn off the charger power at all. Avoiding too many on/off cycles
            # preserves the life of the TWC's main power relay and may also
            # prevent errors in the car that might be caused by turning its
            # charging on and off too rapidly.
            #
            # Seeing $self->{reportedAmpsActual} < 4.0 means the car hasn't
            # ramped up to whatever level we told it to charge at last time. It
            # may be asleep and take up to 15 minutes to wake up, see there's
            # power, and start charging.
            #
            # Unfortunately, $self->{reportedAmpsActual} < 4.0 can also mean the
            # car is at its target charge level and may not accept power for
            # days until the battery drops below a certain level. I can't think
            # of a reliable way to detect this case. When the car stops itself
            # from charging, we'll see $self->{reportedAmpsActual} drop to near
            # 0.0A and $heartbeatData[0] becomes 03, but we can see the same 03
            # state when we tell the TWC to stop charging. We could record the
            # time the car stopped taking power and assume it won't want more
            # for some period of time, but we can't reliably detect if someone
            # unplugged the car, drove it, and re-plugged it so it now needs
            # power, or if someone plugged in a different car that needs power.
            # Even if I see the car hasn't taken the power we've offered for the
            # last hour, it's conceivable the car will reach a battery state
            # where it decides it wants power the moment we decide it's safe to
            # stop offering it. Thus, I think it's safest to always wait until
            # the car has taken 5A for a minute before cutting power even if
            # that means the car will charge for a minute when you first plug it
            # in after a trip even at a time when no power should be available.
            #
            # One advantage of the above situation is that whenever you plug the
            # car in, unless no power has been available since you unplugged,
            # the charge port will turn green and start charging for a minute.
            # This lets the owner quickly see that TWCManager is working
            # properly each time they return home and plug in.
            if($debugLevel >= 10) {
                print("Don't stop charging yet because:\n"
                      . 'time - $self->{timeLastAmpsMaxChanged} '
                      . (time - $self->{timeLastAmpsMaxChanged})
                      . "< 60\n"
                      . '|| time - $self->{timeLastAmpsActualChanged} '
                      . (time - $self->{timeLastAmpsActualChanged})
                      . "< 60\n"
                      . '|| $self->{reportedAmpsActual} ' . $self->{reportedAmpsActual}
                      . " < 4\n");
            }
            $desiredAmpsMax = 5.0;
        }
    }
    else {
        # We can tell the TWC how much power to use in 0.01A increments, but the
        # car will only alter its power in larger increments (somewhere between
        # 0.5 and 0.6A). The car seems to prefer being sent whole amps and when
        # asked to adjust between certain values like 12.6A one second and 12.0A
        # the next second, the car reduces its power use to ~5.14-5.23A and
        # refuses to go higher. So it seems best to stick with whole amps.
        $desiredAmpsMax = int($desiredAmpsMax);

        if($self->{lastAmpsMax} == 0
           && time - $self->{timeLastAmpsMaxChanged} < 60
        ) {
            # Keep charger off for at least 60 seconds before turning back on.
            # See reasoning above where I don't turn the charger off till it's
            # been on at least 60 seconds.
            if($debugLevel >= 10) {
                print("Don't start charging yet because:\n"
                      . '$self->{lastAmpsMax} '
                      . $self->{lastAmpsMax} . " == 0\n"
                      . '&& time - $self->{timeLastAmpsMaxChanged} '
                      . (time - $self->{timeLastAmpsMaxChanged})
                      . " < 60\n");
            }
            $desiredAmpsMax = $self->{lastAmpsMax};
        }
        else {
            # Mid Oct 2017, Tesla pushed a firmware update to their cars that
            # seems to create the following bug:
            # If you raise $desiredAmpsMax AT ALL from the car's current max amp
            # limit, the car will drop its max amp limit to the 6A setting
            # (5.14-5.23A actual use as reported in $heartbeatData[2-3]). The
            # odd fix to this problem is to tell the car to raise to at least
            # $spikeAmpsToCancel6ALimit for 5 or more seconds, then tell it to
            # lower the limit to $desiredAmpsMax. Even 0.01A less than
            # $spikeAmpsToCancel6ALimit is not enough to cancel the 6A limit.
            #
            # I'm not sure how long we have to hold $spikeAmpsToCancel6ALimit
            # but 3 seconds is definitely not enough but 5 seconds seems to
            # work. It doesn't seem to matter if the car actually hits
            # $spikeAmpsToCancel6ALimit of power draw. In fact, the car is slow
            # enough to respond that even with 10s at 21A the most I've seen it
            # actually draw starting at 6A is 13A.
            if($debugLevel >= 10) {
                print('$desiredAmpsMax=' . $desiredAmpsMax
                      . ' $spikeAmpsToCancel6ALimit=' . $spikeAmpsToCancel6ALimit
                      . ' $self->{lastAmpsMax}=' . $self->{lastAmpsMax}
                      . ' $self->{reportedAmpsActual}=' . $self->{reportedAmpsActual}
                      . ' time - $self->{timeLastAmpsActualChanged}='
                      . (time - $self->{timeLastAmpsActualChanged})
                      . "\n");
            }

            if(
               $desiredAmpsMax < $spikeAmpsToCancel6ALimit
                 &&
               (
                 $desiredAmpsMax > $self->{lastAmpsMax}
                   ||
                 (
                   # If we somehow trigger the bug that drops power use to
                   # 5.14-5.23A, this should detect it after 10 seconds and
                   # we'll spike our power request to $spikeAmpsToCancel6ALimit
                   # to fix it.
                   $self->{reportedAmpsActual} > 1.0 # The car is drawing enough amps to be charging
                     &&
                   ($self->{lastAmpsMax} - $self->{reportedAmpsActual}) > 1.0 # Car is charging at over an amp under what we want it to charge at.
                     &&
                   time - $self->{timeLastAmpsActualChanged} > 10 # Car hasn't changed its amp draw significantly in over 10 seconds
                 )
               )
            ) {
                $desiredAmpsMax = $spikeAmpsToCancel6ALimit;

                # Note that the car should have no problem increasing max amps
                # to any whole value over $spikeAmpsToCancel6ALimit as long as
                # it's below any upper limit manually set in the car's UI. One
                # time when I couldn't get TWC to push the car over 21A, I found
                # the car's UI had set itself to 21A despite my setting it to
                # 40A the day before. I have been unable to reproduce whatever
                # caused that problem.
            }
            elsif($desiredAmpsMax < $self->{lastAmpsMax}) {
                # Tesla doesn't mind if we set a lower amp limit than the one
                # we're currently using, but make sure we don't change limits
                # more often than every 5 seconds. This has the side effect of
                # holding the 21A limit mentioned above for 5 seconds to make
                # sure the car sees it.
                if($debugLevel >= 10) {
                    print('Reduce amps: time - $self->{timeLastAmpsMaxChanged} '
                        . (time - $self->{timeLastAmpsMaxChanged})
                        . "\n");
                }
                if(time - $self->{timeLastAmpsMaxChanged} < 5) {
                    $desiredAmpsMax = $self->{lastAmpsMax};
                }
            }
        }
    }

    # set_last_amps_max does some final checks to see if the new $desiredAmpsMax
    # is safe. It should be called after we've picked a final value for
    # $desiredAmpsMax.
    $desiredAmpsMax = $self->set_last_amps_max($desiredAmpsMax);

    # See notes in send_slave_heartbeat() for details on how we transmit
    # $desiredAmpsMax and the meaning of the code in
    # $self->{masterHeartbeatData}[0].
    #
    # Rather than only sending $desiredAmpsMax when slave is sending code 04 or
    # 08, it seems to work better to send $desiredAmpsMax whenever it does not
    # equal $self->{reportedAmpsMax} reported by the slave TWC. Doing it that
    # way will get a slave charging again even when it's in state 00 or 03 which
    # it swings between after you set $desiredAmpsMax = 0 to stop charging.
    #
    # I later found that a slave may end up swinging between state 01 and 03
    # when $desiredAmpsMax == 0:
    #   S 032e 0.25/0.00A: 01 0000 0019 0000  M: 00 0000 0000 0000
    #   S 032e 0.25/6.00A: 03 0258 0019 0000  M: 05 0000 0000 0000
    #   S 032e 0.25/0.00A: 01 0000 0019 0000  M: 00 0000 0000 0000
    #   S 032e 0.25/6.00A: 03 0258 0019 0000  M: 05 0000 0000 0000
    #
    # While it's doing this, it's continuously opening and closing the relay on
    # the TWC each second which makes an audible click and will wear out the
    # relay. To avoid that problem, always send code 05 when $desiredAmpsMax ==
    # 0. In that case, slave's response should always look like this:
    #   S 032e 0.25/0.00A: 03 0000 0019 0000 M: 05 0000 0000 0000
    if($self->{reportedAmpsMax} != $desiredAmpsMax
       || $desiredAmpsMax == 0
    ) {
        my $desiredHundredthsOfAmps = int($desiredAmpsMax * 100);
        $self->{masterHeartbeatData} = [0x05,
          ($desiredHundredthsOfAmps >> 8) & 0xFF,
          $desiredHundredthsOfAmps & 0xFF,
          0x00,0x00,0x00,0x00];
    }
    else {
        $self->{masterHeartbeatData} = [0x00,0x00,0x00,0x00,0x00,0x00,0x00];
    }

    if($debugLevel >= 1) {
        my $debugOutput =
            sprintf(": S %02x%02x %02.2f/%02.2fA: "
            . "%02x %02x%02x %02x%02x %02x%02x  "
            . "M: %02x %02x%02x %02x%02x %02x%02x\n",
            vec($self->{ID}, 0, 8), vec($self->{ID}, 1, 8),
            ((($heartbeatData[3] << 8) + $heartbeatData[4]) / 100),
            ((($heartbeatData[1] << 8) + $heartbeatData[2]) / 100),
            $heartbeatData[0], $heartbeatData[1], $heartbeatData[2],
            $heartbeatData[3], $heartbeatData[4], $heartbeatData[5],
            $heartbeatData[6],
            $self->{masterHeartbeatData}->[0], $self->{masterHeartbeatData}->[1], $self->{masterHeartbeatData}->[2],
            $self->{masterHeartbeatData}->[3], $self->{masterHeartbeatData}->[4], $self->{masterHeartbeatData}->[5],
            $self->{masterHeartbeatData}->[6]
            );

        # Only output once-per-second heartbeat debug info when it's different
        # from the last output, or if it's been 10 mins since the last output or
        # if $debugLevel is turned up to 11.
        if($debugOutput ne $self->{lastHeartbeatDebugOutput}
            || time - $timeLastHeartbeatDebugOutput > 600
            || $debugLevel >= 11
        ) {
            print(main::time_now() . $debugOutput);
            $self->{lastHeartbeatDebugOutput} = $debugOutput;
            $timeLastHeartbeatDebugOutput = time;
        }
    }
}

sub set_last_amps_max
# $self->{lastAmpsMax} should only be changed using this sub.
{
    my ($self, $desiredAmpsMax) = @_;

    if($debugLevel >= 10) {
        print("set_last_amps_max(" . main::hex_str($self->{ID})
              . "," . $desiredAmpsMax . ")\n");
    }

    if($desiredAmpsMax != $self->{lastAmpsMax}) {
        my $oldLastAmpsMax = $self->{lastAmpsMax};
        $self->{lastAmpsMax} = $desiredAmpsMax;
        if(main::is_slave_total_power_unsafe()) {
            print "ERROR: Unable to increase power to slave TWC to "
                . $desiredAmpsMax
                . "A without overloading wiring shared by all TWCs.\n";
            $self->{lastAmpsMax} = $oldLastAmpsMax;
            return $self->{lastAmpsMax};
        }

        if($desiredAmpsMax > $self->{wiringMaxAmps}) {
            print "ERROR: Unable to increase power to slave TWC to "
                . $desiredAmpsMax
                . "A without overloading wiring to the TWC.\n";
            $self->{lastAmpsMax} = $oldLastAmpsMax;
            return $self->{lastAmpsMax};
        }

        $self->{timeLastAmpsMaxChanged} = time;
    }
    return $self->{lastAmpsMax};
}

sub punish_slave
{
    # Sadly, this sub is unused.
    print "Slave punished.";
}
