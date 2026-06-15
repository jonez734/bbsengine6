<?php

require_once("../config.php");
require_once("engine.php");
require_once("session.php");
//require_once("lib.php");

/**
 * this module accepts a moniker or loginid and password and validates it against the database.
 *
 * @copyright (c) 2007-2024 {@link https://zoidtechnologies.com/ zoidtechnologies.com} all rights reserved
 * @package bbsengine6
 */
class login
{
  /**
   * @since 20150420
   */
  function checklogin($args)
  {
          \bbsengine6\util\logentry("checklogin.50: args=".var_export($args, true));

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
//          print("checklogin.100: memberid=".var_export($memberid, true)." login=".var_export($login, true)." password=".var_export($password, true));
          if (\bbsengine6\member\lib\checkpassword($password, $moniker) === false)
          {
            \bbsengine6\util\logentry("{$moniker} failed password check");
            return false;
          }
          if (\bbsengine6\member\lib\verified($moniker) === false)
          {
            \bbsengine6\util\logentry("{$moniker} tried to login but has not been validated");
            return false;
          }
          if (\bbsengine6\member\lib\updatelastlogin($moniker) === false)
          {
            \bbsengine6\util\logenry("failed to update lastlogin for {$moniker}");
            return false;
          }

          \bbsengine6\util\actionlog(action: "login", moniker: $moniker);

          \bbsengine6\util\logentry("{$moniker} login success!");
          return true;
  }
  /**
   * wrapper which validates credentials (username/password) passed via quickform.
   *
   * @return boolean
   */
  function validate($values) // $username, $password)
  {
    $login = isset($values["login"]) ? $values["login"] : null;
    $password = isset($values["password"]) ? $values["password"] : null;

    \bbsengine6\util\logentry("login.100: login=".var_export($login, true)." password=".var_export($password, true));
    $dbh = \bbsengine6\database\connect(\config\SYSTEMDSN);
    if (PEAR::isError($dbh))
    {
      displayerrorpage("database error (code: login.102)");
      \bbsengine6\util\logentry("login.102: " . $dbh->toString());
      return False;
    }

    $sql = "select * from engine.member where (loginid=:login or moniker=:login or email=:login) and password=crypt(:password, password)";// and approvedbyid is not null";
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

//    \bbsengine6\setlastlogin($member["lastlogin"]);
//    \bbsengine6\setlastloginfrom($member["lastloginfrom"]);
    
    $moniker = $member["moniker"]; // isset($member["moniker"]) ? $member["moniker"] : $member["loginid"];

//    $member = [];
//    $member["lastlogin"] = "now()";
//    $member["lastloginfrom"] = \bbsengine6\util\getremoteaddr(); // $_SERVER["REMOTE_ADDR"];
//    \bbsengine6\member\lib\update($pdo, $memberid, $member);
/*
    $res = $dbh->autoExecute("engine.__member", $member, MDB2_AUTOQUERY_UPDATE, "id=" . $dbh->quote($memberid, "integer"));
    if (PEAR::isError($res))
    {
      displayerrorpage("database error (login.108)");
      logentry("login.108: " . $res->toString());
      $dbh->rollback();
      return False;
    }
*/
    \bbsengine6\util\logentry("engine.login.100: moniker=".var_export($moniker, true)." memberid=".var_export($memberid, true));
    \bbsengine6\member\lib\setcurrentmoniker($moniker);
    \bbsengine6\member\lib\setcurrentid($memberid);

    session_regenerate_id(true);

    $options = [
       "expires" => time()+\config\SESSIONCOOKIEEXPIRE,
       "path" => \config\SESSIONCOOKIEPATH,
       "domain" => ".theaiconsensus.com",// \config\SESSIONCOOKIEDOMAIN,
       "secure" => 1,
//       "httponly" => 0,
       "SameSite" => "Lax"
    ];
    setcookie(session_name(), session_id(), $options);
//    setcookie(session_name(),session_id(),time()+\config\SESSIONCOOKIEEXPIRE, \config\SESSIONCOOKIEPATH, \config\SESSIONCOOKIEDOMAIN, true, false, "strict");
                
//    session_set_cookie_params($lifetime); <-- called in startsession() in bbsengine3.php

    \bbsengine6\member\lib\setflag("AUTHENTICATED", 1, $memberid);

    \bbsengine6\displayredirectpage("OK -- logged in");
    
    \bbsengine6\util\logentry("login.20: success for ".var_export($moniker, true)." (#{$memberid})");
    return true;
  }
  
  function main()
  {
    \bbsengine6\session\start();
    
    \bbsengine6\setcurrentsite("engine");
    \bbsengine6\setcurrentaction("login");

    $form = \bbsengine6\getquickform("rgs-login", "post", array("action" => "/login"));
    $this->buildloginfieldset($form);
//    \bbsengine6\buildcaptchafieldset($form);

    $actions = $form->addFieldset("actions");
    $group = $actions->addGroup("group")->setSeparator("&nbsp;");
    $group->addElement("submit", "submit", ["value" => "red pill (accept)"]);
    $group->addElement("submit", "cancel", ["value" => "blue pill (decline)"]);

    $const = [];
    $form->addDataSource(new \HTML_QuickForm2_DataSource_Array($const));

    $res = \bbsengine6\handleform($form, [$this, "validate"], "follow the white rabbit...");
    if (\PEAR::isError($res))
    {
      \bbsengine6\util\logentry("login.300: " . $res->toString());
      return \PEAR::raiseError("login form handling error (code: login.300)");
    }
    if ($res === True)
    {
      \bbsengine6\util\logentry("login.310: handleform(...) returned True");
      return $res;
    }

    $renderer = \bbsengine6\getquickformrenderer();
    $form->render($renderer);

    $options = [];
//    $options["stylesheets"] = [STATICSKINURL."css/login.css"];

    $res = \bbsengine6\displayform($renderer, "knock, knock, neo...", $options);
    if (\PEAR::isError($res))
    {
      \bbsengine6\util\logentry("login.320: " . $res->toString());
      return \PEAR::raiseError("error displaying form (code: login.320)");
    }
//    $data = ["pagetemplate" => "form.tmpl"];
//    \bbsengine6\displaypage($data);
    return $res;
  }

  function buildloginfieldset($form)
  {
    $fieldset = $form->addElement("fieldset");
    $fieldset->setLabel("authenticate");

    $login = $fieldset->addElement("text", "login");
    $login->setLabel("Moniker");
    $login->addRule("required", "'Moniker' is a required field");

    $password = $fieldset->addElement("password", "password");
    $password->setLabel("Password");
    $password->addRule("required", "'Password' is a required field");
    
    $fieldset->addRule("callback", "'Moniker' or 'Password' incorrect.", [$this, "checklogin"]); // array("callback" => "checklogin"));
    
    return;
  }

}

$a = new login();
$b = $a->main();
if (PEAR::isError($b))
{
  \bbsengine6\util\logentry("login.400: " . $b->toString());
}

?>
