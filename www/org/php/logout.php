<?php
/*
 * this module performs a "logout" of the currently logged in member.
 *
 * @copyright (C) 2008 {@link http://zoidtechnologies.com/ Zoid Technologies} All Rights Reserved.
 */
require_once("config.php");
require_once("bbsenginedotorg.php");
require_once("bbsengine3.php");

class logout
{
  function main()
  {
    session_start();
    
    $id = $_SESSION["currentmemberid"];
    
    displayredirectpage("OK -- logged out");
    logentry("logout: OK for id #{$id}");
    unset($_SESSION["currentmemberid"]);

    return;
  }
}

$l = new logout();
$l->main();

?>
