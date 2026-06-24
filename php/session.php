<?php

namespace bbsengine6\session;

/**
 * session management for bbsengine6.php
 * @since 20230329
 */

require_once("/srv/www/bbsengine6/php/bootstrap.php");

require_once("config.php");
require_once("engine.php");
require_once("database.php");
require_once("libmember.php");
require_once("util.php");

/**
 * Helper function to get the database DSN - delegates to database namespace
 * @return string DSN connection string
 * @deprecated Use \bbsengine6\database\getDSN() instead
 */
function getDSN(): string
{
  return \bbsengine6\database\getDSN();
}

 /**
  * @since 20111215
  * @access public
  */
function start()
{
//  logentry("startsession.50: expire=".var_export(SESSIONCOOKIEEXPIRE, true)." domain=".var_export(SESSIONCOOKIEDOMAIN, true));
  
  // Use defined constants with fallback defaults if not set by config
  $expire = defined('\config\SESSIONCOOKIEEXPIRE') ? \config\SESSIONCOOKIEEXPIRE : (12*60*60);
  $domain = defined('\config\SESSIONCOOKIEDOMAIN') ? \config\SESSIONCOOKIEDOMAIN : '';
  
  session_set_cookie_params($expire, "/", $domain, false, true);
  session_set_save_handler(
    "\\bbsengine6\\session\\open",
    "\\bbsengine6\\session\\close",
    "\\bbsengine6\\session\\read",
    "\\bbsengine6\\session\\write",
    "\\bbsengine6\\session\\destroy",
    "\\bbsengine6\\session\\garbagecollect",
    "\\session_create_id",
    "\\bbsengine6\\session\\validate",
    "\\bbsengine6\\session\\updatelastactivity"); // , "\\bbsengine5\\_create_sid", "\\bbsengine6\\_validate_sid", "\\bbsengine6\\_update_timestamp");

  ini_set("session.gc_probability", 10);
  ini_set("session.gc_divisor", 100);
  ini_set("session.serialize_handler", "php_serialize");

  $sessionname = defined('\config\SESSIONNAME') ? \config\SESSIONNAME : 'PHPSESSID';
  session_name($sessionname);
  session_start();
  $lifetime = 0;
  setcookie(session_name(),session_id(),time()+$lifetime, false, true);

  \bbsengine6\util\logentry("completed session start");

  return;
}


function get($sessionid)
{
  $dbh = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
  if ($dbh === null)
  {
    \bbsengine6\util\logentry("bbsengine6.getsession.100: databaseconnect() returned null");
    return null;
  }

  $stmt = \bbsengine6\database\query($dbh, 'SELECT * FROM $engine.session WHERE id = :id', [":id" => $sessionid]);
  if ($stmt === false) {
    return null;
  }
  $session = $stmt->fetch();
  if ($session === false)
  {
    \bbsengine6\util\logentry("bbsengine5.getsession.160: get(".var_export($sessionid, true).") returned null");
    return null;
  }

  return $session;
}

/** 
 * custom session handler open function
 *
 * @since 20111228
 * @access private
 */
function open($path, $name)
{
  \bbsengine6\util\logentry("bbsengine6.session.open.10: stub. path=".var_export($path, true)." name=".var_export($name, true));
  return true;
}

/** 
 * custom session handler close function.
 *
 * @since 20111228
 * @access private
 */
function close()
{
//  logentry("_closesession.10: called");
  return true;
}

/** 
 * custom session handler read function.
 *
 * @since 20111228
 * @access private
 */
function read($sessionid)
{
  \bbsengine6\util\logentry("bbsengine6.session.read.100: sessionid=".var_export($sessionid, true));
  if (validate($sessionid) === false)
  {
    $data = [];
    insert($sessionid, $data);
    return \serialize($data);
  }

  $dbh = \bbsengine6\database\connect(getDSN());
  $stmt = \bbsengine6\database\query($dbh, 'SELECT * FROM $engine.session WHERE id = :id', [":id" => $sessionid]);
  if ($stmt === false || $stmt->rowcount() === 0)
  {
    \bbsengine6\util\logentry("bbsengine6.session.read.120: session disappeared. sessionid=".var_export($sessionid, true));
    return false;
  }

  $res = $stmt->fetch();
  $decoded = \bbsengine6\util\decodejson($res["data"]);
  $serialized = \serialize($decoded);
//  \bbsengine6\logentry("readsesion.120: decoded=".var_export($decoded, true));
  return $serialized;
}

/**
 * custom session handler write function
 *
 * @since 20111228
 * @since 20230402 ported to bbsengine6
 * @access private
 */
