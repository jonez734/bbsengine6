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
    if (strpos($e->getMessage(), 'SQLSTATE[08006] [7]') !== false) {
      error_log('Database connection error: ' . $e->getMessage());
      echo 'We are experiencing technical difficulties [database]. Please try again later.';
    } 
    else 
    {
      throw $e;
    }

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

function quoteIdentifier(string $identifier): string
{
  if (strpos($identifier, '.') !== false) {
    return $identifier;
  }
  return '"' . str_replace('"', '""', $identifier) . '"';
}

/**
 * Build a parameterized SQL query from readable string.
 *
 * Allows readable SQL like:
 *   $db->query("SELECT * FROM $engine.__session WHERE id = :id", [':id' => $sessionid])
 *
 * Supports:
 *   - $schema.table identifiers (converted to proper SQL identifiers)
 *   - :name named placeholders
 *   - $1, $2 positional placeholders
 *
 * @param \PDO $pdo Database connection
 * @param string $sql_template SQL with $schema.table identifiers and :name placeholders
 * @param array $params Parameters for placeholders
 * @return \PDOStatement|false
 */
function query(\PDO $pdo, string $sql_template, array $params = []): \PDOStatement|false
{
  $identifier_pattern = '/\$([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)/';
  $named_placeholder_pattern = '/:([a-zA-Z_][a-zA-Z0-9_]*)/';
  $positional_pattern = '/\$(\d+)/';

  $result = '';
  $last_end = 0;

  preg_replace_callback($identifier_pattern, function($matches) use ($sql_template, &$result, &$last_end) {
    $match = $matches[0];
    $identifier = $matches[1];

    $result .= substr($sql_template, $last_end, strpos($sql_template, $match) - $last_end);

    if (strpos($identifier, '.') !== false) {
      $result .= $identifier;
    } else {
      $result .= '"' . $identifier . '"';
    }

    $last_end = strpos($sql_template, $match) + strlen($match);
  }, $sql_template);

  $result .= substr($sql_template, $last_end);

  try {
    $stmt = $pdo->prepare($result);
    $stmt->execute($params);
    return $stmt;
  } catch (\PDOException $e) {
    \bbsengine6\util\echo_traceback("bbsengine6.database.query.100: " . $e->getMessage());
    return false;
  }
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

  $quotedTable = quoteIdentifier($tablename);
  $quotedColumns = array_map('bbsengine6\database\quoteIdentifier', $validColumns);
  $sql = "insert into $quotedTable(" . join(", ", $quotedColumns) . ")";
  $foo = [];
  foreach(array_keys($data) as $k)
  {
    $foo[] = ":$k";
  }
  $sql .= " values (" . join(", ", $foo) . ")";
  if ($returnid === true)
  {
    $sql .= " returning " . quoteIdentifier($primarykey);
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
    if (isset($pdo) && $pdo->inTransaction()) {
      $pdo->rollBack();
    }
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

  $quotedTable = quoteIdentifier($tablename);
  $sql = "update $quotedTable set ";
  
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
      $foo[] = quoteIdentifier($k) . "=:$k";
    }
  }
  $sql .= join(", ", $foo);
  $sql .= " where " . quoteIdentifier($primarykey) . "=:$primarykey";
  \bbsengine6\util\logentry("bbsengine6.database.update.100: sql=".var_export($sql, true));

  try {
    $pdo->beginTransaction();
    $stmt = $pdo->prepare($sql);
    $data[$primarykey] = $key;
    $stmt->execute($data);
    $pdo->commit();
    return $stmt->rowcount();
  } catch (\Throwable $e) {
    if (isset($pdo) && $pdo->inTransaction()) {
      $pdo->rollBack();
    }
    \bbsengine6\util\echo_traceback("bbsengine6.database.update.200: " . $e->getMessage());
    return false;
  }
}

function disconnect($dsn)
{
  return;
}

define("bbsengine6\\database\\MDB2_AUTOQUERY_INSERT", 1);
define("bbsengine6\\database\\MDB2_AUTOQUERY_UPDATE", 2);
define("bbsengine6\\database\\MDB2_AUTOQUERY_DELETE", 3);

function getAll(\PDO $dbh, string $sql, array $params = []): array|false
{
  try {
    $stmt = $dbh->prepare($sql);
    $stmt->execute($params);
    return $stmt->fetchAll(\PDO::FETCH_ASSOC);
  } catch (\PDOException $e) {
    \bbsengine6\util\echo_traceback("database.getAll.error: " . $e->getMessage());
    return false;
  }
}

function getRow(\PDO $dbh, string $sql, array $params = []): array|false
{
  try {
    $stmt = $dbh->prepare($sql);
    $stmt->execute($params);
    return $stmt->fetch(\PDO::FETCH_ASSOC) ?: false;
  } catch (\PDOException $e) {
    \bbsengine6\util\echo_traceback("database.getRow.error: " . $e->getMessage());
    return false;
  }
}

function autoExecute(\PDO $dbh, string $table, array $data, int $mode, ?string $where = null, array $whereParams = []): bool
{
  if (!validateTableName($table)) {
    \bbsengine6\util\echo_traceback("database.autoExecute.100: Invalid table name: " . $table);
    return false;
  }

  $quotedTable = quoteIdentifier($table);

  if ($mode === \bbsengine6\database\MDB2_AUTOQUERY_UPDATE || $mode === \bbsengine6\database\MDB2_AUTOQUERY_DELETE) {
    if (!is_string($where) || trim($where) === "") {
      \bbsengine6\util\logentry("database.autoExecute.110: empty WHERE clause rejected for mode=$mode");
      return false;
    }
    if (strpos($where, '?') === false && empty($whereParams)) {
      \bbsengine6\util\logentry("database.autoExecute.120: WHERE clause has no placeholders rejected for mode=$mode");
      return false;
    }
  }

  try {
    if ($mode === \bbsengine6\database\MDB2_AUTOQUERY_INSERT) {
      $cols = [];
      $placeholders = [];
      $values = [];
      foreach ($data as $col => $val) {
        if (!validateColumnName($col)) {
          continue;
        }
        $cols[] = quoteIdentifier($col);
        $placeholders[] = "?";
        $values[] = $val;
      }
      $sql = "INSERT INTO $quotedTable (" . implode(", ", $cols) . ") VALUES (" . implode(", ", $placeholders) . ")";
      $stmt = $dbh->prepare($sql);
      return $stmt->execute($values);
    }

    if ($mode === \bbsengine6\database\MDB2_AUTOQUERY_UPDATE) {
      $set = [];
      $values = [];
      foreach ($data as $col => $val) {
        if (!validateColumnName($col)) {
          continue;
        }
        $set[] = quoteIdentifier($col) . " = ?";
        $values[] = $val;
      }
      $values = array_merge($values, array_values($whereParams));
      $sql = "UPDATE $quotedTable SET " . implode(", ", $set) . " WHERE " . $where;
      $stmt = $dbh->prepare($sql);
      return $stmt->execute($values);
    }

    if ($mode === \bbsengine6\database\MDB2_AUTOQUERY_DELETE) {
      $sql = "DELETE FROM $quotedTable WHERE " . $where;
      $stmt = $dbh->prepare($sql);
      return $stmt->execute(array_values($whereParams));
    }

    return false;
  } catch (\PDOException $e) {
    \bbsengine6\util\echo_traceback("database.autoExecute.error: " . $e->getMessage());
    return false;
  }
}

function quote(\PDO $dbh, $value, ?string $type = null): string
{
  if ($value === null) {
    return "NULL";
  }
  return $dbh->quote($value);
}

}
?>
