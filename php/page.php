<?php

namespace bbsengine6\page;

require_once("/srv/www/bbsengine6/php/bootstrap.php");

require_once("config.php");
require_once("engine.php");
require_once("session.php");

// require_once("Markdown.inc.php");

 /**
  * display the permission denied template
  *
  * @access public
  * @since 20240810 copied from bbsengine4
  */
 function permissiondenied($message="permission denied", $statuscode=403, $title="permission denied")
 {
   util\logentry("displaypermissiondenied.100: message=".var_export($message, true));

   $message = empty($message) ? "permission has been denied. sorry it didn't work out." : $message;
   $res = displayerrorpage($message, $statuscode, $title);
   return $res;
 }

 function redirect($message, $url = null, $delay = -1)
 {
   // if we were not given a url to redirect to, get the last one that was
   // set and use that.
   $url = ($url === null) ? getreturntourl() : $url;
   $title = getreturntotitle();

   if ($url !== null)
   {
     header("Location: {$url}");
     return;
   }
   $data = [];
   $data["url"] = $url;
   $data["delay"] = $delay;
   $data["message"] = $message;

   util\logentry("bbsengine6.displayredirectpage.100: data=".var_export($data, true));

   return \bbsengine6\displaypage($data, "redirectpage.tmpl");
 }

/**
 * display an error page template with message
 * 
 * @param string $message
 * @param integer $statuscode http error code (i.e. 500, 404)
 * @param string $title
 * @param string $template
 * @access public
 * @since 20120608
 * @since 20230214 added to bbsengine5/engine.php
 * @since 20241114 moved from engine.php to page.php and renamed
 */
function error($message, $statuscode=418, $title="error", $template="errormessage.tmpl", $data=[])
{
  \bbsengine6\util\logentry("displayerrorpage.100: message=".var_export($message, true)." statuscode=".var_export($statuscode, true));

  header("HTTP/1.0 {$statuscode} {$title}", true, $statuscode);
  $data["statuscode"] = $statuscode;
  $data["message"] = $message;
  $data["title"] = $title;
  \bbsengine6\displaypage($data, $template);
  return;
}

/*
class Page
{
  function main()
  {
    \bbsengine6\session\start();

    $file = isset($_REQUEST["file"]) ? $_REQUEST["file"] : null;
    if ($file === null)
    {
      \bbsengine6\util\logentry("page.200: 'file' is null");
      \bbsengine6\displayerrorpage("page not found", 404);
      return;
    }

    $info = pathinfo($file);
    $fileextension = $info["extension"];
    $filename = $info["filename"];

    \bbsengine6\setreturnto(\bbsengine6\getcurrenturi());
    \bbsengine6\setcurrentsite(\config\SITENAME);
    \bbsengine6\setcurrentaction("view");
    \bbsengine6\setcurrentpage($filename);

    switch ($fileextension)
    {
      case "md":
      {
        $pagetemplate = "page-markdown.tmpl";
        $content = Markdown::defaultTransform(file_get_contents($file));
        break;
      }
      case "tmpl":
      {
        $pagetemplate = $file;
        $smarty = \bbsengine6\getsmarty();
        if ($smarty->templateExists($file) == false)
        {
          \bbsengine6\displayerrorpage("template not found", 404);
          return;
        }
        $content = $smarty->fetch($file);
        break;
      }
    }

    $data = [];
    $data["content"] = $content;
    
    $res = \bbsengine6\displaypage($data, $pagetemplate);
    return $res;
  }
};
*/
//$a = new page();
//$b = $a->main();
