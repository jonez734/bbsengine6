<?php
/**
 * test_ltree_query.php - Test ltree query variations with different PDO settings
 *
 * Usage: php test_ltree_query.php
 *
 * Tests various combinations of:
 * - Named vs positional parameters
 * - ltree type cast
 * - PDO emulated prepares on/off
 * - Different databases and paths
 */

$testPaths = [
    "top.entertainment",
    "top.eros", 
    "top",
];

$databases = [
    ["dsn" => "pgsql:host=127.0.0.1;port=5432;dbname=zoid6test", "name" => "zoid6test"],
    ["dsn" => "pgsql:host=127.0.0.1;port=5432;dbname=zoid6", "name" => "zoid6"],
];

$variations = [
    [
        "name" => "Named params, no cast",
        "sql" => "select title, path, uri from engine.sig where path @> :sigpath order by path asc",
        "getParams" => fn($path) => ["sigpath" => $path]
    ],
    [
        "name" => "Named params, with cast",
        "sql" => "select title, path, uri from engine.sig where path @> :sigpath::ltree order by path asc",
        "getParams" => fn($path) => ["sigpath" => $path]
    ],
    [
        "name" => "Positional, no cast",
        "sql" => "select title, path, uri from engine.sig where path @> ? order by path asc",
        "getParams" => fn($path) => [$path]
    ],
    [
        "name" => "Positional, with cast",
        "sql" => "select title, path, uri from engine.sig where path @> ?::ltree order by path asc",
        "getParams" => fn($path) => [$path]
    ],
];

echo "=== Testing ltree @> operator with various parameter styles ===\n\n";

foreach ($databases as $db) {
    echo "=== DATABASE: {$db['name']} ===\n";
    
    foreach ([false, true] as $emulate) {
        echo "--- EMULATE_PREPARES = " . ($emulate ? "true" : "false") . " ---\n";
        
        try {
            $pdo = new \PDO($db["dsn"], 'opencode', '', [
                \PDO::ATTR_ERRMODE => \PDO::ERRMODE_EXCEPTION,
                \PDO::ATTR_EMULATE_PREPARES => $emulate,
            ]);
        } catch (\PDOException $e) {
            echo "  FAILED to connect: " . $e->getMessage() . "\n";
            continue;
        }
        
        foreach ($testPaths as $testPath) {
            echo "  Path: $testPath\n";
            
            foreach ($variations as $v) {
                $params = $v["getParams"]($testPath);
                try {
                    $stmt = $pdo->prepare($v["sql"]);
                    $stmt->execute($params);
                    $rows = $stmt->fetchAll();
                    echo "    [OK]   {$v['name']}: " . count($rows) . " rows\n";
                } catch (\PDOException $e) {
                    echo "    [FAIL] {$v['name']}: " . $e->getMessage() . "\n";
                }
            }
        }
    }
    echo "\n";
}

echo "=== Test complete ===\n";
