<?php
/**
 * logout.php - Member logout
 *
 * @copyright (C) 2024 {@link https://zoidtechnologies.com/ zoidtechnologies.com} All Rights Reserved.
 * @package bbsengine6
 */

require_once(__DIR__ . "/../config.php");
require_once(__DIR__ . "/../php/session.php");
require_once(__DIR__ . "/../php/engine.php");
require_once(__DIR__ . "/../php/libmember.php");

use bbsengine6\util\logentry;
use bbsengine6\member\lib as memberlib;

function logout_run(array $args = []): void
{
    \bbsengine6\session\start();
    
    $moniker = $_SESSION["currentmoniker"] ?? null;
    $memberid = $_SESSION["currentmemberid"] ?? null;
    
    logentry("logout: OK for moniker " . var_export($moniker, true));

    if ($memberid !== null)
    {
        memberlib\setflag("AUTHENTICATED", 0, $memberid);
    }

    \bbsengine6\util\actionlog(action: "logout");

    $name = session_name();
    setcookie($name, "", 1);
    setcookie($name, false);
    unset($_COOKIE[$name]);

    session_regenerate_id(true);

    $_SESSION["currentid"] = null;
    $_SESSION["currentmoniker"] = null;
    $_SESSION["currentmemberid"] = null;

    \bbsengine6\page\redirect("OK -- logged out");
}

logout_run();
