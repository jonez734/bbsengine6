<?php 
 /* 
  * Smarty plugin "LinkUrl" 
  * Purpose: links URLs und shortens it to a specific length 
  * Home: http://www.cerdmann.com/linkurl/ 
  * Copyright (C) 2005 Christoph Erdmann 
  * 
  * This library is free software; you can redistribute it and/or modify it under the terms of the GNU Lesser General Public License as published by the Free Software Foundation; either version 2.1 of the License, or (at your option) any later version. 
  * 
  * This library is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details. 
  * 
  * You should have received a copy of the GNU Lesser General Public License along with this library; if not, write to the Free Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110, USA 
  * ------------------------------------------------------------- 
  * Author:   Christoph Erdmann (CE) 
  * Internet: http://www.cerdmann.com 
 
  * Author:   Daniel Cummings (DC) 
  * 
  * Changelog: 
  * 2006-03-01 fixed POST javascript for IE (DC) 
  * 2006-02-27 fixed POST link style to handle multiple URLs properly (DC) 
  * 2006-02-23 added https support 
  *            changed link param to allow none, simple, get, post (DC) 
  * 2004-11-24 New parameter allows truncation without linking the URL (CE) 
  * 2004-11-20 In braces enclosed URLs are now better recognized (CE) 
  * 
  *  EXAMPLES: 
  * {$urls|linkurl} {* defaults to 50, SIMPLE direct link to original URL *} 
  * {$urls|linkurl:"25"} {* change the length of the displayed URL link *} 
  * {$urls|linkurl:"25":"NONE"} {* remove live link but still show clipped URL *} 
  * {$urls|linkurl:"25":"GET":"url.php?url="} {* redirect URL via GET *} 
  * {$urls|linkurl:"25":"POST":"url.php"} {* redirect via POST *} 
  * ------------------------------------------------------------- 
  */ 
 
 function smarty_modifier_linkurl($string, $length=50, $link="SIMPLE", $redir="url.php") 
    { 
    if (!function_exists('kuerzen')) { 
    function kuerzen($string,$length) 
       { 
       $returner = $string; 
       if (strlen($returner) > $length) 
          { 
          $url = preg_match("=[^/]/[^/]=",$returner,$treffer,PREG_OFFSET_CAPTURE); 
          $cutpos = $treffer[0][1]+2; 
          $part[0] = substr($returner,0,$cutpos); 
          $part[1] = substr($returner,$cutpos); 
 
          $strlen1 = $cutpos; 
          if ($strlen1 > $length) return substr($returner,0,$length-3).'...'; 
          $strlen2 = strlen($part[1]); 
          $cutpos = $strlen2-($length-3-$strlen1); 
          $returner = $part[0].'...'.substr($part[1],$cutpos); 
          } 
       return $returner; 
       } 
    } 
     
    // strtoupper() casts TRUE to string "1" and FALSE to string '' (empty) 
    // this line lets us maintain backwards compatibility and is handled in the switch 
    $link=strtoupper($link); 
    $pattern = '#(^|[^\"=]{1})(https?://|ftp://|www\.)([^\s<>\)]+)([\s\n<>\)]|$)#smei'; 
     
    switch (TRUE) 
       { 
       case ($link === "NONE" OR $link === ''): // just show the URL truncated 
          $string = preg_replace($pattern,"kuerzen('$2$3',$length)",$string); 
          break; 
       case ($link === "SIMPLE" OR $link === '1'): // builds basic a href link showing truncated URL 
//          $string = preg_replace($pattern,"'$1<a href=\"$2$3\" title=\"$2$3\" target=\"_blank\" rel=\"nofollow\">'.kuerzen('$2$3',$length).'</a>$4'",$string); 
          $string = preg_replace($pattern,"'$1<a href=\"$2$3\" title=\"$2$3\" rel=\"nofollow\">'.kuerzen('$2$3',$length).'</a>$4'",$string); 
             $string = str_ireplace("href=\"www.","href=\"http://www.",$string); 
          break; 
       case ($link === "GET"): // allows passing url to a redirecting file via GET - use redir param with format "url.php?url=" 
//          $string = preg_replace($pattern,"'$1<a href=\"$redir$2$3\" title=\"$2$3\" target=\"_blank\" rel=\"nofollow\">'.kuerzen('$2$3',$length).'</a>$4'",$string); 
          $string = preg_replace($pattern,"'$1<a href=\"$redir$2$3\" title=\"$2$3\" rel=\"nofollow\">'.kuerzen('$2$3',$length).'</a>$4'",$string); 
             $string = str_ireplace("href=\"" . $redir . "www.","href=\"" . $redir . "http://www.",$string); 
          break; 
       case ($link === "POST"): // send URL via POST (builds form and embeds javascript submit script in link) - use redir param with format "url.php" 
          // here we use preg_match_all() to be able to 
          // build multiple forms (since each form needs 
          // a unique name) 
          preg_match_all($pattern,$string,$matches,PREG_SET_ORDER); 
          foreach ($matches as $key=>$ul) { 
             // use the key as the unique formname 
             $form = "<form name=\"sub$key\" method=\"post\" action=\"$redir\"><input type=\"hidden\" id=\"up\" name=\"up\" value=\"$ul[2]$ul[3]\"></FORM>"; 
//             $string_new .= "$form $ul[1]<a href=\"javascript:void(0)\" onclick=\"document.sub$key.submit(); return false;\" target=\"_blank\" rel=\"nofollow\">" . kuerzen("$ul[2]$ul[3]",$length)."</a>$ul[4]"; 
             $string_new .= "$form $ul[1]<a href=\"javascript:void(0)\" onclick=\"document.sub$key.submit(); return false;\" rel=\"nofollow\">" . kuerzen("$ul[2]$ul[3]",$length)."</a>$ul[4]"; 
          } 
          $string = $string_new; 
             $string = str_ireplace("value=\"www.","value=\"http://www.",$string); 
          break; 
       } 
    return $string; 
    } 
 
 ?>
