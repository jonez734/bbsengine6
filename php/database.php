<?php

namespace bbsengine6\database 
{

/**
 * @since 20221116
 */
function connect($dsn)
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
function insert($dbh, $tablename, $data, $returnid=true, $primarykey="id", $removeprimary=true, $mogrify=false)
{
  if (array_key_exists($primarykey, $data) === true && $removeprimary == true)
  {
    unset($data[$primarykey]);
  }

  $sql = "insert into $tablename(".join(", ", array_keys($data)).")";
  // values (:data, :foo, :bar)
  $foo = [];
  foreach(array_keys($data) as $k)
  {
    $foo[] = ":$k";
  }
  $sql .= " values (".join(", ", $foo).")";

  \bbsengine6\logentry("database.insert.100: sql=$sql");

  return $dbh->prepare($sql)->execute(array_values($data));
}

function update($dbh, $tablename, $key, $data, $primarykey="id", $removeprimary=true, $mogrify=false)
{
/*
  if (array_key_exists($primarykey, $data) === true)
  {
    unset($data[$primarykey]);
    \bbsengine6\logentry("bbsengine6.update.100: removed $primarykey");
  }
*/
  $sql = "update $tablename set ";
  
  $foo = [];
  foreach (array_keys($data) as $k)
  {
    if ($removeprimary === true && $k !== $primarykey)
    {
      $foo[] = "$k=:$k";
    }
  }
  $sql .= join(", ", $foo);
  $sql .= " where $primarykey=:$primarykey";
  \bbsengine6\logentry("bbsengine6.database.update.100: sql=".var_export($sql, true));
  $stmt = $dbh->prepare($sql);
  $data[$primarykey] = $key;
  $stmt->execute($data);
  return $stmt->rowcount();
}

function disconnect($dsn)
{
  // $pdocache[$dsn] = null;
  return;
}
}
?>
