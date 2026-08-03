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
  * You should have received a copy of the GNU Lesser General Public License along with this library; if not, write to the Free Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301 USA
  * -------------------------------------------------------------
  * Author:   Christoph Erdmann (CE)
  * Internet: http://www.cerdmann.com
  *
  * Author:   Daniel Cummings (DC)
  *
  * Changelog:
  * 2026-08-02 rewrite: replaced deprecated preg_replace /e with preg_replace_callback
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

 function kuerzen($string, $length)
 {
   $returner = $string;
   if (strlen($returner) > $length)
   {
     $treffer = [];
     preg_match("=[^/]/[^/]=", $returner, $treffer, PREG_OFFSET_CAPTURE);
     $cutpos = isset($treffer[0]) ? $treffer[0][1] + 2 : strlen($returner);
     $part[0] = substr($returner, 0, $cutpos);
     $part[1] = substr($returner, $cutpos);

     $strlen1 = $cutpos;
     if ($strlen1 > $length) return substr($returner, 0, max(0, $length - 3)) . '...';
     $strlen2 = strlen($part[1]);
     $cutpos = max(0, $strlen2 - ($length - 3 - $strlen1));
     $returner = $part[0] . '...' . substr($part[1], $cutpos);
   }
   return $returner;
 }

 function smarty_modifier_linkurl($string, $length = 50, $link = "SIMPLE", $redir = "url.php")
 {
   if (!is_string($string)) {
     return '';
   }
   $length = (int)$length;
   if ($length < 1) {
     $length = 1;
   }
   if ($length > 5000) {
     $length = 5000;
   }
   if (!is_string($redir)) {
     $redir = "url.php";
   }

   $link = strtoupper((string)$link);
   $pattern = '#(^|[^"=]{1})(https?://|ftp://|www\.)([^\s<>\)]+)([\s\n<>\)]|$)#smi';

   switch (TRUE)
   {
     case ($link === "NONE" || $link === ''):
       $string = preg_replace_callback($pattern, function($m) use ($length) {
         return kuerzen($m[2] . $m[3], $length);
       }, $string);
       break;
     case ($link === "SIMPLE" || $link === '1'):
       $string = preg_replace_callback($pattern, function($m) use ($length) {
         $url = $m[2] . $m[3];
         $display = kuerzen($url, $length);
         $title = htmlspecialchars($url, ENT_QUOTES, 'UTF-8');
         return $m[1] . '<a href="' . $title . '" title="' . $title . '" rel="nofollow">' . htmlspecialchars($display, ENT_QUOTES, 'UTF-8') . '</a>' . $m[4];
       }, $string);
       $string = str_ireplace('href="www.', 'href="http://www.', $string);
       break;
     case ($link === "GET"):
       $string = preg_replace_callback($pattern, function($m) use ($length, $redir) {
         $url = $m[2] . $m[3];
         $display = kuerzen($url, $length);
         $title = htmlspecialchars($url, ENT_QUOTES, 'UTF-8');
         return $m[1] . '<a href="' . htmlspecialchars($redir, ENT_QUOTES, 'UTF-8') . $title . '" title="' . $title . '" rel="nofollow">' . htmlspecialchars($display, ENT_QUOTES, 'UTF-8') . '</a>' . $m[4];
       }, $string);
       $string = str_ireplace('href="' . $redir . 'www.', 'href="' . $redir . 'http://www.', $string);
       break;
     case ($link === "POST"):
       $matches = [];
       preg_match_all($pattern, $string, $matches, PREG_SET_ORDER);
       $string_new = '';
       foreach ($matches as $key => $ul) {
         $url = $ul[2] . $ul[3];
         $display = kuerzen($url, $length);
         $form = "<form name=\"sub$key\" method=\"post\" action=\"" . htmlspecialchars($redir, ENT_QUOTES, 'UTF-8') . "\"><input type=\"hidden\" id=\"up\" name=\"up\" value=\"" . htmlspecialchars($url, ENT_QUOTES, 'UTF-8') . "\"></FORM>";
         $string_new .= "$form $ul[1]<a href=\"javascript:void(0)\" onclick=\"document.sub$key.submit(); return false;\" rel=\"nofollow\">" . htmlspecialchars($display, ENT_QUOTES, 'UTF-8') . "</a>$ul[4]";
       }
       $string = $string_new;
       $string = str_ireplace('value="www.', 'value="http://www.', $string);
       break;
   }
   return $string;
 }

 ?>

