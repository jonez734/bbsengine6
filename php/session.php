<?php

namespace bbsengine6\session;

/**
 * session management for bbsengine6.php
 * @since 20230329
*/

require_once("config.php");
require_once("engine.php");
require_once("database.php");
require_once("libmember.php");
require_once("util.php");
 /**
 * @since 20111215
 * @access public
 */
function start()
{
//  logentry("startsession.50: expire=".var_export(SESSIONCOOKIEEXPIRE, true)." domain=".var_export(SESSIONCOOKIEDOMAIN, true));
  
  session_set_cookie_params(\config\SESSIONCOOKIEEXPIRE, "/", \config\SESSIONCOOKIEDOMAIN, false, true);
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

  session_name(\config\SESSIONNAME);
  session_start();
  $lifetime = 0;
  setcookie(session_name(),session_id(),time()+$lifetime, false, true);

  \bbsengine6\util\logentry("completed session start");

  return;
}

function check()
{
  return true;
}

function end()
{
  return true;
}

function get($sessionid)
{
  $dbh = \bbsengine6\database\connect(\SYSTEMDSN);
  if (PEAR::isError($dbh))
  {
    \bbsengine6\util\logentry("bbsengine5.getsession.120: " . $dbh->toString());
    return $dbh;
  }
  if ($dbh === null)
  {
    \bbsengine6\util\logentry("bbsengine6.getsession.100: databaseconnect() returned null");
    return null;
  }

  $sql = "select * from engine.session where id=:sessionid";
  $dat = ["id" => $sessionid];
  $session = $dbh->getRow($sql, ["integer"], $dat, ["text"]);
  if (PEAR::isError($session))
  {
    logentry("bbsengine5.getsession.140: " . $session->toString());
    return $session;
  }
  if ($session === null)
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

  $sql = "select * from engine.session where id=:id";
  $dat = ["id" => $sessionid ];
  $dbh = \bbsengine6\database\connect(\SYSTEMDSN);
  $stmt = $dbh->prepare($sql);
  $stmt->execute($dat);
  if ($stmt->rowcount() === 0)
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
    $dbh = \bbsengine6\database\connect(\SYSTEMDSN);

    $moniker = \bbsengine6\member\lib\getcurrentmoniker();
    
    $validsession = validate($sessionid);
    \bbsengine6\util\logentry("bbsengine6.session.write.120: validsession=".var_export($validsession, true));

    if ($validsession === false)
    {
      \bbsengine6\util\logentry("bbsengine6.session.write.130: validsession is false");
      $sessionid = session_create_id();
      logentry("bbsengine6.session.write.140: new sessionid=$sessionid");
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
    $dbh = \bbsengine6\database\connect(\SYSTEMDSN);
    $dbh->beginTransaction();
    $sql = "delete from engine.__session where id=:id";
    $dat = ["id" => $sessionid];
    $stmt = $dbh->prepare($sql);
    $stmt->execute($dat);
    $dbh->commit();
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
    $dbh = \bbsengine6\database\connect(\SYSTEMDSN);
    $dbh->beginTransaction();
    $sql = "delete from engine.__session where expiry < now()";
    $stmt = $dbh->prepare($sql);
    $stmt->execute();
    $dbh->commit();
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
    $dbh = \bbsengine6\database\connect(\SYSTEMDSN);
    $sql = "select 1 from engine.__session where id=:id and expiry > now()";
    $dat = ["id" => $sessionid];
    $stmt = $dbh->prepare($sql);
    $stmt->execute($dat);
    return ($stmt->rowcount() == 1) ? true : false;
  } catch (\Throwable $e) {
    \bbsengine6\util\echo_traceback("bbsengine6.session.validate.200: " . $e->getMessage());
    return false;
  }
}

function updatelastactivity($sessionid)
{
  \bbsengine6\util\logentry("bbsengine6.session.updatelastactivity.100: sessionid=".var_export($sessionid, true));

  try {
    $dbh = \bbsengine6\database\connect(\SYSTEMDSN);
    $dbh->beginTransaction();
    $sql = "update engine.__session set lastactivity=:lastactivity where id=:id";
    $dat = ["lastactivity" => "now()", "id" => $sessionid];
    $stmt = $dbh->prepare($sql);
    $stmt->execute($dat);
    $dbh->commit();
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
      $dbh = \bbsengine6\database\connect(\SYSTEMDSN);

      $session = [];
      $session["id"] = $sessionid;
      $session["data"] = \bbsengine6\util\encodejson($data);
      $session["expiry"] = \date(DATE_RFC822, time() + \config\SESSIONCOOKIEEXPIRE);
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
