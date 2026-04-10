<?php

/**
 * Smarty filesize_format modifier plugin
 *
 * Type:     modifier<br>
 * Name:     filesize_format<br>
 * Purpose:  format an integer into a "human readable" format via sprintf
 * @author Patrick Prasse <pprasse@actindo.de>
 * @version $Revision: 1.3 $
 * @param string
 * @param string
 * @return string
 * 
 * this code is based on {@link
 * http://smarty.incutio.com/?page=filesize_format filesize_format smarty
 * modifier}. so far all I've done is adjust the name of the modifier and
 * made some coding style changes.
 */
function smarty_modifier_filesize($size)
{
  if (!is_numeric($size) || $size == 0) {
    return '0 B';
  }

  if ($size < 0) {
    return '&nbsp;';
  }

  if ($size >= 1024*1024*1024) {
    return sprintf("%.1f GB", $size / (1024*1024*1024));
  }
  if ($size >= 1024*1024) {
    return sprintf("%.1f MB", $size / (1024*1024));
  }
  if ($size >= 1024) {
    return sprintf("%.1f kB", $size / 1024);
  }
  return sprintf("%d B", $size);
}
?>
