<?php

/**
 * this is a module to handle member registrations
 */

require_once("../config.php");
require_once("engine.php");
require_once("session.php");
require_once("database.php");
require_once("libmember.php");

class join
{
    var $pdo = null;
    
    function insert($values)
    {
      $currentmemberid = \bbsengine6\member\lib\getcurrentid();

      $moniker = $values["moniker"];

      $member = [];
      $member["email"] = $values["email"];
//      $member["name"] = $values["name"];
      $member["moniker"] = $moniker;// values["moniker"];
      if (\bbsengine6\member\lib\checkflag("SYSOP"))
      {
        $member["credits"] = $values["credits"];
      }
      else
      {
        $member["credits"] = 42;
      }
      $member["datecreated"] = "now()";
      $member["createdbyid"] = $currentmemberid;
      $member["dateupdated"] = "now()";
      $member["updatedbyid"] = $currentmemberid;

      $res = $this->pdo->beginTransaction();
      if (PEAR::isError($res))
      {
        logentry("join.15: " . $res->toString());
        return PEAR::raiseError("Unable to start transaction (code: join.15)");
      }
      $res = \bbsengine6\database\insert($this->pdo, "engine.__member", $member);
      $memberid = $this->pdo->lastInsertID();
      $res = \bbsengine6\member\lib\setpassword($memberid, $values["password"]);
      if ($res === false)
      {
        return PEAR::raiseError("unable to set password");
      }

      $res = $this->pdo->commit();

      \bbsengine6\util\actionlog(action: "join", moniker: $moniker);

      $data = [];
      \bbsengine6\displaypage($data, "thankyouforjoining.tmpl");
      return True;
    }
    
    function main()
    {
        \bbsengine6\session\start();
        
/*
        if (\bbsengine6\flag("AUTHENTICATED") === False)
        {
            \bbsengine6\displaypermissiondenied();
            return;
        }
*/
        $this->pdo = \bbsengine6\database\connect(\config\SYSTEMDSN);
        
        \bbsengine6\setcurrentsite("rgs");
        \bbsengine6\setcurrentaction("join");

        \bbsengine6\logentry("join.100: site=".var_export(\bbsengine6\getcurrentsite(), True)." action=".var_export(\bbsengine6\getcurrentaction(), true));

        $form = \bbsengine6\getquickform(\config\LOGENTRYPREFIX."-join");
        \bbsengine6\member\lib\buildfieldset($form, ["uniquemoniker" => true]);
        // buldprofilefieldset($form);
        \bbsengine6\buildnewpasswordfieldset($form);
        \bbsengine6\buildcaptchafieldset($form);

        $fs = $form->addFieldset("actionsfs");
        $gr = $fs->addGroup("actionsgr")->setSeparator("&nbsp;");
        $gr->addElement("submit", "submit", ["value" => "apply"]);
//        $gr->addElement("submit", "cancel", ["value" => "test"]);
        
        $const = [];
        $const["memberid"] = isset($_REQUEST["memberid"]) ? intval($_REQUEST["memberid"]) : \bbsengine6\member\lib\getcurrentid();
        
        $form->addDataSource(new HTML_QuickForm2_DataSource_Array($const));
  
        $defaults = [];
        $form->addDataSource(new HTML_QuickForm2_DataSource_Array($defaults));
        
        $res = \bbsengine6\handleform($form, [$this, "insert"], "new member");
        if (PEAR::isError($res))
        {
            logentry("join.100: " . $res->toString());
            return \PEAR::raiseError("displayform error (code: join.100)");
        }
        if ($res === True)
        {
            \bbsengine6\logentry("join.130: handleform(...) returned True");
            return True;
        }
        $renderer = \bbsengine6\getquickformrenderer();
        $form->render($renderer);
        $res = \bbsengine6\displayform($renderer, "knock, knock neo...");
        if (PEAR::isError($res))
        {
          logentry("join.302: " . $res->toString());
          return PEAR::raiseError("error displaying form (code: join.302)");
        }
//        $this->pdo->disconnect();
        return $res;
    }
};

$j = new join();
$r = $j->main();
if (PEAR::isError($r))
{
    logentry("join.100: " . $r->toString());
    displayerrormessage($r->getMessage());
    exit;
}
?>
