<?php
    ///////////////////////////////////////////////////////////////////////////
    // Configuration parameters

    // Choose how much debugging info to output.
    // 0 is no output other than errors.
    // 1 is just the most useful info.
    // 10 is all info.
    $debugLevel = 0;
    $twcScriptDir = "/etc/twcmanager";

    // End configuration parameters
    ///////////////////////////////////////////////////////////////////////////


    // Prevent page from showing cached version
    header('Expires: Mon, 26 Jul 1997 05:00:00 GMT');
    header('Last-Modified: ' . gmdate("D, d M Y H:i:s") . 'GMT');
    header('Cache-Control: no-cache, must-revalidate');
    header('Pragma: no-cache');
?><!DOCTYPE html>
<html>
<head>
    <title>TWCManager</title>
    <link rel="icon" type="image/png" href="favicon.png">

    <?php /* This tag makes the page fill a mobile phone screen. */ ?>
    <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<?php
    // Initialize Interprocess Communication message queue for sending commands to
    // TWCManager.py script and getting data back.  See notes in TWCManager.py for
    // how IPC works.
    $ipcKey = ftok($twcScriptDir, "T");
    $ipcQueue = msg_get_queue($ipcKey, 0666);

    if(@$_REQUEST['debugTWC'] != '') {
        print '<script>document.title = "TWCDebug";</script>';
        if(@$_REQUEST['submit'] != '') {
            if(@$_REQUEST['setDebugLevel'] > 0) {
                print '<script>document.title = "TWCDebugLevel";</script>';
                ipcCommand('setDebugLevel=' . intval($_REQUEST['setDebugLevel']));
            }
            else if(array_key_exists('beginTest', $_REQUEST)) {
                print '<script>document.title = "TWCTest";</script>';
                if($_REQUEST['beginTest'] == '') {
                    ipcCommand('beginTest');
                }
                else {
                    ipcCommand('beginTest=' . $_REQUEST['beginTest']);
                }
            }
        }
        ?>
        <form action="index.php" method="get">
            <input type="hidden" name="debugTWC" value="<?=htmlspecialchars($_REQUEST['debugTWC'])?>">
            Debug level: <input type="text" name="setDebugLevel" size="2" value="<?=htmlspecialchars(@$_REQUEST['setDebugLevel'])?>">
            <input type="submit" name="submit" value="Set">
        </form>
        <p>
        <form action="index.php" method="get">
            <input type="hidden" name="debugTWC" value="<?=htmlspecialchars($_REQUEST['debugTWC'])?>">
            Test: <input type="text" name="beginTest" size="2" value="<?=htmlspecialchars(@$_REQUEST['beginTest'])?>">
            <input type="submit" name="submit" value="Begin">
        </form>
        <p>
            <a href="index.php?sendTWCMsg=&submit=1">Send message</a>
            | <a href="index.php?setMasterHeartbeatData=&submit=1">Override master heartbeat data</a>
            | <a href="index.php?dumpState=1&submit=1">Dump state</a>
        </p><p>
        <a href="index.php?debugTWC=<?=htmlspecialchars($_REQUEST['debugTWC'])?>&beginTest=&submit=1">Begin test</a>
        </p>
        <?php
        print '</body></html>';

        exit;
    }
    elseif(@$_REQUEST['submit'] != '') {
        if(@$_REQUEST['email'] != '' && @$_REQUEST['password'] != '') {
            ipcCommand('carApiEmailPassword=' . $_REQUEST['email'] . "\n" . $_REQUEST['password']);
            // Wait 5 seconds for TWCManager to log in or getStatus will have us show
            // the user/password entry again.
            usleep(5000000);
        }
        else if(array_key_exists('sendTWCMsg', $_REQUEST)) {
            // This hidden option can be used to tell a TWC to send an arbitrary
            // message on the RS-485 network for debugging and experimentation.
            //
            // *****************************************************************
            // THE WRONG MESSAGE CAN PERMANENTLY DISABLE YOUR TWC.
            // TWCManager.py will prevent you from sending messages known to
            // kill TWCs, but there may still be unknown messages that are
            // damaging, so do not use this feature without good reason.
            // *****************************************************************
            //
            // To use, type a URL like this in your browser:
            // http://(Pi address)/index.php?submit=1&sendTWCMsg=FB1B
            // This will send message FB 1B 00 00 00 00 00 00 00 00 00 00 00
            // on a protocol 2 TWC.  The message is truncated or padded with 00
            // such that it is always the standard message length for your TWC's
            // protocol version.  Message start, CRC, and end bytes are added
            // automatically.
            ?>
            <form action="index.php" method="get">
            Send RS485 message: <input type="text" name="sendTWCMsg" size="40" value="<?=htmlspecialchars($_REQUEST['sendTWCMsg'])?>">
            <input type="submit" name="submit" value="Submit">
            </form>
            <script>document.title = "TWCSendMsg";</script>
            <p>
            <a href="index.php?sendTWCMsg=FB1B&submit=1">Get firmware version</a>
            | <a href="index.php?sendTWCMsg=FB19&submit=1">Get (S)TSN (serial number)</a>
            | <a href="index.php?sendTWCMsg=FB1A&submit=1">Get model</a>
            | <a href="index.php?sendTWCMsg=FCE1777766&submit=1">Master Linkready1</a>
            | <a href="index.php?sendTWCMsg=FBE2777766&submit=1">Master Linkready2</a>
            </p>
            <?php

            if(@$_REQUEST['sendTWCMsg'] != '') {
                ipcCommand('sendTWCMsg=' . preg_replace('/[ \r\n\t]/', '', $_REQUEST['sendTWCMsg']));

                // Most messages return a response within 2 seconds.  The few that
                // don't are likely not safe to use.  Sometimes the message sent
                // gets no response because we happened to send it at the same
                // time another message was sent or received, in which case both
                // messages get corrupted.
                sleep(3);
                if(substr($_REQUEST['sendTWCMsg'], 0, 4) == "FCA1") {
                    // FCA1 will silence TWC for ~5 seconds.  Wait that long
                    // before looking for a response.
                    sleep(5);
                }
                $response = ipcQuery('getLastTWCMsgResponse');
                print '<p>Response: <strong>' . $response . '</strong></p>';
                if(substr($response, 0, 5) == "FD 19") {
                    $serialHexAry = explode(' ', substr($response, 6, strlen($response) - 6 - 3));
                    $stsn = '';
                    foreach($serialHexAry as $value) {
                        $ascii = hexdec($value);
                        if($ascii > 0 && $ascii < 0xFF) {
                            $stsn .= chr($ascii);
                        }
                    }

                    // I originally theorized substr($stsn, 1, 2) is the year of
                    // manufacture, while substr($stsn, 3, 1) represent the
                    // 'half month' of manufacture. So substr($stsn, 3, 1) = 0 =
                    // 1/1, 1 = 1/15, 2 = 2/1, etc. Later, user greenjb reported
                    // an (S)TSN starting with A18D. D = 7/15, but that's after
                    // his delivery date of 6/27. Interpreting as 14-day periods
                    // instead of half-months makes 0 = 1/1, 1 = 1/15, 2 = 1/29,
                    // D = 7/2, which is still too late.
                    //
                    // So, maybe 0 is not used at all, which makes 1 = 1/1, 2 =
                    // 1/15, D = 6/18. It seems unlikely that it was
                    // manufactured and delivered in 9 days, but not impossible
                    // if Tesla also has a factory making them in the EU (do
                    // they?). I then realized that 365 days in a year / 14 day
                    // periods = 26.07. Since there are 26 letters between A-Z,
                    // it seems most likely that A=1/1 instead of 0 = 1/1. Out
                    // of 6 TSNs reported so far, none have had 0-9 in them. I'm
                    // going with that theory for now. That means A18D was
                    // manufactured 2/12/18.
                    $day = ord(substr($stsn, 3, 1)) - 0x41;
                    $day *= 14;
                    $year = intval('20'.substr($stsn, 1, 2));
                    $dateStart = DateTime::createFromFormat('Y z' , $year . ' ' . $day);
                    $dateEnd = DateTime::createFromFormat('Y z' , $year . ' ' . ($day + 13));
                    print '<p><strong><u>Decoded response</u></strong><br>(S)TSN: <strong>' . $stsn
                        . '</strong> (manufactured between '
                        . $dateStart->format('M jS') . ' and '
                        . $dateEnd->format('M jS Y') . ', TWCID '
                        . substr($stsn, 7, 4) . ')</p>';
                }
                else if(substr($response, 0, 5) == "FD 1A") {
                    $serialHexAry = explode(' ', substr($response, 6, strlen($response) - 6 - 3));
                    $model = '';
                    foreach($serialHexAry as $value) {
                        $ascii = hexdec($value);
                        if($ascii > 0 && $ascii < 0xFF) {
                            $model .= chr($ascii);
                        }
                    }

                    print '<p><strong><u>Decoded response</u></strong><br>Model: <strong>'
                        . $model . '</strong></p>';
                }
                else if(substr($response, 0, 5) == "FD 1B") {
                    print '<p><strong><u>Decoded response</u></strong><br>Firmware version: <strong>'
                        . hexdec(substr($response, 6, 2)) . '.'
                        . hexdec(substr($response, 9, 2)) . '.'
                        . hexdec(substr($response, 12, 2)) . '</strong></p>';
                }
            }
            ?>
            <p>
                <a href="index.php?debugTWC=1">Main debug menu</a>
            </p>
            </body></html>
            <?php
            exit;
        }
        else if(array_key_exists('setMasterHeartbeatData', $_REQUEST)) {
            // This hidden option can be used to tell a TWC to set arbitrary
            // Master heartbeat data for debugging and experimentation.
            // To use, type a URL like this in your browser:
            // http://(Pi address)/index.php?submit=1&setMasterHeartbeatData=090600000000000000
            ipcCommand('setMasterHeartbeatData=' . preg_replace('/[ \r\n\t]/', '', $_REQUEST['setMasterHeartbeatData']));
            ?>
            <form action="index.php" method="get">
            Override Master heartbeat data: <input type="text" name="setMasterHeartbeatData" size="30" value="<?=htmlspecialchars($_REQUEST['setMasterHeartbeatData'])?>">
            <input type="submit" name="submit" value="Submit">
            </form>
            <p>
                <a href="index.php?setMasterHeartbeatData=&submit=1">Stop overriding</a>
                | <a href="index.php?setMasterHeartbeatData=05&submit=1">Charge 0A</a>
                | <a href="index.php?setMasterHeartbeatData=050258&submit=1">Charge 6A</a>
                | <a href="index.php?setMasterHeartbeatData=050834&submit=1">Charge 21A</a>
                | <a href="index.php?setMasterHeartbeatData=050FA0&submit=1">Charge 40A</a>
                | <a href="index.php?setMasterHeartbeatData=093200&submit=1">Charge 128A (buggy 0A)</a>
                | <a href="index.php?setMasterHeartbeatData=0201&submit=1">Error 1</a>
            </p>
            <p>
                <a href="index.php?debugTWC=1">Main debug menu</a>
            </p>
            <?php
            print '<script>document.title = "TWCHeartbeat";</script>';
            print '</body></html>';

            exit;
        }
        else if(@$_REQUEST['dumpState'] != '') {
            // This hidden option will display the state of a number of
            // variables used by TWCManager.
            // To use, type a URL like this in your browser:
            // http://(Pi address)/index.php?submit=1&dumpState=1
            ?>
            <form action="index.php" method="get">
            <p style="line-height:2;">
            <?=preg_replace('/\n/', '<br>', htmlspecialchars(ipcQuery('dumpState', true))) . '</p>'?>
            <input type="hidden" name="dumpState" value="1">
            <input type="submit" name="submit" value="Refresh">
            </form>
            <script>document.title = "TWCDump";</script>
            </body></html>
            <p>
                <a href="index.php?debugTWC=1">Main debug menu</a>
            </p>
            <?php
            exit;
        }
        else {
            if(@$_REQUEST['nonScheduledAmpsMax'] != '') {
                // Someone submitted the form asking to change the power limit, so
                // tell TWCManager.py script how many amps to limit charging to.
                // A limit of -1 means track green energy sources.
                ipcCommand('setNonScheduledAmps=' . $_REQUEST['nonScheduledAmpsMax']);
            }
            if(@$_REQUEST['scheduledAmpsMax'] != '') {
                $daysBitmap = 0;
                for($i = 0; $i < 7; $i++) {
                    if(@$_REQUEST['scheduledAmpsDay'][$i]) {
                        $daysBitmap |= (1 << $i);
                    }
                }
                ipcCommand('setScheduledAmps=' . $_REQUEST['scheduledAmpsMax']
                           . "\nstartTime=" . @$_REQUEST['scheduledAmpStartTime']
                           . "\nendTime=" . @$_REQUEST['scheduledAmpsEndTime']
                           . "\ndays=" . $daysBitmap);
            }
            if(@$_REQUEST['resumeTrackGreenEnergyTime'] != '') {
                ipcCommand('setResumeTrackGreenEnergyTime=' . $_REQUEST['resumeTrackGreenEnergyTime']);
            }

            if(preg_match('/^1-day charge/', $_REQUEST['submit'])) {
                ipcCommand('chargeNow');
            }
            else if($_REQUEST['submit'] == 'Cancel 1-day charge') {
                ipcCommand('chargeNowCancel');
            }
        }
    }
