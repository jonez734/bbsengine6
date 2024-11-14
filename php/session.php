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
  $dbh = \bbsengine6\database\connect(\config\SYSTEMDSN);
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
  $dbh = \bbsengine6\database\connect(\config\SYSTEMDSN);
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
/*
function _writesession($id, $data)
{
//  logentry("_writesession.10: id=".var_export($id, True)." data=".var_export($data, True));
//  logentry("_writesession.11: session=".var_export($_SESSION, True));

  $dbh = databaseconnect(SYSTEMDSN);
  if (PEAR::isError($dbh))
  {
    logentry("_writesession.14: " . $dbh->toString());
    return False;
  }
  $sql = "select 1 from engine.__session where id=?";
  $dat = array($id);
  $res = $dbh->getOne($sql, array("integer"), $dat, array("text"));
  if (PEAR::isError($res))
  {
    logentry("_writesession.16: " . $res->toString());
    return False;
  }

  $memberid = getcurrentmemberid();

  if ($res === null)
  {
    $expiry = time() + SESSIONCOOKIEEXPIRE;

    $session = array();
    $session["id"] = $id;
    $session["data"] = session_encode();
    $session["expiry"] = date(DATE_RFC822, $expiry);
    $session["ipaddress"] = $_SERVER["REMOTE_ADDR"];
    $session["useragent"] = isset($_SERVER["HTTP_USER_AGENT"]) ? $_SERVER["HTTP_USER_AGENT"] : "";
    $session["memberid"] = $memberid;
    $session["datecreated"] = "now()";

//    logentry("_writesession.18: new session=".var_export($session, True));

    $res = $dbh->autoExecute("engine.__session", $session, MDB2_AUTOQUERY_INSERT);
    if (PEAR::isError($res))
    {
      logentry("_writesession.20: " . $res->toString());
      return False;
    }

  }
  else
  {
    $session = array();
    $session["data"] = session_encode();
    $session["memberid"] = $memberid;

//    logentry("_writesession.22: update session=".var_export($session, True)." id=".var_export($id, True));
    $res = $dbh->autoExecute("engine.__session", $session, MDB2_AUTOQUERY_UPDATE, "id=".$dbh->quote($id, "text"));
    if (PEAR::isError($res))
    {
      logentry("_writesession.24: ".$res->toString());
      return False;
    }

  }

  return true;
}
*/

function write($sessionid, $data)
{
//  logentry("_writesession.10: id=".var_export($id, True)." data=".var_export($data, True));
//  \bbsengine6\logentry("bbsengine6.session.write.125: session=".var_export($_SESSION, True));

  $dbh = \bbsengine6\database\connect(\config\SYSTEMDSN);
/*
  $sql = "select 1 from engine.__session where id=:id";
  $dat = ["id" => $sessionid];
  $stmt = $dbh->prepare($sql);
  $stmt->execute($dat);
  $rowcount = $stmt->rowcount();
*/
//  \bbsengine6\logentry("bbsengine6.session.write.100: sessionid=$sessionid, rowcount=$rowcount");
  \bbsengine6\util\logentry("bbsengine6.session.write.100: sessionid=$sessionid");

  $dbh->beginTransaction();

  $memberid = \bbsengine6\member\lib\getcurrentid();
  
  $validsession = validate($sessionid);
  \bbsengine6\util\logentry("bbsengine6.session.write.120: validsession=".var_export($validsession, true));

  // if there is not a session record in the db, it's a new session, so build a record and insert it
  if ($validsession === false)
  {
    \bbsengine6\util\logentry("bbsengine6.session.write.130: validsession is false");
    $expiry = time() + \config\SESSIONCOOKIEEXPIRE;
    $sessionid = session_create_id();
    logentry("bbsengine6.session.write.100=$sessionid");
    insert($sessionid, $_SESSION);

    \bbsengine6\util\logentry("bbsengine6.session.write.100: session=".var_export($session, true));
    
//    \bbsengine6\database\insert($dbh, "engine.__session", $session, false, "id", false, false);
  }
  else
  {
    \bbsengine6\util\logentry("bbsengine6.session.write.140: updating session $sessionid");

    $session = [];
    $session["data"] = \bbsengine6\util\encodejson($_SESSION); // session_encode();
    $session["memberid"] = $memberid;
    $session["dateupdated"] = "now()";
    $session["lastactivity"] = "now()";
    
    \bbsengine6\database\update($dbh, "engine.__session", $sessionid, $session);

//    logentry("_writesession.22: update session=".var_export($session, True)." id=".var_export($id, True));
/*    $res = $dbh->autoExecute("engine.__session", $session, MDB2_AUTOQUERY_UPDATE, "id=".$dbh->quote($id, "text"));
    if (PEAR::isError($res))
    {
      logentry("_writesession.24: ".$res->toString());
      return False;
    }
*/
  }

  $dbh->commit();

  return true;
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
  $dbh = \bbsengine6\database\connect(\config\SYSTEMDSN);
  $dbh->beginTransaction();
  $sql = "delete from engine.__session where id=:id";
  $dat = ["id" => $sessionid];
  $stmt = $dbh->prepare($sql);
  $res = $stmt->execute($dat);
  $dbh->commit();
  return true;
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
  $dbh = \bbsengine6\database\connect(\config\SYSTEMDSN);
  $dbh->beginTransaction();
  $sql = "delete from engine.__session where expiry < now()";
  $stmt = $dbh->prepare($sql);
  $stmt->execute();
  $dbh->commit();
  return true;
}