function write($sessionid, $data)
{
  \bbsengine6\util\logentry("bbsengine6.session.write.100: sessionid=$sessionid");

  try {
    $dbh = \bbsengine6\database\connect(getDSN());

    $moniker = \bbsengine6\member\lib\getcurrentmoniker();
    
    $validsession = validate($sessionid);
    \bbsengine6\util\logentry("bbsengine6.session.write.120: validsession=".var_export($validsession, true));

    if ($validsession === false)
    {
      \bbsengine6\util\logentry("bbsengine6.session.write.130: validsession is false");
      $sessionid = session_create_id();
      \bbsengine6\util\logentry("bbsengine6.session.write.140: new sessionid=$sessionid");
      insert($sessionid, $_SESSION);
    }
    else
    {
      \bbsengine6\util\logentry("bbsengine6.session.write.150: updating session $sessionid");

      $session = [];
      $session["data"] = \bbsengine6\util\encodejson($_SESSION);
      $session["moniker"] = $moniker;
      $session["dateupdated"] = "now()";
      $session["lastactivity"] = "now()";
      
      $result = \bbsengine6\database\update($dbh, "engine.__session", $sessionid, $session);
      if ($result === false) {
        \bbsengine6\util\logentry("bbsengine6.session.write.160: update failed");
      }
    }

    return true;
  } catch (\Throwable $e) {
    if (isset($dbh) && $dbh->inTransaction()) {
      $dbh->rollBack();
    }
    \bbsengine6\util\echo_traceback("bbsengine6.session.write.200: " . $e->getMessage());
    return false;
  }
}

/**
 * custom session handler destroy function
 *
 * @since 20111228
 * @since 20230402 ported to bbsengine6
 * @access private
 */
function destroy($sessionid)
{
  \bbsengine6\util\logentry("_destroy.10: sessionid=".var_export($sessionid, true));
  try {
    $dbh = \bbsengine6\database\connect(getDSN());
    \bbsengine6\database\query($dbh, 'DELETE FROM $engine.__session WHERE id = :id', [":id" => $sessionid]);
    return true;
  } catch (\Throwable $e) {
    if (isset($dbh) && $dbh->inTransaction()) {
      $dbh->rollBack();
    }
    \bbsengine6\util\echo_traceback("bbsengine6.session.destroy.200: " . $e->getMessage());
    return false;
  }
}

/**
 * custom session handler garbage collection function
 *
 * @since 20111228
 * @since 20230402 ported to bbsengine6
 * @access private
 */
function garbagecollect($maxlifetime)
{
  try {
    $dbh = \bbsengine6\database\connect(getDSN());
    \bbsengine6\database\query($dbh, 'DELETE FROM $engine.__session WHERE expiry < now()');
    return true;
  } catch (\Throwable $e) {
    if (isset($dbh) && $dbh->inTransaction()) {
      $dbh->rollBack();
    }
    \bbsengine6\util\echo_traceback("bbsengine6.session.garbagecollect.200: " . $e->getMessage());
    return false;
  }
}

function validate($sessionid)
{
  \bbsengine6\util\logentry("bbsengine6.session.validate.100: sessionid=".var_export($sessionid, true));

  try {
    $dbh = \bbsengine6\database\connect(getDSN());
    $stmt = \bbsengine6\database\query($dbh, 'SELECT 1 FROM $engine.__session WHERE id = :id AND expiry > now()', [":id" => $sessionid]);
    return ($stmt !== false && $stmt->rowcount() == 1) ? true : false;
  } catch (\Throwable $e) {
    \bbsengine6\util\echo_traceback("bbsengine6.session.validate.200: " . $e->getMessage());
    return false;
  }
}

function updatelastactivity($sessionid)
{
  \bbsengine6\util\logentry("bbsengine6.session.updatelastactivity.100: sessionid=".var_export($sessionid, true));

  try {
    $dbh = \bbsengine6\database\connect(getDSN());
    \bbsengine6\database\query($dbh, 'UPDATE $engine.__session SET lastactivity = now() WHERE id = :id', [":id" => $sessionid]);
    \bbsengine6\util\logentry("updatelastactivity.100: sessionid=$sessionid");
    return true;
  } catch (\Throwable $e) {
    if (isset($dbh) && $dbh->inTransaction()) {
      $dbh->rollBack();
    }
    \bbsengine6\util\echo_traceback("bbsengine6.session.updatelastactivity.200: " . $e->getMessage());
    return false;
  }
}

function insert($sessionid, $data=[])
{
    \bbsengine6\util\logentry("bbsengine6.session.insert.100: sessionid=".var_export($sessionid, true));

    try {
      $dbh = \bbsengine6\database\connect(getDSN());

      $session = [];
      $session["id"] = $sessionid;
      $session["data"] = \bbsengine6\util\encodejson($data);
      $cookieExpire = defined('\config\SESSIONCOOKIEEXPIRE') ? \config\SESSIONCOOKIEEXPIRE : (12*60*60);
      $session["expiry"] = \date(DATE_RFC822, time() + $cookieExpire);
      $session["ipaddress"] = \bbsengine6\util\getremoteaddr() ?? '';
      $session["useragent"] = isset($_SERVER["HTTP_USER_AGENT"]) ? $_SERVER["HTTP_USER_AGENT"] : "";
      $session["moniker"] = \bbsengine6\member\lib\getcurrentmoniker();
      $session["datecreated"] = "now()";

      $result = \bbsengine6\database\insert($dbh, "engine.__session", $session, false, "id", false, false);
      if ($result === false) {
        \bbsengine6\util\logentry("bbsengine6.session.insert.200: insert failed");
        return false;
      }
      
      return true;
    } catch (\Throwable $e) {
      \bbsengine6\util\echo_traceback("bbsengine6.session.insert.300: " . $e->getMessage());
      return false;
    }
}
?>
