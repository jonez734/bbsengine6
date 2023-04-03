<?php

/**
 * session management for bbsengine6.php
 * @since 20230329
*/

require_once("database.php");

 /**
 * @since 20111215
 * @access public
 */
function startsession()
{
//  logentry("startsession.50: expire=".var_export(SESSIONCOOKIEEXPIRE, true)." domain=".var_export(SESSIONCOOKIEDOMAIN, true));
  
  session_set_cookie_params(SESSIONCOOKIEEXPIRE, "/", SESSIONCOOKIEDOMAIN, false, true);
  session_set_save_handler("_opensession", "_closesession", "_readsession", "_writesession", "_destroysession", "_gcsession");
  ini_set("session.gc_probability", 10);
  ini_set("session.gc_divisor", 100);
  session_name(SESSIONNAME);
  session_start();
  $lifetime = 0;
  setcookie(session_name(),session_id(),time()+$lifetime, false, true);
  return;
}

function checksession()
{
  return true;
}

function endsession()
{
  return true;
}

function getsession($sessionid)
{
  $dbh = databaseconnect(SYSTEMDSN);
  if (PEAR::isError($dbh))
  {
    logentry("bbsengine5.getsession.120: " . $dbh->toString());
    return $dbh;
  }
  if ($dbh === null)
  {
    logentry("bbsengine6.getsession.100: databaseconnect() returned null");
    return null;
  }

  $sql = "select * from engine.session where sessionid=?";
  $dat = [$sessionid];
  $session = $dbh->getRow($sql, ["integer"], $dat, ["text"]);
  if (PEAR::isError($session))
  {
    logentry("bbsengine5.getsession.140: " . $session->toString());
    return $session;
  }
  if ($session === null)
  {
    logentry("bbsengine5.getsession.160: getsession(".var_export($sessionid, true).") returned null");
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
function _opensession($path, $name)
{
//  logentry("_opensession.10: path=".var_export($path, true)." name=".var_export($name, true));
  return true;
}

/** 
 * custom session handler close function.
 *
 * @since 20111228
 * @access private
 */
function _closesession()
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
function _readsession($sessionid)
{
//  logentry("_readsession.100: sessionid=".var_export($sessionid, true));
  $pdo = databaseconnect(SYSTEMDSN);
  $sql = "select data from engine.session where id=:id and expiry >= now()";
  $dat = ["id" => $sessionid];
  $stmt = $pdo->prepare($sql);
  $stmt->execute($dat);
  $res = $stmt->fetchAll();
  
  $data = $res[0];
  $decoded = decodejson($data);
  if ($decoded === null)
  {
    return "";
  }
  return $decoded;
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
function _writesession($sessionid, $data)
{
//  logentry("_writesession.10: id=".var_export($id, True)." data=".var_export($data, True));
//  logentry("_writesession.11: session=".var_export($_SESSION, True));

  $dbh = databaseconnect(SYSTEMDSN);
  $sql = "select 1 from engine.__session where sessionid=:sessionid";
  $dat = [":sessionid" => $sessionid];
  $stmt = $dbh->prepare($sql);
  $stmt->execute($dat);
  $res = $stmt->fetch();

  $memberid = getcurrentmemberid();

  // if there is not a session record in the db, it's a new session, so build a record and insert it
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

/**
 * custom session handler destroy function
 *
 * @since 20111228
 * @since 20230402 ported to bbsengine6
 * @access private
 */
function _destroysession($sessionid)
{
  logentry("_destroy.10: sessionid=".var_export($sessionid, true));
  $dbh = dbconnect(SYSTEMDSN);
  if (PEAR::isError($dbh))
  {
    logentry("_destroy.130: " . $dbh->toString());
    return false;
  }
  $sql = "delete from engine.__session where id=".$dbh->quote($sessionid, "text");
  $res = $dbh->exec($sql);
  if (PEAR::isError($res))
  {
    logentry("_destroy.120: " . $res->toString());
    return false;
  }
  return true;
}

/**
 * custom session handler garbage collection function
 *
 * @since 20111228
 * @since 20230402 ported to bbsengine6
 * @access private
 */
function _gcsession($maxlifetime)
{
  if (defined("DEBUGSESSION"))
  {
    logentry("_gcsession.10: maxlifetime=".var_export($maxlifetime, true));
  }
  $dbh = dbconnect(SYSTEMDSN);
  $res = $dbh->autoExecute("engine.__session", null, MDB2_AUTOQUERY_DELETE, "expiry < now()");
  if (PEAR::isError($res))
  {
    logentry("_gcsession.20: " . $res->toString());
    return false;
  }
  return true;
}

?>