?>
<h1>Note</h1>

Thanks for using TWCManager, we hope you are finding this project useful.

<p>This web interface is scheduled for eventual deprecation. We retain it for the components that have not yet been migrated to the new web interface, and for backwards compatibility with other TWCManager forks.

<p>The defaults for the Web IPC Control Module have changed, disabling the module by default in v1.2.1. If you need to use the legacy web interface, please read the documentation <a href="https://github.com/ngardiner/TWCManager/blob/v1.2.1/docs/modules/Control_WebIPC.md">here</a> for details on what you need to configure.

<p>We strongly recommend using the <a href="https://github.com/ngardiner/TWCManager/blob/v1.2.1/docs/modules/Control_HTTP.md">New Web Interface</a>. Feature partiy in the new web interface is a high priority goal of v1.2.1.

<hr />

<form action="index.php" name="refresh" method="get">
    <table border="0" padding="0" margin="0"><tr>
        <td valign="top">
            <?php
                // TWC models in different world regions have different max amp values.
                // Default to 80 amps and expect to fix this value later based on what
                // slave TWCs connect to TWCManager.py.
                $twcModelMaxAmps = 80;

                $carApiEmailPasswordNeeded = 0;

                // Get status info from TWCManager.py which includes state of each slave
                // TWC and how many amps total are being split amongst them.
                $response = ipcQuery('getStatus');
                if($debugLevel >= 1) {
                    print("Got response: '$response'<p>");
                }

                if($response != '') {
                    $status = explode('`', $response);
                    $statusIdx = 0;
                    $maxAmpsToDivideAmongSlaves = $status[$statusIdx++];
                    $wiringMaxAmpsAllTWCs = $status[$statusIdx++];
                    $minAmpsPerTWC = $status[$statusIdx++];
                    $chargeNowAmps = $status[$statusIdx++];
                    $GLOBALS['nonScheduledAmpsMax'] = $status[$statusIdx++];
                    $GLOBALS['scheduledAmpsMax'] = $status[$statusIdx++];
                    $GLOBALS['scheduledAmpStartTime'] = $status[$statusIdx++];
                    $GLOBALS['scheduledAmpsEndTime'] = $status[$statusIdx++];
                    $scheduledAmpsDaysBitmap = $status[$statusIdx++];
                    for($i = 0; $i < 7; $i++) {
                        if($scheduledAmpsDaysBitmap & (1 << $i)) {
                            $GLOBALS["scheduledAmpsDay[$i]"] = 1;
                        }
                    }

                    $GLOBALS['resumeTrackGreenEnergyTime'] = $status[$statusIdx++];

                    print "<p style=\"margin-top:0;\"><strong>Power available for all TWCs:</strong> ";
                    if($maxAmpsToDivideAmongSlaves > 0) {
                          print $maxAmpsToDivideAmongSlaves . "A";
                    }
                    else {
                        print "None";
                    }

                    $carApiEmailPasswordNeeded = $status[$statusIdx++];

                    if($status[$statusIdx] < 1) {
                        print "</p><p style=\"margin-bottom:0\">";
                        print "<strong>No slave TWCs found on RS485 network.</strong>";
                    }
                    else {
                        // Display info about each TWC being managed.
                        $numTWCs = $status[$statusIdx++];
                        for($i = 0; $i < $numTWCs; $i++) {
                            print "</p><p style=\"margin-bottom:0\">";
                            $subStatus = explode('~', $status[$statusIdx++]);
                            $twcModelMaxAmps = $subStatus[1];
                            print("<strong>TWC " . $subStatus[0] . ':</strong> ');
                            if($subStatus[2] < 1.0) {
                                /*if($subStatus[4] == 0) {
                                    // I was hoping state 0 meant no car is plugged in, but
                                    // there are periods when we're telling the car no power is
                                    // available and the state flips between 5 and 0 every
                                    // second. Sometimes it changes to state 0 for long periods
                                    // (likely when the car goes to sleep for ~15 mins at a
                                    // time) even when the car is plugged in, so it looks like
                                    // we can't actually determine if a car is plugged in or
                                    // not.
                                    print "No car plugged in.";
                                }
                                else {*/
                                if($subStatus[3] < 5.0) {
                                    if($maxAmpsToDivideAmongSlaves > 0 &&
                                       $maxAmpsToDivideAmongSlaves < $minAmpsPerTWC) {
                                        print "Power available less than {$minAmpsPerTWC}A (minAmpsPerTWC).";
                                    }
                                    else {
                                        print "No power available.";
                                    }
                                }
                                else {
                                    print "Finished charging, unplugged, or waking up."
                                        . " (" . $subStatus[3] . "A available)";
                                }
                            }
                            else {
                                print "Charging at " . $subStatus[2] . "A.";
                                if($subStatus[3] - $subStatus[2] > 1.0) {
                                    // Car is using over 1A less than is available, so print
                                    // a note.
                                    print " (" . $subStatus[3] . "A available)";
                                }
                            }
                        }
                    }
                    print "</p>";
                }

                if($twcModelMaxAmps < 40) {
                    $use24HourTime = true;
                    $aryStandardAmps = array();
                    for ($i = 6; $i <= 32; $i++) {
                        $aryStandardAmps[strval($i).'A'] = strval($i);
                    }
                }
                else {
                    // Offer values appropriate for an 80A North American TWC
                    $use24HourTime = false;
                    $aryStandardAmps = array(
                                            '6A' => '6',
                                            '8A' => '8',
                                            '12A' => '12',
                                            '16A' => '16',
                                            '20A' => '20',
                                            '24A' => '24',
                                            '28A' => '28',
                                            '32A' => '32',
                                            '36A' => '36',
                                            '40A' => '40',
                                            '48A' => '48',
                                            '56A' => '56',
                                            '64A' => '64',
                                            '72A' => '72',
                                            '80A' => '80',
                                        );
                }

                // Remove amp values higher than the value of
                // $wiringMaxAmpsAllTWCs or lower than $minAmpsPerTWC set in
                // TWCManager.py.
                foreach($aryStandardAmps as $key => $value) {
                    if($value > $wiringMaxAmpsAllTWCs || $value < $minAmpsPerTWC) {
                        unset($aryStandardAmps[$key]);
                    }
                }

                $aryHours = array();
                for($hour = 0; $hour < 12; $hour++) {
                    if($use24HourTime) {
                        $aryHours[sprintf("%02d:00", $hour)] = sprintf("%02d:00", $hour);
                    }
                    else {
                        $aryHours[sprintf("%d:00am", ($hour < 1 ? $hour + 12 : $hour))] = sprintf("%02d:00", $hour);
                    }
                }
                for($hour = 12; $hour < 24; $hour++) {
                    if($use24HourTime) {
                        $aryHours[sprintf("%02d:00", $hour)] = sprintf("%02d:00", $hour);
                    }
                    else {
                        $aryHours[sprintf("%d:00pm", ($hour > 12 ? $hour - 12 : $hour))] = sprintf("%02d:00", $hour);
                    }
                }
            ?>
        </td>
        <td valign="middle">
            <input type="image" alt="Refresh" src="refresh.png" style="margin-left:1em">
        </td>
    </tr></table>
    </form>
