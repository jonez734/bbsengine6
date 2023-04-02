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
  $sql = "select data from engine.session where id=? and expiry >= now()";
  $dat = ["id" => $sessionid];
  $stmt = $this->pdo->prepare($sql);
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

?>
