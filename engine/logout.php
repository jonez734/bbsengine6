<?php
/**
 * logout.php - Member logout
 *
 * @copyright (C) 2024 {@link https://zoidtechnologies.com/ zoidtechnologies.com} All Rights Reserved.
 * @package bbsengine6
 */

require_once("/srv/www/bbsengine6/php/bootstrap.php");

require_once("config.php");
require_once("session.php");
require_once("engine.php");
require_once("libmember.php");

use bbsengine6\util\logentry;
use bbsengine6\member\lib as memberlib;

function logout_run(array $args = []): void
{
    if ($_SERVER['REQUEST_METHOD'] !== 'POST')
    {
        header('Allow: POST');
        http_response_code(405);
        echo 'Method Not Allowed';
        return;
    }

    \bbsengine6\session\start();

    if (!\bbsengine6\util\csrfCheckRequest())
    {
        logentry("logout: CSRF validation failed");
        http_response_code(403);
        echo 'Forbidden';
        return;
    }

    $moniker = $_SESSION["currentmoniker"] ?? null;
    $memberid = $_SESSION["currentmemberid"] ?? null;

    logentry("logout: OK for moniker " . var_export($moniker, true));

    if ($memberid !== null)
    {
        memberlib\setflag("AUTHENTICATED", 0, $memberid);
    }

    \bbsengine6\util\actionlog(action: "logout");

    $name = session_name();
    $secure = (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off');
    $cookieParams = session_get_cookie_params();
    setcookie($name, '', [
        'expires' => time() - 3600,
        'path' => $cookieParams['path'] ?? '/',
        'domain' => $cookieParams['domain'] ?? '',
        'secure' => $secure,
        'httponly' => true,
        'samesite' => 'Lax',
    ]);
    unset($_COOKIE[$name]);

    $_SESSION = [];

    if (session_status() === PHP_SESSION_ACTIVE) {
        session_destroy();
    }

    \bbsengine6\page\redirect("OK -- logged out");
}

logout_run();