</div>
<br />
<div style="display: inline-block; text-align:right;">
    <form action="index.php" name="setAmps" method="get">
        <p style="margin-bottom:0;">
            <strong>Scheduled power:</strong>
            <?php
            DisplaySelect('scheduledAmpsMax',
                          " onchange=\"if(this.value=='-1'){document.getElementById('scheduledPower').style.display='none'}"
                        . "else {document.getElementById('scheduledPower').style.display='block'};\"",
                          array_merge(array('Disabled' => '-1'), $aryStandardAmps));
            ?>
        </p>
        <div id="scheduledPower">
            <p style="margin-top:0.3em; margin-bottom:0; padding-top:0;">
                <strong>from</strong>
                <?php
                DisplaySelect('scheduledAmpStartTime', '', $aryHours);
                ?>
                <strong>to</strong>
                <?php
                DisplaySelect('scheduledAmpsEndTime', '', $aryHours);
                ?>
            </p>
            <p style="margin-top:0.3em; margin-bottom:0; padding-top:0;">
                <strong>on days</strong>
                <?php DisplayCheckbox("scheduledAmpsDay[6]", '', '1') ?>Su
                <?php DisplayCheckbox("scheduledAmpsDay[0]", '', '1') ?>Mo
                <?php DisplayCheckbox("scheduledAmpsDay[1]", '', '1') ?>Tu
                <?php DisplayCheckbox("scheduledAmpsDay[2]", '', '1') ?>We
                <?php DisplayCheckbox("scheduledAmpsDay[3]", '', '1') ?>Th
                <?php DisplayCheckbox("scheduledAmpsDay[4]", '', '1') ?>Fr
                <?php DisplayCheckbox("scheduledAmpsDay[5]", '', '1') ?>Sa
            </p>
        </div>

        <p style="margin-bottom:0; margin-top:1.8em;">
            <strong>Non-scheduled power:</strong>
            <?php
                DisplaySelect('nonScheduledAmpsMax',
                              " onchange=\"if(this.value=='-1'){document.getElementById('resumeGreen').style.display='none'}"
                            . "else {document.getElementById('resumeGreen').style.display='block'};\"",
                              array_merge(array('Do not charge' => '0'),
                                          $aryStandardAmps));
            ?>
        </p>
        <p id="resumeGreen" style="margin-top:0.3em">
            <strong>Resume 'Track green energy' at:</strong>
            <?php
            DisplaySelect('resumeTrackGreenEnergyTime', '', array_merge(array('Never' => '23:59'),
                                                                             $aryHours));
            ?>
        </p>

        <p style="margin-top:1.8em; text-align:right;">
            <?php
            if($chargeNowAmps > 0) {
                print '<input type="submit" name="submit" value="Cancel 1-day charge">';
            }
            else {
                print '<input type="submit" name="submit" value="1-day charge, '
                    . sprintf("%.0f", $wiringMaxAmpsAllTWCs) . 'A">';
            }
            ?>
            <input type="submit" name="submit" value="Save">
        </p>
    </form>
    <?php
        if($carApiEmailPasswordNeeded) {
            ?>
            <form action="index.php" method="get">
                <p>
                    Enter your email and password to allow TWCManager to start and
                    stop Tesla vehicles you own from charging.  These credentials are
                    sent once to Tesla and are not stored.  Credentials must be entered
                    again if no cars are connected to this charger for over 45 days.
                </p>
                <p>
                <?php
                if(@$_REQUEST['email'] != '' || @$_REQUEST['password'] != '') {
                    // An email or password were entered, but not authorized
                    // by car API, so presumably they were wrong.
                    print '<p style="color:#bb0000; font-weight:bold;">Incorrect email or password.</p>';
                }
                ?>
                Email: <input type="text" name="email" value="<?php print htmlspecialchars(@$_REQUEST['email'])?>"><br>
                Password: <input type="password" name="password"><br>
                <input type="submit" name="submit" value="Submit">
                </p>
            </form>
            <?php
        }
    ?>
