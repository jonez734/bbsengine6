<?php

//require_once("MDB2.php");
require_once("Log.php");

/**
 * @since 20221116
 */
function databaseconnect($dsn)
{
  static $pdocache = [];

  if (array_key_exists($dsn, $pdocache))
  {
//    logentry("databaseconnect.100: returning cached pdo ref");
    return $pdocache[$dsn];
  }

  $options = [
    \PDO::ATTR_ERRMODE            => \PDO::ERRMODE_EXCEPTION,
    \PDO::ATTR_DEFAULT_FETCH_MODE => \PDO::FETCH_ASSOC,
    \PDO::ATTR_EMULATE_PREPARES   => false,
  ];
  
  $user = "apache";
  
  $pass = "";

  try {
    $pdo = new \PDO($dsn, $user, $pass, $options);
  } catch (\PDOException $e) {
    throw new \PDOException($e->getMessage(), (int)$e->getCode());
  }
  
  $pdocache[$dsn] = $pdo;
  return $pdo;
}

/*
function &databaseconnect($dsn)
{
  logentry("databaseconnect.100: dsn=".var_export($dsn, true));
//  $dbh = MDB2::singleton($dsn);
  $dbh = MDB2::connect($dsn, ["ssl" => true, "debug" => 2]);
  if (PEAR::isError($dbh))
  {
    logentry("databaseconnect.110: " . $dbh->toString());
    return $dbh;
  }
  
  $res = $dbh->setFetchMode(MDB2_FETCHMODE_ASSOC);
  if (PEAR::isError($res))
  {
    logentry("databaseconnect.112: " . $res->toString());
    return $res;
  }
  
  $res = $dbh->loadModule("Extended");
  if (PEAR::isError($res))
  {
    logentry("databaseconnect.114: " . $res->toString());
    return $res;
  }

  return $dbh;
}
*/
?>
