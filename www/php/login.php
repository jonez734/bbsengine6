<?php
/*
 * this module accepts a login id and password and validates it against the postgresql database.
 *
 * @copyright (C) 2009 {@link http://zoidtechnologies.com/ Zoid Technologies} All Rights Reserved.
 */
require_once("config.php");
require_once("bbsenginedotorg.php");
require_once("bbsengine3.php");

require_once("HTML/QuickForm.php");
require_once("HTML/QuickForm/Renderer/Array.php");

class login
{
  function buildloginform()
  {
    $form = getquickform(LOGENTRYPREFIX."-login");

    $form->addElement("header", "header", "Login");
    
    $form->addElement("text", "emailaddress", "E-Mail address", array("size" => 40, "maxlength" => 255));
    $form->addRule("emailaddress", "'E-Mail address' is a required field.", "required");
    $form->addRule("emailaddress", "'E-Mail address'  must be in correct format", "email");
    
    $form->addElement("password", "password", "Password", array("size" => 40, "maxlength" => 255));
    $form->addRule("password", "'Password' is a required field.", "required");
    $form->addRule("password", "'Password' must be at least 5 characters in length.", "minlength", 5);
    
    return $form;
  }

  /**
   * validate credentials (username/password) passed via $_REQUEST.
   *
   * @return none
   */
  function validate($values)
  {
    $emailaddress = isset($values["emailaddress"]) ? $values["emailaddress"] : null;
    $password =   isset($values["password"]) ? $values["password"] : null;
    
    $dbh = &dbconnect(SYSTEMDSN);
    if (PEAR::isError($dbh))
    {
      logentry("login.10: " . $dbh->toString());
      return PEAR::raiseError("incorrect login id or password");
    }

    $sql = "select id from member where emailaddress=? and password=?";
    $dat = array($emailaddress, md5($password));
    $res = $dbh->getOne($sql, "integer", $dat, array("text", "text", "text"));
    if (PEAR::isError($res))
    {
      logentry("login.20: " . $res->toString());
      return PEAR::raiseError("database error (code: login.20)");
    }

    if (is_null($res))
    {
      logentry("login.30: query returned null");
      return PEAR::raiseError("incorrect login id or password");
    }

    $id = intval($res);

    $member = array();
    $member["lastlogin"] = "now()";
    $member["lastloginfrom"] = $_SERVER["REMOTE_ADDR"];
    $res = $dbh->autoExecute("member", $member, MDB2_AUTOQUERY_UPDATE, "id=" . $dbh->quote($id, "integer"));
    if (PEAR::isError($res))
    {
      logentry("login.50: " . $res->toString());
      return PEAR::raiseError("Database Error (code: login.50)");
    }

    $member = getmember($id);
    if (PEAR::isError($member))
    {
      logentry("login.60: " . $member->toString());
      return PEAR::raiseError("Database Error (code: login.60)");
    }

    setcurrentmemberid($id);

    displayredirectpage("OK");

    logentry("login: success for " . $member["emailaddress"] . " (#{$id})");
//    logentry("login: getcurrentmemberid=" . getcurrentmemberid());
    $dbh->disconnect();
    return;
  }
  
  function main()
  {
    session_start();

    setcurrentpage("login");
    
    $constants = array();
    $defaults = array();
    $form = $this->buildloginform();

    buildcaptchafieldset($form);

    $buttons = array();
    $buttons[] = &HTML_QuickForm::createElement("submit", null, "login");
    $buttons[] = &HTML_QuickForm::createElement("button", "cancel", "cancel", array("onclick"=>"javascript:location.href='".getreturntourl()."';"));
    $form->addGroup($buttons);

    $form->setConstants($constants);
    $form->setDefaults($defaults);
    
    if ($form->validate())
    {
      $form->freeze();
      return $form->process(array(&$this, "validate"), False);
    }

    $renderer = new HTML_QuickForm_Renderer_Array(True);
    $form->accept($renderer);

    $tmpl = getsmarty();
    $tmpl->assign("form", $renderer->toArray());
    
    $page = getpage("auth");
    $page->addStyleSheet(SKINURL . "css/form.css");
    $page->addBodyContent(fetchheader());
    $page->addBodyContent($tmpl->fetch("form.tmpl"));
    $page->addBodyContent(fetchfooter());
    $page->display();
    return;
  }
}

$l = new login();
$r = $l->main();
if (PEAR::isError($r))
{
    logentry("login.100: " . $r->toString());
    displayerrormessage($r->getMessage());
    exit;
}


?>
