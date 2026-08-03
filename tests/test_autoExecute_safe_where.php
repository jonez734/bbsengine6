<?php
/**
 * test_autoExecute_safe_where.php
 *
 * Regression test for Phase 3 database.php autoExecute() hardening.
 *
 * Pre-Phase-3 the function built SQL like:
 *
 *     UPDATE <table> SET ... WHERE <$where>
 *
 * with $where interpolated as a raw string and values passed via
 * $data. If a caller passed a tainted $where (e.g. "1=1; DROP TABLE x"
 * or "id = $id" with unsanitised $id), the query would be unsafe.
 *
 * Phase 3 changed the signature to:
 *
 *     autoExecute($dbh, $table, $data, $mode, $where, $whereParams)
 *
 * and added two safety checks for UPDATE / DELETE modes:
 *   1. $where must be a non-empty string.
 *   2. $where must contain a `?` placeholder OR $whereParams must
 *      be non-empty — so callers MUST bind values, not interpolate.
 *
 * This test pins down the corrected contract by reading the source
 * file and asserting:
 *   1. The signature includes $whereParams.
 *   2. The empty-WHERE rejection is present.
 *   3. The no-placeholder rejection is present.
 *   4. UPDATE/DELETE SQL uses "WHERE " . $where with $whereParams bound.
 *   5. INSERT does NOT require a WHERE clause.
 */

error_reporting(E_ALL);
ini_set('display_errors', 1);

$tests_passed = 0;
$tests_failed = 0;
$test_results = [];

function run_test_ae($name, $callable) {
    global $tests_passed, $tests_failed, $test_results;
    try {
        $callable();
        $tests_passed++;
        $test_results[] = "PASS: $name";
        echo "  PASS: $name\n";
    } catch (\Exception $e) {
        $tests_failed++;
        $test_results[] = "FAIL: $name - " . $e->getMessage();
        echo "  FAIL: $name\n";
        echo "    Error: " . $e->getMessage() . "\n";
    }
}

$source_path = __DIR__ . "/../php/database.php";
$source = file_get_contents($source_path);

echo "================================================================================\n";
echo "database.autoExecute() WHERE-clause safety Test Suite\n";
echo "================================================================================\n\n";

run_test_ae("source file exists", function() use ($source_path) {
    if (!file_exists($source_path)) {
        throw new \Exception("database.php not found at $source_path");
    }
});

run_test_ae("autoExecute signature includes \$whereParams", function() use ($source) {
    if (!preg_match('/function autoExecute\s*\([^)]*\$whereParams[^)]*\)/s', $source)) {
        throw new \Exception(
            "autoExecute() signature must include \$whereParams as a separate parameter " .
            "so callers bind values instead of interpolating"
        );
    }
});

run_test_ae("autoExecute signature has type-hint on \$whereParams (array)", function() use ($source) {
    if (!preg_match('/function autoExecute\s*\([^)]*array\s+\$whereParams[^)]*\)/s', $source)) {
        throw new \Exception(
            "autoExecute() \$whereParams should be type-hinted as array"
        );
    }
});

/**
 * Extract the autoExecute() function body using brace counting.
 */
$extract_autoexecute_body = function(string $src) {
    // Signature may include return type hint like `): bool {`, so match
    // any non-{ chars between `)` and `{`.
    if (preg_match('/function autoExecute\s*\([^)]*\)[^{]*\{/', $src, $m, PREG_OFFSET_CAPTURE) !== 1) {
        throw new \Exception("Could not find function autoExecute()");
    }
    $start = $m[0][1] + strlen($m[0][0]);
    $depth = 1;
    $i = $start;
    $len = strlen($src);
    while ($i < $len && $depth > 0) {
        $ch = $src[$i];
        if ($ch === '{') $depth++;
        elseif ($ch === '}') $depth--;
        $i++;
    }
    if ($depth !== 0) {
        throw new \Exception("Could not balance braces in autoExecute() body");
    }
    return substr($src, $start, $i - $start - 1);
};

