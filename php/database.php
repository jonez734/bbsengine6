<?php

namespace bbsengine6\database 
{

/**
 * Helper function to get the database DSN with fallback
 * @return string DSN connection string
 */
function getDSN(): string
{
  if (defined('\config\SYSTEMDSN')) {
    return \config\SYSTEMDSN;
  } elseif (defined('\SYSTEMDSN')) {
    return \SYSTEMDSN;
  }
  return '';
}

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

function validateColumnName(string $column): bool
{
  return preg_match('/^[a-zA-Z_][a-zA-Z0-9_]*$/', $column) === 1;
}

function validateTableName(string $table): bool
{
  return preg_match('/^[a-zA-Z_][a-zA-Z0-9_.]*$/', $table) === 1;
}

function insert($pdo, $tablename, $data, $returnid=true, $primarykey="id", $removeprimary=true, $mogrify=false)
{
  if (empty($data)) {
    \bbsengine6\util\logentry("database.insert.100: empty data array");
    return false;
  }

  if (!validateTableName($tablename))
  {
    \bbsengine6\util\echo_traceback("bbsengine6.database.insert.110: Invalid table name: " . $tablename);
    return false;
  }

  $validColumns = [];
  foreach (array_keys($data) as $col)
  {
    if (!validateColumnName($col))
    {
      \bbsengine6\util\echo_traceback("bbsengine6.database.insert.115: Invalid column name: " . $col);
      return false;
    }
    $validColumns[] = $col;
  }

  if (array_key_exists($primarykey, $data) === true && $removeprimary == true)
  {
    unset($data[$primarykey]);
  }

  $sql = "insert into $tablename(".join(", ", $validColumns).")";
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

  try {
    $pdo->beginTransaction();
    $stmt = $pdo->prepare($sql);
    $stmt->execute(array_values($data));
    $pdo->commit();
    if ($returnid === true)
    {
      return $pdo->lastInsertId();
    }
    return true;
  } catch (\Throwable $e) {
    $pdo->rollBack();
    \bbsengine6\util\echo_traceback("bbsengine6.database.insert.200: " . $e->getMessage());
    return false;
  }
}

function update($pdo, $tablename, $key, $data, $primarykey="id", $removeprimary=true, $mogrify=false)
{
  if (empty($data)) {
    \bbsengine6\util\logentry("database.update.100: empty data array");
    return false;
  }

  if (!validateTableName($tablename))
  {
    \bbsengine6\util\echo_traceback("bbsengine6.database.update.110: Invalid table name: " . $tablename);
    return false;
  }

  if (!validateColumnName($primarykey))
  {
    \bbsengine6\util\echo_traceback("bbsengine6.database.update.115: Invalid primary key: " . $primarykey);
    return false;
  }

  $sql = "update $tablename set ";
  
  $foo = [];
  foreach (array_keys($data) as $k)
  {
    if (!validateColumnName($k))
    {
      \bbsengine6\util\echo_traceback("bbsengine6.database.update.120: Invalid column name: " . $k);
      return false;
    }
    if ($removeprimary === true && $k !== $primarykey)
    {
      $foo[] = "$k=:$k";
    }
  }
  $sql .= join(", ", $foo);
  $sql .= " where $primarykey=:$primarykey";
  \bbsengine6\util\logentry("bbsengine6.database.update.100: sql=".var_export($sql, true));

  try {
    $pdo->beginTransaction();
    $stmt = $pdo->prepare($sql);
    $data[$primarykey] = $key;
    $stmt->execute($data);
    $pdo->commit();
    return $stmt->rowcount();
  } catch (\Throwable $e) {
    $pdo->rollBack();
    \bbsengine6\util\echo_traceback("bbsengine6.database.update.200: " . $e->getMessage());
    return false;
  }
}

function disconnect($dsn)
{
  // $pdocache[$dsn] = null;
  return;
}
} /* namespace \bbsengine6\database */
?>
