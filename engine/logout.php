<?php
/*
 * this module performs a "logout" of the currently logged in member.
 *
 * @copyright (C) 2024 {@link https://zoidtechnologies.com/ zoidtechnologies.com} All Rights Reserved.
 */
require_once("../config.php");
require_once("session.php");
require_once("engine.php");

//require_once("zoid6.php");

class logout
{
  function main()
  {
    \bbsengine6\session\start();
    
    $moniker = $_SESSION["currentmoniker"];
    \bbsengine6\util\logentry("logout: OK for moniker ".var_export($moniker, true));

    \bbsengine6\member\lib\setflag("AUTHENTICATED", 0, $_SESSION["currentmemberid"]);

    \bbsengine6\util\actionlog(action: "logout");

    $name = session_name();
    setcookie($name, "", 1);
    setcookie($name, false);
    unset($_COOKIE[$name]);

    session_regenerate_id(true);

    $_SESSION["currentid"] = null;
    $_SESSION["currentmoniker"] = null;
    

    \bbsengine6\displayredirectpage("OK -- logged out");

    return;
  }
}

$l = new logout();
$l->main();

?>