function validate($sessionid)
{
  \bbsengine6\util\logentry("bbsengine6.session.validate.100: sessionid=".var_export($sessionid, true));

  $dbh = \bbsengine6\database\connect(\config\SYSTEMDSN);
  $sql = "select 1 from engine.__session where id=:id and expiry > now()";
  $dat = ["id" => $sessionid];
  $stmt = $dbh->prepare($sql);
  $stmt->execute($dat);
  return ($stmt->rowcount() == 1) ? true : false;
}

function updatelastactivity($sessionid)
{
  \bbsengine6\util\logentry("bbsengine6.session.updatelastactivity.100: sessionid=".var_export($sessionid, true));

  $dbh = \bbsengine6\database\connect(\config\SYSTEMDSN);
  $dbh->beginTransaction();
  $sql = "update engine.__session set lastactivity=:lastactivity where id=:id";
  $dat = ["lastactivity" => "now()", "id" => $sessionid];
  $stmt = $dbh->prepare($sql);
  $stmt->execute($dat);
  $dbh->commit();
  \bbsengine6\util\logentry("updatelastactivity.100: sessionid=$sessionid");
  return true;
}

function insert($sessionid, $data=[])
{
    \bbsengine6\util\logentry("bbsengine6.session.insert.100: sessionid=".var_export($sessionid, true));

    $dbh = \bbsengine6\database\connect(\config\SYSTEMDSN);

    \bbsengine6\util\logentry("bbsengine6.session.insert.100: sessionid=$sessionid");
    $session = [];
    $session["id"] = $sessionid; // session_create_id(); // $sessionid;
    $session["data"] = \bbsengine6\util\encodejson($data);
    $session["expiry"] = \date(DATE_RFC822, time() + \config\SESSIONCOOKIEEXPIRE);
    $session["ipaddress"] = $_SERVER["REMOTE_ADDR"];
    $session["useragent"] = isset($_SERVER["HTTP_USER_AGENT"]) ? $_SERVER["HTTP_USER_AGENT"] : "";
    $session["memberid"] = \bbsengine6\member\lib\getcurrentid();
    $session["datecreated"] = "now()";

//    \bbsengine6\logentry("bbsengine6.session.insert.100: session=".var_export($session, true));
    
    \bbsengine6\database\insert($dbh, "engine.__session", $session, false, "id", false, false);
    
    return true;
}
?>
