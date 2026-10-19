<?php

/**
 * Smarty plugin
 * @package bbsengine4
 * @subpackage plugins
 */


/**
 * Smarty date modifier plugin
 * Purpose:  converts unix timestamps or datetime strings to words
 * Type:     modifier<br>
 * Name:     timeAgo<br>
 * @author   Stephan Otto
 * @param unixtimestamp
 * @param text format (optional)
 * @return string
 * @since 20120809
 * 
 * 2012-aug-09: jam changed the coding style, renamed the modifier to be named 'ago' and changed timeStrings from .de to .us
 * shamelessly ripped from http://www.smarty.net/forums/viewtopic.php?p=61841
 *
 * @param bool $terse  when true, return compact output such as "1d6h2m" or "3mo"
 *                     instead of "1 day, 6 hours, 2 minutes" style phrases
 *
 */
function smarty_modifier_ago($unixtimestamp, $terse = false)
{
       $seconds = time() - $unixtimestamp;

       if ($terse) {
             return smarty_modifier_ago_terse($seconds);
       }

       $timeStrings = array("a few seconds",            // 0       <- now or future posts :-)
                        "second", "seconds",    // 1,1
                        "minute", "minutes",      // 3,3
                        "hour", "hours",   // 5,5
                        "day", "days",         // 7,7
                        "week", "weeks",      // 9,9
                        "month", "months",      // 11,12
                        "year", "years");      // 13,14

            if ($seconds < 1)
            {
                  $seconds = 0;
            }
            
            if ( $seconds <= 0) return $timeStrings[0];
            
            if ( $seconds < 2) return $seconds." ".$timeStrings[1];
            if ( $seconds < 60) return round($seconds,0)." ".$timeStrings[2];
            
            $min = $seconds / 60;
            if ( floor($min+0.5) < 2) return floor($min+0.5)." ".$timeStrings[3];
            if ( $min < 60) return floor($min+0.5)." ".$timeStrings[4];
            
            $hrs = $min / 60;
            if ( floor($hrs+0.5) < 2) return floor($hrs+0.5)." ".$timeStrings[5];
            if ( $hrs < 24) return floor($hrs+0.5)." ".$timeStrings[6];

            $days = $hrs / 24;
            if ( floor($days+0.5) < 2) return floor($days+0.5)." ".$timeStrings[7];
            if ( $days < 7) return floor($days+0.5)." ".$timeStrings[8];

            $weeks = $days / 7;
            if ( floor($weeks+0.5) < 2) return floor($weeks+0.5)." ".$timeStrings[9];
            if ( $weeks < 4) return floor($weeks+0.5)." ".$timeStrings[10];
            
            $months = $weeks / 4;
            if ( floor($months+0.5) < 2) return floor($months+0.5)." ".$timeStrings[11];
            if ( $months < 12) return floor($months+0.5)." ".$timeStrings[12];
            
            $years = $weeks / 51;
            if ( floor($years+0.5) < 2) return floor($years+0.5)." ".$timeStrings[13];
            return floor($years+0.5)." ".$timeStrings[14];
}


/**
 * Terse form of smarty_modifier_ago().
 *
 * Under 30 days: exact compound, largest unit first, down to minutes
 * (seconds only when the span is under one minute), e.g. "1d6h2m".
 * Truncates remainders. 30 days and up: one rounded unit, "3mo", "2y".
 *
 * Units: s, m (minutes), h, d, mo (30-day months), y (365-day years).
 *
 * @param int $seconds  elapsed seconds (may be negative for future times)
 * @return string
 */
function smarty_modifier_ago_terse($seconds)
{
       if ($seconds < 1) return "now";

       if ($seconds < 60) return (int)$seconds . "s";

       $minute = 60;
       $hour   = 60 * $minute;
       $day    = 24 * $hour;
       $month  = 30 * $day;
       $year   = 365 * $day;

       if ($seconds >= $month) {
             $months = floor($seconds / $month + 0.5);
             if ($months < 12) return $months . "mo";
             return floor($seconds / $year + 0.5) . "y";
       }

       $parts = "";
       $d = intdiv($seconds, $day);
       $h = intdiv($seconds % $day, $hour);
       $m = intdiv($seconds % $hour, $minute);
       if ($d) $parts .= $d . "d";
       if ($h) $parts .= $h . "h";
       if ($m) $parts .= $m . "m";
       return $parts;
}


?>