run_test_ae("autoExecute() rejects empty WHERE clause for UPDATE/DELETE", function() use ($source, $extract_autoexecute_body) {
    $body = $extract_autoexecute_body($source);
    if (!preg_match('/trim\s*\(\s*\$where\s*\)\s*===\s*["\']["\']/', $body)) {
        throw new \Exception(
            "autoExecute() must check for empty \$where in UPDATE/DELETE modes " .
            "(looking for 'trim(\$where) === \"\"' pattern)"
        );
    }
});

run_test_ae("autoExecute() rejects WHERE without placeholders or params", function() use ($source, $extract_autoexecute_body) {
    $body = $extract_autoexecute_body($source);
    if (!preg_match('/strpos\s*\(\s*\$where\s*,\s*["\']\?["\']\s*\)\s*===\s*false\s*&&\s*empty\s*\(\s*\$whereParams\s*\)/', $body)) {
        throw new \Exception(
            "autoExecute() must check that \$where has a '?' placeholder " .
            "OR \$whereParams is non-empty (looking for " .
            "'strpos(\$where, '?') === false && empty(\$whereParams)' pattern)"
        );
    }
});

run_test_ae("autoExecute() UPDATE branch uses WHERE + binds \$whereParams", function() use ($source, $extract_autoexecute_body) {
    $body = $extract_autoexecute_body($source);
    if (!preg_match('/UPDATE\s+\$quotedTable\s+SET.*?WHERE\s*"\.?\s*\.\s*\$where/s', $body)) {
        throw new \Exception(
            "autoExecute() UPDATE branch must build SQL with 'WHERE ' . \$where\n" .
            "looking for: UPDATE \$quotedTable SET ... WHERE \". \$where"
        );
    }
    if (!preg_match('/array_merge\s*\(\s*\$values\s*,\s*array_values\s*\(\s*\$whereParams\s*\)\s*\)/', $body)) {
        throw new \Exception(
            "autoExecute() UPDATE branch must merge \$data values with \$whereParams values " .
            "before binding via PDO::execute()"
        );
    }
});

run_test_ae("autoExecute() DELETE branch binds \$whereParams", function() use ($source, $extract_autoexecute_body) {
    $body = $extract_autoexecute_body($source);
    if (!preg_match('/DELETE\s+FROM\s+\$quotedTable\s+WHERE\s+"\.?\s*\.\s*\$where/s', $body)) {
        throw new \Exception(
            "autoExecute() DELETE branch must build SQL with 'WHERE ' . \$where\n" .
            "looking for: DELETE FROM \$quotedTable WHERE \". \$where"
        );
    }
    if (!preg_match('/->execute\s*\(\s*array_values\s*\(\s*\$whereParams\s*\)\s*\)/', $body)) {
        throw new \Exception(
            "autoExecute() DELETE branch must execute with array_values(\$whereParams)"
        );
    }
});

run_test_ae("autoExecute() INSERT branch does not require a WHERE clause", function() use ($source, $extract_autoexecute_body) {
    $body = $extract_autoexecute_body($source);
    if (!preg_match('/MDB2_AUTOQUERY_INSERT.*?INSERT\s+INTO/s', $body)) {
        throw new \Exception(
            "autoExecute() INSERT branch should exist and build an INSERT statement"
        );
    }
});

run_test_ae("autoExecute() table name is validated before use", function() use ($source, $extract_autoexecute_body) {
    $body = $extract_autoexecute_body($source);
    if (strpos($body, "validateTableName(\$table)") === false) {
        throw new \Exception(
            "autoExecute() must call validateTableName(\$table) to reject " .
            "SQL-injection-style table identifiers"
        );
    }
});

run_test_ae("autoExecute() column names are validated per data row", function() use ($source, $extract_autoexecute_body) {
    $body = $extract_autoexecute_body($source);
    if (substr_count($body, "validateColumnName(\$col)") < 2) {
        throw new \Exception(
            "autoExecute() must call validateColumnName(\$col) for both " .
            "INSERT and UPDATE branches (at least 2 occurrences expected)"
        );
    }
});

echo "\n";
echo "================================================================================\n";
echo "Test Results: " . ($tests_passed + $tests_failed) .
     " total, $tests_passed passed, $tests_failed failed\n";
echo "================================================================================\n";

if ($tests_failed > 0) {
    foreach ($test_results as $r) {
        if (strpos($r, "FAIL") !== false) echo "  $r\n";
    }
    exit(1);
}
exit(0);
