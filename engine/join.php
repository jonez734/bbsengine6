<?php
/**
 * join.php - Member registration
 *
 * @copyright (c) 2007-2024 {@link https://zoidtechnologies.com/ zoidtechnologies.com} all rights reserved
 * @package bbsengine6
 */

require_once(__DIR__ . "/../config.php");
require_once(__DIR__ . "/../php/engine.php");
require_once(__DIR__ . "/../php/session.php");
require_once(__DIR__ . "/../php/database.php");
require_once(__DIR__ . "/../php/libmember.php");

use bbsengine6\util\logentry;
use bbsengine6\member\lib as memberlib;

function join_insert(array $values): bool
{
    $currentmemberid = memberlib\getcurrentid();
    $moniker = $values["moniker"];

    $member = [];
    $member["email"] = $values["email"];
    $member["moniker"] = $moniker;
    
    if (memberlib\checkflag("SYSOP") === true && isset($values["credits"]))
    {
        $member["credits"] = intval($values["credits"]);
    }
    else
    {
        $member["credits"] = 42;
    }
    
    $member["datecreated"] = "now()";
    $member["createdbyid"] = $currentmemberid;
    $member["dateupdated"] = "now()";
    $member["updatedbyid"] = $currentmemberid;

    $pdo = \bbsengine6\database\connect(\config\SYSTEMDSN);
    
    try
    {
        $pdo->beginTransaction();
        
        $memberid = \bbsengine6\database\insert($pdo, "engine.__member", $member);
        
        $res = memberlib\setpassword($memberid ?? $moniker, $values["password"]);
        if ($res === false)
        {
            $pdo->rollBack();
            return false;
        }

        $pdo->commit();
    }
    catch (\Throwable $e)
    {
        if ($pdo->inTransaction())
        {
            $pdo->rollBack();
        }
        logentry("join.15: " . $e->getMessage());
        return false;
    }

    \bbsengine6\util\actionlog(action: "join", moniker: $moniker);

    $data = [];
    \bbsengine6\displaypage($data, "thankyouforjoining.tmpl");
    return true;
}

function join_run(array $args = []): bool
{
    \bbsengine6\session\start();
    
    $pdo = \bbsengine6\database\connect(\config\SYSTEMDSN);
    
    \bbsengine6\setcurrentsite("rgs");
    \bbsengine6\setcurrentaction("join");

    logentry("join.100: site=" . var_export(\bbsengine6\getcurrentsite(), true) . " action=" . var_export(\bbsengine6\getcurrentaction(), true));

    $form = \bbsengine6\getquickform(\config\LOGENTRYPREFIX . "-join");
    memberlib\buildfieldset($form, ["uniquemoniker" => true]);
    \bbsengine6\buildnewpasswordfieldset($form);
    \bbsengine6\buildcaptchafieldset($form);

    $fs = $form->addFieldset("actionsfs");
    $gr = $fs->addGroup("actionsgr")->setSeparator("&nbsp;");
    $gr->addElement("submit", "submit", ["value" => "apply"]);
    
    $const = [];
    $const["memberid"] = isset($_REQUEST["memberid"]) ? intval($_REQUEST["memberid"]) : memberlib\getcurrentid();
    
    $form->addDataSource(new \HTML_QuickForm2_DataSource_Array($const));
  
    $defaults = [];
    $form->addDataSource(new \HTML_QuickForm2_DataSource_Array($defaults));
    
    $res = \bbsengine6\handleform($form, "join_insert", "new member");
    if ($res === true)
    {
        logentry("join.130: handleform(...) returned True");
        return true;
    }
    
    $renderer = \bbsengine6\getquickformrenderer();
    $form->render($renderer);
    $res = \bbsengine6\displayform($renderer, "knock, knock neo...");
    
    return $res ?? false;
}

$result = join_run();
if ($result instanceof \PEAR)
{
    logentry("join.400: " . $result->toString());
    echo "Error: " . htmlspecialchars($result->getMessage());
    exit(1);
}
