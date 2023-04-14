<?php

require_once("config.php");
require_once("bbsengine3.php");

require_once("HTML/QuickForm2/Rule/Callback.php");
require_once("HTML/QuickForm2/Rule/Required.php");

startsession();

function testformsuccess($values)
{
  $bodycontent = array();
  $bodycontent[] = "<pre>".var_export($values, True)."</pre>";
  
/*
  logentry("testformsuccess.100: display permission denied page");
  displayredirectpage("testing", null, 0);
  return True;
*/
  $page = getpage("foo");
  $page->addBodyContent($bodycontent);
  $res = displaypage($page);
  
//  $res = displaypage($page);
/*
  $pageprotocol = getpageprotocol();
  if ($pageprotocol === "enhanced")
  {
    $bodycontent = $page->getBodyContent();
    $page = array();
    $page["body"] = $bodycontent;
    print encodejson(array("page" => $page));
//    return PEAR::raiseError("bogus");
    return True;
  }
  elseif ($pageprotocol === "standard")
  {
    print "standard protocol not handled yet";
  }
*/
  return True;
}

$form = getquickform("test-form");

$defaults = array();
$defaults["textinput"] = "http://example.com/";

$form->addDataSource(new HTML_QuickForm2_DataSource_Array($defaults));

$const = array();
$const["mode"] = "test";
$const["memberid"] = getcurrentmemberid();

$form->addDataSource(new HTML_QuickForm2_DataSource_Array($const));

$fieldset = $form->addFieldset("testing")->setLabel("Test Form!");

$textinput = $fieldset->addElement("text", "textinput");
$textinput->setLabel("Text Input");
$textinput->addRule("required", "'Text Input' is a required field.");
// $textinput->addRule("callback", "URL exists", "uniqueurl");

$textarea = $fieldset->addElement("textarea", "anothertest");
$textarea->setLabel("text area");

$group = $fieldset->addElement("group", "radiogroup");
$group->setSeparator("&nbsp;");
$group->addElement("radio", "radiotest", array("value" => 1), array("content" => "one fish"));
$group->addElement("radio", "radiotest", array("value" => 2), array("content" => "two fish"));

$group = $fieldset->addElement("group", "checkboxgroup");
$group->setSeparator("&nbsp;");
$group->addElement("checkbox", "checkboxtest", array("value" => 1), array("content" => "red fish"));
$group->addElement("checkbox", "checkboxtest", array("value" => 2), array("content" => "blue fish"));

$fieldset->addElement("submit", "tryitout", array("value" => "test"));

$res = handleform($form, "testformsuccess", "page title here");
if ($res === True)
{
  logentry("testform.200: processform() returned true");
  exit;
//  displayredirectpage("OK -- form tested", "/", 5);
}
elseif (PEAR::isError($res))
{
  logentry("testform.100: " . $res->toString());
  displayerrorpage($res->getMessage());
  exit;
}

$renderer = getquickformrenderer();
$form->render($renderer);
$res = displayform($renderer, "title here");
exit;

?>
