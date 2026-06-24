<?php
/**
 * login.php - Member authentication
 *
 * @copyright (c) 2007-2024 {@link https://zoidtechnologies.com/ zoidtechnologies.com} all rights reserved
 * @package bbsengine6
 */

require_once("/srv/www/bbsengine6/php/bootstrap.php");

require_once("config.php");
require_once("engine.php");
require_once("session.php");
require_once("libmember.php");

use bbsengine6\util\logentry;
use bbsengine6\member\lib as memberlib;

function login_checklogin(array $args): bool
{
    logentry("checklogin.50: args=" . var_export($args, true));

    $login = $args["login"];
    $password = $args["password"];
    
    $sql = "select moniker from engine.member where (loginid=:login or moniker=:login or email=:login) and password=crypt(:password, password) and verifiedbyid is not null";
    $dat = ["login" => $login, "password" => $password];
    $pdo = \bbsengine6\database\connect(\config\SYSTEMDSN);
    $stmt = $pdo->prepare($sql);
    $stmt->execute($dat);
    if ($stmt->rowCount() === 0)
    {
        return false;
    }
    $moniker = $stmt->fetchColumn();
    
    if (memberlib\checkpassword($password, $moniker) === false)
    {
        logentry("{$moniker} failed password check");
        return false;
    }
    
    $verified = memberlib\checkflag("verified", $moniker);
    if ($verified !== true)
    {
        logentry("{$moniker} tried to login but has not been validated");
        return false;
    }
    
    if (memberlib\updatelastlogin($moniker) === false)
    {
        logentry("failed to update lastlogin for {$moniker}");
        return false;
    }

    \bbsengine6\util\actionlog(action: "login", moniker: $moniker);

    logentry("{$moniker} login success!");
    return true;
}

function login_validate(array $values): bool
{
    $login = $values["login"] ?? null;
    $password = $values["password"] ?? null;

    logentry("login.100: login=" . var_export($login, true) . " password=" . var_export($password, true));
    
    $sql = "select * from engine.member where (loginid=:login or moniker=:login or email=:login) and password=crypt(:password, password)";
    $dat = ["login" => $login, "password" => $password];
    
    $pdo = \bbsengine6\database\connect(\config\SYSTEMDSN);

    $stmt = $pdo->prepare($sql);
    $stmt->execute($dat);
    if ($stmt->rowCount() === 0)
    {
        return false;
    }

    $member = $stmt->fetch();
    $memberid = $member["id"];
    $moniker = $member["moniker"];

    logentry("engine.login.100: moniker=" . var_export($moniker, true) . " memberid=" . var_export($memberid, true));
    memberlib\setcurrentmoniker($moniker);
    memberlib\setcurrentid($memberid);

    session_regenerate_id(true);

    $options = [
        "expires" => time() + \config\SESSIONCOOKIEEXPIRE,
        "path" => \config\SESSIONCOOKIEPATH,
        "domain" => \config\SESSIONCOOKIEDOMAIN,
        "secure" => 1,
        "SameSite" => "Lax"
    ];
    setcookie(session_name(), session_id(), $options);

    memberlib\setflag("AUTHENTICATED", 1, $memberid);

    \bbsengine6\page\redirect("OK -- logged in");
    
    logentry("login.20: success for " . var_export($moniker, true) . " (#{$memberid})");
    return true;
}

function login_buildloginfieldset(object $form): void
{
    $fieldset = $form->addElement("fieldset");
    $fieldset->setLabel("authenticate");

    $loginField = $fieldset->addElement("text", "login");
    $loginField->setLabel("Moniker");
    $loginField->addRule("required", "'Moniker' is a required field");

    $password = $fieldset->addElement("password", "password");
    $password->setLabel("Password");
    $password->addRule("required", "'Password' is a required field");
    
    $fieldset->addRule("callback", "'Moniker' or 'Password' incorrect.", "login_checklogin");
}

function login_run(array $args = []): bool
{
    \bbsengine6\session\start();
    
    \bbsengine6\setcurrentsite("engine");
    \bbsengine6\setcurrentaction("login");

    $form = \bbsengine6\getquickform("rgs-login", "post", ["action" => "/login"]);
    login_buildloginfieldset($form);

    $actions = $form->addFieldset("actions");
    $group = $actions->addGroup("group")->setSeparator("&nbsp;");
    $group->addElement("submit", "submit", ["value" => "red pill (accept)"]);
    $group->addElement("submit", "cancel", ["value" => "blue pill (decline)"]);

    $const = [];
    $form->addDataSource(new \bbsengine6\Form\DataSource\ArrayDataSource($const));

    $res = \bbsengine6\handleform($form, "login_validate", "follow the white rabbit...");
    if ($res === true)
    {
        logentry("login.310: handleform(...) returned True");
        return $res;
    }

    $renderer = \bbsengine6\getquickformrenderer();
    $form->render($renderer);

    $options = [];
    $res = \bbsengine6\displayform($renderer, "knock, knock, neo...", $options);
    return $res;
}

$result = login_run();
if ($result instanceof \PEAR)
{
    logentry("login.400: " . $result->toString());
}
