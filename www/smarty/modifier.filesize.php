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
  if (is_null($size) || $size === FALSE || $size == 0)
    return $size;

  if ($size > 1024*1024*1024)
    $size = sprintf("%.1f GB", $size / (1024*1024*1024));
  if ($size > 1024*1024)
    $size = sprintf( "%.1f MB", $size / (1024*1024));
  elseif ($size > 1024)
    $size = sprintf( "%.1f kB", $size / 1024);
  elseif ($size < 0)
    $size = '&nbsp;';
  else
    $size = sprintf("%d B", $size);

  return $size;
}
?>
