<?php
    ///////////////////////////////////////////////////////////////////////////
    // Configuration parameters

    // Choose how much debugging info to output.
    // 0 is no output other than errors.
    // 1 is just the most useful info.
    // 10 is all info.
    $debugLevel = 0;

    // Point $twcScriptDir to the directory containing the TWCManager.pl script.
    // Interprocess Communication with TWCManager.pl will not work if this
    // parameter is incorrect.
    $twcScriptDir = "/home/pi/TWC/";

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
    // TWCManager.pl script and getting data back.  See notes in TWCManager.pl for
    // how IPC works.
    $ipcKey = ftok($twcScriptDir, "T");
    $ipcQueue = msg_get_queue($ipcKey, 0666);

    if(@$_REQUEST['submit'] != '') {
        if(@$_REQUEST['nonScheduledAmpsMax'] != '') {
            // Someone submitted the form asking to change the power limit, so
            // tell TWCManager.pl script how many amps to limit charging to.
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
        if(@$_REQUEST['sendTWCMsg'] != '') {
            // This hidden option can be used to tell a TWC to send an arbitrary
            // message on the RS-485 network for debugging and experimentation.
            // To use, type a URL like this in your browser:
            // http://(Pi Zero address)/index.php?submit=1&sendTWCMsg=FBEB7777032E000000000000000000
            // This will send message FBEB7777032E000000000000000000.  Message
            // start, CRC, and end bytes are added automatically.
            ipcCommand('sendTWCMsg=' . $_REQUEST['sendTWCMsg']);
        }
    }
?>
<form action="index.php" name="refresh" method="get">
    <table border="0" padding="0" margin="0"><tr>
        <td valign="top">
            <?php
                // TWC models in different world regions have different max amp values.
                // Default to 80 amps and expect to fix this value later based on what
                // slave TWCs connect to TWCManager.pl.
                $twcModelMaxAmps = 80;

                // Get status info from TWCManager.pl which includes state of each slave
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
                    print "</p><p style=\"margin-bottom:0\">";

                    if($status[$statusIdx] < 1) {
                        print "<strong>No slave TWCs found on RS485 network.</strong>";
                    }

                    // Display info about each TWC being managed.
                    for($i = 0; $i < $status[$statusIdx]; $i++) {
                        $subStatus = explode('~', $status[$statusIdx + 1]);
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
                                print "No power available.";
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
                    print "</p>";
                }

                if($twcModelMaxAmps < 40) {
                    // The last TWC in the list reported supporting under 40 total amps.
                    // Assume this is a 32A EU TWC and offer appropriate values.  You can
                    // add or remove values, just make sure they are whole numbers between 5
                    // and $twcModelMaxAmps.
                    $use24HourTime = true;
                    $aryStandardAmps = array(
                                            '5A' => '5',
                                            '6A' => '8',
                                            '8A' => '8',
                                            '10A' => '10',
                                            '13A' => '13',
                                            '16A' => '16',
                                            '20A' => '20',
                                            '25A' => '25',
                                            '32A' => '32',
                                        );
                }
                else {
                    // Offer values appropriate for an 80A North American TWC
                    $use24HourTime = false;
                    $aryStandardAmps = array(
                                            '5A' => '5',
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
                // $wiringMaxAmpsAllTWCs set in TWCManager.pl.
                foreach($aryStandardAmps as $key => $value) {
                    if($value > $wiringMaxAmpsAllTWCs) {
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
                <?php DisplayCheckbox("scheduledAmpsDay[0]", '', '1') ?>Su
                <?php DisplayCheckbox("scheduledAmpsDay[1]", '', '1') ?>Mo
                <?php DisplayCheckbox("scheduledAmpsDay[2]", '', '1') ?>Tu
                <?php DisplayCheckbox("scheduledAmpsDay[3]", '', '1') ?>We
                <?php DisplayCheckbox("scheduledAmpsDay[4]", '', '1') ?>Th
                <?php DisplayCheckbox("scheduledAmpsDay[5]", '', '1') ?>Fr
                <?php DisplayCheckbox("scheduledAmpsDay[6]", '', '1') ?>Sa
            </p>
        </div>

        <p style="margin-bottom:0; margin-top:1.8em;">
            <strong>Non-scheduled power:</strong>
            <?php
                DisplaySelect('nonScheduledAmpsMax',
                              " onchange=\"if(this.value=='-1'){document.getElementById('resumeGreen').style.display='none'}"
                            . "else {document.getElementById('resumeGreen').style.display='block'};\"",
                              array_merge(array('Track green energy' => '-1',
                                                'Do not charge' => '0'),
                                          $aryStandardAmps));
            ?>
        </p>
        <p id="resumeGreen" style="margin-top:0.3em">
            <strong>Resume 'Track green energy' at:</strong>
            <?php
            DisplaySelect('resumeTrackGreenEnergyTime', '', array_merge(array('Never' => '-1:00'),
                                                                             $aryHours));
            ?>
        </p>

        <p style="margin-top:1.8em; text-align:right;">
            <input type="submit" name="submit" value="Save">
        </p>
    </form>
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
    // Send an IPC command to TWCManager.pl.  A command does not expect a
    // response.
    {
        global $ipcQueue, $debugLevel;
        $ipcErrorCode = 0;
        $ipcMsgID = 0;
        $ipcMsgTime = time();

        ipcSend($ipcMsgTime, $ipcMsgID, $ipcCommand);
    }

    function ipcQuery($ipcMsgSend)
    // Send an IPC query to TWCManager.pl and wait for a response which we
    // return.
    {
        global $ipcQueue, $debugLevel;
        $ipcErrorCode = 0;

        // There could be multiple web pages or other interfaces sending queries
        // to TWCManager.pl.  To help ensure we get back the response to our
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
        for(; $i < $maxRetries; $i++) {
            if(msg_receive($ipcQueue, 1, $ipcMsgType, $ipcMaxMsgSize, $ipcMsgRecv, false, MSG_IPC_NOWAIT, $ipcErrorCode) == false) {
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
                    // This response matches our message ID, so return the
                    // response.
                    return $aryMsg['msg'];
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
    // Most messages we send to TWCManager.pl will use $ipcMsgType = 2 while
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