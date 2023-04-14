<?php

/**
 * @since 20110621
 */
/*
function buildpath($path)
{
  $path = str_replace("-", "_", $path);
  
  logentry("buildpath.10: path={$path}");
  return $path;
}
*/
/**
 * @since 20110622
 */
function categoryexists($path)
{
  if ($path == "top")
  {
    return True;
  }

  $dbh = dbconnect(SYSTEMDSN);
  if (PEAR::isError($dbh))
  {
    logentry("categoryexists.10: " . $dbh->toString());
    return PEAR::raiseError($dbh);
  }
  $path = trim($path);
  $sql = "select 1 from category where path=?";
  $dat = array($path);
  $res = $dbh->getOne($sql, null, $dat);
  if ($res === null)
  {
    logentry("categoryexists.20: ".var_export($path, true). " does not exist.");
    return False;
  }
  logentry("categoryexists.25: ".var_export($path, true)." exists.");
  return True;
}

/**
 * @since 20110621
 */
function getcategorywithpath($path)
{
  $path = buildpath($path);
  $sql = "select * from category where path=?";
  $dat = array($path);
  $dbh = dbconnect(SYSTEMDSN);
  $res = $dbh->getRow($sql, null, $dat);
  if (PEAR::isError($res))
  {
    logentry("getcategorywithpath.10: " . $res->toString());
    return PEAR::raiseError($res);
  }
  return $res;
}

/**
 * function to build a suitable path part for the location bar
 * @since 20100630
 * @author Zoid Technologies
 */
/*
function buildname($name)
{
  $name = strtolower($name);
  // replace anything that is not a-z0-9 with -
  $name = preg_replace("@[^a-z0-9\/_]@","-", $name);
  // replace 2 or more - with single -
  $name = preg_replace("@[-]{2,}@", "-", $name);
  // remove a - at start or end 
  $name = preg_replace("@-$@", "", $name);
  $name = preg_replace("@^-@", "", $name);
  
  return $name;
}
*/
function buildprofilefieldset(&$form)
{
    $form->addElement("header", "profilefieldset", "Account information");
    $form->addElement("text", "emailaddress", "E-Mail address");
    $form->addRule("emailaddress", "E-mail address is a required field", "required");
    $form->addElement("password", "password", "Password");
    $form->addRule("password", "'Password' is a required field", "required");
    $form->addElement("text", "fullname", "Full Name");
    return;
}

/**
 * process an uploaded file
 *
 * rewritten based on rbr's register.php 2010-10-20
 *
 * @since 20100730
 * @author Zoid Technologies
 */
/*
function processupload($form, $elementname, $destination)
{
  if ($form->elementExists($elementname))
  {
    $element = $form->getElement($elementname);
    if (PEAR::isError($element))
    {
      logentry("processupload.10: " . $element->toString());
      return PEAR::raiseError("Form Error (code: processupload.10)");
    }

//    var_export($element);
//    exit;
    if ($element->isUploadedFile())
    {
      logentry("processupload.20");
      // FIX: possible collision here. check to see if the filename exists already and pick another one if it does.
      $value = $element->getValue();
      logentry("processupload.30: value=".var_export($value, True));
      $filename = buildname(rand(1,999).trim($value["name"]));
      logentry("processupload.40: filename=".var_export($filename, true)." destination=".var_export($destination, true));
      $res = $element->moveUploadedFile($destination, $filename);
      if ($res == False)
      {
        logentry("processupload.50: move of {$elementname} failed");
        return PEAR::raiseError("System Error (code: processupload.50)");
      }
      return $filename;
    }
  }

  return null;
}
*/
/**
 * @since 20110720
 */
function insertpost($post)
{
  $rec = array();
}

/**
 * @since 20110721
 */
function getpost($id)
{
  $dbh = dbconnect(SYSTEMDSN);
  if (PEAR::isError($dbh))
  {
    logentry("getpost.2: " . $dbh->toString());
    return PEAR::raiseError($dbh);
  }
  $sql = "select * from post where id=?";
  $dat = array($id);
  $res = $dbh->getRow($sql, null, $dat, array("integer"));
  if (PEAR::isError($res))
  {
    logentry("getpost.4: " . $res->toString());
    return PEAR::raiseError($res);
  }
  if ($res === null)
  {
    logentry("getpost.6: query returned null");
    return null;
  }
  $post = $res;
  if ($post["membersonly"] == "f") 
  {
    $post["membersonly"] = False;
  }
  else
  {
    $post["membersonly"] = True;
  }
  return $post;
}

function accesspost($op, $post=null, $uid=null)
{
  if ($uid === null)
  {
    $uid = getcurrentmemberid();
  }

  logentry("access_post.10: op=".var_export($op, true)." post=".var_export($post, true)." uid=".var_export($uid, true));

  switch ($op)
  {
    case "add":
      if (flag("ADMIN"))
      {
        return True;
      }
      return False;
    
    case "view":
      if (flag("ADMIN"))
      {
        return True;
      }

      if ($post["membersonly"] == False)
      {
        return True;
      }

      if (flag("MEMBER", $uid) == True)
      {
        return True;
      }

      return False;

    case "edit":
      if (flag("ADMIN", $uid))
      {
        return True;
      }
      return False;

    case "delete":
      if (flag("ADMIN", $uid))
      {
        return True;
      }
      return False;
    default:
      logentry("access_post.20: unknown operation ".var_export($op, true)." requested. uid=".var_export($uid, true));
      return PEAR::raiseError("Bad Input (code: post.20)");
  }
  return False;
}

function accessfile($op, $file=null, $uid=null)
{
  logentry("accessfile.10: op=".var_export($op, true)." file=".var_export($file, true));
  switch ($op)
  {
    case "download":
    {
      if ($file["hidden"] == "t" && flag("ADMIN", $uid) === False)
      {
        return False;
      }
      if ($file["hidden"] == "f" && strpos($file["filepath"], "bbsengine/") === 0)
      {
        return True;
      }
      if ($file["hidden"] == "f" && strpos($file["filepath"], "bbsengine3/") === 0)
      {
        return True;
      }
      return False;
    }
  }
  return False;
}

/** 
 * local version of getsmarty() that sets up plugin dirs, template dirs, etc
 *
 * @since 20140710
 */
function getsmarty($options=null)
{
  $options = array();
  $options["pluginsdir"] = array(SMARTYPLUGINSDIR); //, "/srv/www/zoidweb2/smarty/");
  $options["templatedir"] = array(SMARTYTEMPLATESDIR); // , "/srv/www/zoidweb2/skin/tmpl/");
  $options["compiledir"] = SMARTYCOMPILEDTEMPLATESDIR;
  $options["compileid"] = LOGENTRYPREFIX;
//  logentry("getsmarty.100: options=".var_export($options, True));
  return _getsmarty($options);
}

function buildsidebarmenu()
{
  return [];
}

?>
