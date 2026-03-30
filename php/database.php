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
    return $pdocache[$dsn];
  }

  $options = [
    \PDO::ATTR_ERRMODE            => \PDO::ERRMODE_EXCEPTION,
    \PDO::ATTR_DEFAULT_FETCH_MODE => \PDO::FETCH_ASSOC,
    \PDO::ATTR_EMULATE_PREPARES   => false,
  ];
  
  $user = getenv('DB_USER') ?: '';
  $pass = getenv('DB_PASS') ?: '';

  try {
    $pdo = new \PDO($dsn, $user, $pass, $options);
  } catch (\PDOException $e) {
    // Check if the exception is "connection refused"
    // SQLSTATE[08006] [7] connection to server at "127.0.0.1", port 5432 failed: Connection refused
    if (strpos($e->getMessage(), 'SQLSTATE[08006] [7]') !== false) {
      // Gracefully handle the error
      error_log('Database connection error: ' . $e->getMessage());
      echo 'We are experiencing technical difficulties [database]. Please try again later.';
    } 
    else 
    {
      // Re-throw the exception for unexpected cases
      throw $e;
    }

//    throw new \PDOException($e->getMessage(), (int)$e->getCode());
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

function validateColumnName(string $column): bool
{
  return preg_match('/^[a-zA-Z_][a-zA-Z0-9_]*$/', $column) === 1;
}

function validateTableName(string $table): bool
{
  return preg_match('/^[a-zA-Z_][a-zA-Z0-9_.]*$/', $table) === 1;
}

// def insert(dbh, table:str, dict, returnid:bool=True, primarykey:str="id", mogrify:bool=False):
function insert($pdo, $tablename, $data, $returnid=true, $primarykey="id", $removeprimary=true, $mogrify=false)
{
  if (!validateTableName($tablename))
  {
    throw new \InvalidArgumentException("Invalid table name: " . $tablename);
  }

  $validColumns = [];
  foreach (array_keys($data) as $col)
  {
    if (!validateColumnName($col))
    {
      throw new \InvalidArgumentException("Invalid column name: " . $col);
    }
    $validColumns[] = $col;
  }

  if (array_key_exists($primarykey, $data) === true && $removeprimary == true)
  {
    unset($data[$primarykey]);
  }

  $sql = "insert into $tablename(".join(", ", $validColumns).")";
  // values (:data, :foo, :bar)
  $foo = [];
  foreach(array_keys($data) as $k)
  {
    $foo[] = ":$k";
  }
  $sql .= " values (".join(", ", $foo).")";
  if ($returnid === true)
  {
    $sql .=" returning $primarykey";
  }

  \bbsengine6\util\logentry("database.insert.100: sql=$sql");

  $stmt = $pdo->prepare($sql);
  $stmt->execute(array_values($data));
  if ($returnid === true)
  {
    return $pdo->lastInsertId();
  }
  return;
}

function update($pdo, $tablename, $key, $data, $primarykey="id", $removeprimary=true, $mogrify=false)
{
  if (!validateTableName($tablename))
  {
    throw new \InvalidArgumentException("Invalid table name: " . $tablename);
  }

  if (!validateColumnName($primarykey))
  {
    throw new \InvalidArgumentException("Invalid primary key: " . $primarykey);
  }

  $sql = "update $tablename set ";
  
  $foo = [];
  foreach (array_keys($data) as $k)
  {
    if (!validateColumnName($k))
    {
      throw new \InvalidArgumentException("Invalid column name: " . $k);
    }
    if ($removeprimary === true && $k !== $primarykey)
    {
      $foo[] = "$k=:$k";
    }
  }
  $sql .= join(", ", $foo);
  $sql .= " where $primarykey=:$primarykey";
  \bbsengine6\util\logentry("bbsengine6.database.update.100: sql=".var_export($sql, true));
  $stmt = $pdo->prepare($sql);
  $data[$primarykey] = $key;
  $stmt->execute($data);
  return $stmt->rowcount();
}

function disconnect($dsn)
{
  // $pdocache[$dsn] = null;
  return;
}
} /* namespace \bbsengine6\database */
?>
