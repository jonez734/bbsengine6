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
  
  $user = "";
  
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
function databaseconnect($dsn)
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

// def insert(dbh, table:str, dict, returnid:bool=True, primarykey:str="id", mogrify:bool=False):
function insert($dbh, $tablename, $data, $returnid=true, $primarykey="id", $mogrify=false)
{
    $keys = array_keys($data);
    $keys = array_map("pg_escape_identifier", $keys);
//    $keys = array_map('escape_mysql_identifier', $keys);
    $fields = implode(",", $keys);
//    $table = escape_mysql_identifier($table);
    $placeholders = str_repeat('?,', count($keys) - 1) . '?';
    $sql = "INSERT INTO ".pg_escape_identifier($tablename)."($fields) VALUES ($placeholders)";
    if ($returnid === true)
    {
      $sql += " returning {$tablename}.{$primarykey}";
    }
    $dbh->prepare($sql)->execute(array_values($data));
}  
?>
