<?php

/**
 * Smarty plugin
 * @package Smarty
 * @subpackage plugins
 */


/**
 * Smarty date modifier plugin
 * Purpose:  converts unix timestamps or datetime strings to words for future dates
 * Type:     modifier<br>
 * Name:     fromnow<br>
 * @author   Stephan Otto
 * @param string
 * @return string
 * @since 20120809
 * 
 * 2012-aug-09: jam changed the coding style, renamed the modifier to be named 'ago' and changed timeStrings from .de to .us
 * shamelessly ripped from http://www.smarty.net/forums/viewtopic.php?p=61841
 *
 */
function smarty_modifier_fromnow($date)
{
    $timeStrings = array("a few seconds from now",            // 0       <- now or future posts :-)
                        "second", "seconds",    // 1,1
                        "minute", "minutes",      // 3,3
                        "hour", "hours",   // 5,5
                        "day", "days",         // 7,7
                        "week", "weeks",      // 9,9
                        "month", "months",      // 11,12
                        "year", "years");      // 13,14

    $sec = $date - time();

    if ($sec <= 0) return $timeStrings[0];
    
    if ($sec < 2) return $sec." ".$timeStrings[1];
    if ($sec < 60) return $sec." ".$timeStrings[2];
    
    $min = $sec / 60;
    if (floor($min+0.5) < 2) return floor($min+0.5)." ".$timeStrings[3];
    if ($min < 60) return floor($min+0.5)." ".$timeStrings[4];
    
    $hrs = $min / 60;
    if (floor($hrs+0.5) < 2) return floor($hrs+0.5)." ".$timeStrings[5];
    if ($hrs < 24) return floor($hrs+0.5)." ".$timeStrings[6];
    
    $days = $hrs / 24;
    if (floor($days+0.5) < 2) return floor($days+0.5)." ".$timeStrings[7];
    if ($days < 7) return floor($days+0.5)." ".$timeStrings[8];
    
    $weeks = $days / 7;
    if (floor($weeks+0.5) < 2) return floor($weeks+0.5)." ".$timeStrings[9];
    if ($weeks < 4) return floor($weeks+0.5)." ".$timeStrings[10];
    
    $months = $weeks / 4;
    if (floor($months+0.5) < 2) return floor($months+0.5)." ".$timeStrings[11];
    if ($months < 12) return floor($months+0.5)." ".$timeStrings[12];
    
    $years = $weeks / 51;
    if (floor($years+0.5) < 2) return floor($years+0.5)." ".$timeStrings[13];
    return floor($years+0.5)." ".$timeStrings[14];
}

?>