</div>

<script type="text/javascript">
    <!--
    document.getElementById('resumeGreen').style.display='<?=
    ($GLOBALS['nonScheduledAmpsMax'] == -1 ? 'none' : 'block') ?>';

    document.getElementById('scheduledPower').style.display='<?=
    ($GLOBALS['scheduledAmpsMax'] == -1 ? 'none' : 'block') ?>';
    -->
</script>

<?php
    function ipcCommand($ipcCommand)
    // Send an IPC command to TWCManager.py.  A command does not expect a
    // response.
    {
        global $ipcQueue, $debugLevel;
        $ipcErrorCode = 0;
        $ipcMsgID = 0;
        $ipcMsgTime = time();

        ipcSend($ipcMsgTime, $ipcMsgID, $ipcCommand);
    }

    function ipcQuery($ipcMsgSend, $usePackets = false)
    // Send an IPC query to TWCManager.py and wait for a response which we
    // return.
    {
        global $ipcQueue, $debugLevel;
        $ipcErrorCode = 0;

        // There could be multiple web pages or other interfaces sending queries
        // to TWCManager.py.  To help ensure we get back the response to our
        // particular query, assign a random ID to our query and only accept
        // responses containing the same ID.
        $ipcMsgID = rand(1,65535);

        // Also add a timestamp to our query.  Messages unprocessed for too long
        // will be discarded.
        $ipcMsgTime = time();

        // Send our query
        if(ipcSend($ipcMsgTime, $ipcMsgID, $ipcMsgSend) == false) {
            return '';
        }

        // Wait up to 5 seconds for a response.
        $ipcMsgType = 0;
        $ipcMsgRecv = '';
        $ipcMaxMsgSize = 300;
        $i = 0;
        $maxRetries = 50;
        $numPackets = 0;
        $msgResult = '';
        for(; $i < $maxRetries; $i++) {
            // MSG_NOERROR flag prevents showing an error if there are too many
            // characters and some were lost.
            if(msg_receive($ipcQueue, 1, $ipcMsgType, $ipcMaxMsgSize, $ipcMsgRecv, false,
                           MSG_IPC_NOWAIT | MSG_NOERROR, $ipcErrorCode) == false
            ) {
                // Error 42 means no response is available yet, which is likely to happen
                // briefly.
                if($ipcErrorCode != 42) {
                    print("Message receive failed with error code $ipcErrorCode<br>");
                }
            }
            else {
                $aryMsg = unpack("Ltime/SID/a*msg", $ipcMsgRecv);
                if($debugLevel >= 10) {
                   print "ipcQuery received '" . $aryMsg['msg'] . "', id " . $aryMsg['ID']
                           . ", time " . $aryMsg['time'] . "<p>";
                }

                if($aryMsg['ID'] == $ipcMsgID) {
                    // This response matches our message ID
                    if($usePackets) {
                        if($numPackets == 0) {
                            $numPackets = ord($aryMsg['msg']);
                            if($debugLevel >= 10) {
                                print "ipcQuery numPackets $numPackets<p>";
                            }
                        }
                        else {
                            $msgResult .= $aryMsg['msg'];
                            $numPackets--;
                            if($numPackets == 0) {
                                return $msgResult;
                            }
                        }
                        continue;
                    }
                    else {
                        return $aryMsg['msg'];
                    }
                }
                if(time() - $aryMsg['time'] < 30) {
                    // Message ID doesn't match the ID of our query so this
                    // isn't a response to our query. However, this message is
                    // less than 30 seconds old so another process may still be
                    // waiting for it. Therefore, we put it back at the end of
                    // the message queue.
                    if($debugLevel >= 10) {
                        print "ipcQuery: Put unexpired message back at end of queue.<br>";
                    }
                    ipcSend($aryMsg['time'], $aryMsg['ID'], $aryMsg['msg'], 1);
                }
            }

            // Sleep 1/10 of a second, then check again for a response.
            usleep(100000);
        }

        if($i >= $maxRetries) {
            print "<span style=\"color:#F00; font-weight:bold;\">"
                . "Timed out waiting for response from TWCManager script.</span><p>"
                . "If the script is running, make sure the \$twcScriptDir parameter "
                . "in the source of this web page points to the directory containing "
                . "the TWCManager script.</p><p>";
        }
        return '';
    }

    function ipcSend($ipcMsgTime, $ipcMsgID, $ipcMsg, $ipcMsgType = 2)
    // Help ipcCommand or ipcQuery send their IPC message. Don't call this
    // directly.
    // Most messages we send to TWCManager.py will use $ipcMsgType = 2 while
    // responses to queries will use $ipcMsgType = 1. I picked those values
    // thinking I might use type 1 for responses to queries and values 2 and
    // higher to distinguish different commands or queries but decided to use
    // clear English messages.
    {
        global $ipcQueue, $debugLevel;

        if($debugLevel >= 10) {
            if($debugLevel >= 10) {
                print "ipcQuery sending '" . $ipcMsg . "', id " . $ipcMsgID
                        . ", time " . $ipcMsgTime . "<p>";
            }

            if($debugLevel >= 11) {
                // Print binary bytes in the message if debugging requires.
                print "ipcSend binary message of length " . strlen($ipcMsgSend) . ': ';
                for($i = 0; $i < strlen($ipcMsgSend); $i++) {
                    printf("%02x ", ord(substr($ipcMsgSend, $i, 1)));
                }
                print("<p>");
            }
        }

        if(msg_send($ipcQueue, $ipcMsgType, pack("LSa*", $ipcMsgTime, $ipcMsgID, $ipcMsg),
                    false, false, $ipcErrorCode) == false
        ) {
            print("Couldn't send '$ipcMsgSend'.  Error code $ipcErrorcode.<br><br>");
            return false;
        }
        return true;
    }


    function DisplaySelect($name, $selectExtraParams, $valueArray, $defaultKey = "")
    // Display an HTML form <select><option>...</option></select> block using
    // values from $valueArray.
    {
        print "<SELECT name=\"$name\"" . $selectExtraParams . " id=\"$name\">\n";
        foreach($valueArray as $key => $value) {
            print "<OPTION value=\"$value\"";
            // Use === and string casting or else "0" == "" will be found true
            if(((string)$GLOBALS[$name]) === ((string)$value) ||
                ( ((string)$GLOBALS[$name]) === "" && $key === $defaultKey )) {
                print " selected";
            }
            print " autocomplete=\"off\">$key</OPTION>\n";
        }
        print "</SELECT>\n";
    }

    function DisplayCheckbox($name, $extraParams, $value)
    {
        print '<INPUT type="checkbox" name="' . $name . '" value="' . $value . '"';
        if( ((string)$GLOBALS[$name]) === ((string)$value) ) {
            print " checked";
        }
        if($extraParams != '') {
            print $extraParams;
        }
        print '>';
    }
?>
</body>
</html>
