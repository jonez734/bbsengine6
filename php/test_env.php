<?php
/**
 * Test for bbsengine6\util\env() and typed wrappers.
 *
 * Plain PHP test runner (no framework). Run via:
 *     cd bbsengine6 && php php/test_env.php
 *
 * Exits 0 on success, 1 on any failure.
 *
 * @since 20260918
 */

require_once(__DIR__ . "/util.php");

use function bbsengine6\util\env;
use function bbsengine6\util\env_string;
use function bbsengine6\util\env_int;
use function bbsengine6\util\env_bool;
use function bbsengine6\util\getenv_redirect;
use function bbsengine6\util\vhost_label;

$failures = 0;
$total = 0;

function check(string $label, bool $cond): void
{
    global $failures, $total;
    $total++;
    if ($cond) {
        echo "PASS  $label\n";
    } else {
        echo "FAIL  $label\n";
        $failures++;
    }
}

// --- env() ------------------------------------------------------------------

// env wins
putenv("BBSENGINE6_TEST_KEY=from-env");
check("env: getenv returns value when set",
    env("BBSENGINE6_TEST_KEY") === "from-env");

// default fallback when env unset
putenv("BBSENGINE6_TEST_KEY");
check("env: returns default when env unset",
    env("BBSENGINE6_TEST_KEY_MISSING", "fallback") === "fallback");

// empty-string env treated as missing (consistent with handbook_home et al.)
putenv("BBSENGINE6_TEST_KEY=");
check("env: empty-string env treated as missing",
    env("BBSENGINE6_TEST_KEY", "fallback") === "fallback");

// env_int / env_bool / env_string still hit the missing path
putenv("BBSENGINE6_TEST_KEY");
check("env_string: missing => default",
    env_string("BBSENGINE6_TEST_KEY_MISSING", "x") === "x");

// --- defined-constant fallback ---------------------------------------------

// Set a constant (only if not already defined to avoid PHP notices)
if (!defined("BBSENGINE6_TEST_CONST")) {
    define("BBSENGINE6_TEST_CONST", "from-constant");
}

// env set => wins over constant
putenv("BBSENGINE6_TEST_CONST=from-env");
check("env: getenv wins over defined constant",
    env("BBSENGINE6_TEST_CONST") === "from-env");

// env unset => falls through to constant
putenv("BBSENGINE6_TEST_CONST");
check("env: falls back to defined constant",
    env("BBSENGINE6_TEST_CONST") === "from-constant");

// --- env_string ------------------------------------------------------------

putenv("BBSENGINE6_TEST_STRING=hello");
check("env_string: passthrough string",
    env_string("BBSENGINE6_TEST_STRING", "x") === "hello");

putenv("BBSENGINE6_TEST_STRING=");
check("env_string: empty-string env treated as missing",
    env_string("BBSENGINE6_TEST_STRING", "default") === "default");

// --- env_int ---------------------------------------------------------------

putenv("BBSENGINE6_TEST_INT=42");
check("env_int: numeric string",
    env_int("BBSENGINE6_TEST_INT") === 42);

putenv("BBSENGINE6_TEST_INT=-7");
check("env_int: negative numeric string",
    env_int("BBSENGINE6_TEST_INT") === -7);

putenv("BBSENGINE6_TEST_INT=3.14");
check("env_int: non-integer numeric string truncated to int",
    env_int("BBSENGINE6_TEST_INT") === 3);

putenv("BBSENGINE6_TEST_INT=not-a-number");
check("env_int: non-numeric falls back to default",
    env_int("BBSENGINE6_TEST_INT", 7) === 7);

putenv("BBSENGINE6_TEST_INT=");
check("env_int: empty-string env treated as missing",
    env_int("BBSENGINE6_TEST_INT", 99) === 99);

// --- env_bool --------------------------------------------------------------

$cases = [
    ["1",      true],
    ["true",   true],
    ["TRUE",   true],
    ["yes",    true],
    ["on",     true],
    ["t",      true],
    ["0",      false],
    ["false",  false],
    ["FALSE",  false],
    ["no",     false],
    ["off",    false],
    ["f",      false],
    ["",       false],
    ["garbage", false],
];
foreach ($cases as [$val, $expected]) {
    putenv("BBSENGINE6_TEST_BOOL=$val");
    check("env_bool: '$val' => " . ($expected ? "true" : "false"),
        env_bool("BBSENGINE6_TEST_BOOL") === $expected);
}

putenv("BBSENGINE6_TEST_BOOL");
check("env_bool: unset env => default false",
    env_bool("BBSENGINE6_TEST_BOOL", false) === false);
check("env_bool: unset env => default true",
    env_bool("BBSENGINE6_TEST_BOOL_MISSING", true) === true);

// --- env_bool with int passthrough ------------------------------------------

// env_bool is a typed wrapper around env(); env() returns strings for
// env-derived values, but a caller could pass an int via the default.
// Document the int-passthrough behavior.
putenv("BBSENGINE6_TEST_BOOL");
check("env_bool: int default 1 => true",
    env_bool("BBSENGINE6_TEST_BOOL", 1) === true);
check("env_bool: int default 0 => false",
    env_bool("BBSENGINE6_TEST_BOOL", 0) === false);

// --- REDIRECT_<key> chain (Apache internal-redirect carry-over) ----------
//
// When a vhost's .htaccess declares `SetEnv TEOSLABEL teos` and the
// htaccess also does an internal redirect from /<uri> to
// /engine/router.php?uri=<uri>, the value survives only as
// REDIRECT_TEOSLABEL in the env passed to /engine/router.php's PHP
// handler (per-directory config is re-evaluated for /engine/ and the
// teos htaccess is no longer in scope). bbsengine6\util\env() walks
// one or more REDIRECT_ layers so callers can keep using env().

// clean slate
foreach (["BBSENGINE6_TEST_KEY",
          "REDIRECT_BBSENGINE6_TEST_KEY",
          "REDIRECT_REDIRECT_BBSENGINE6_TEST_KEY"] as $k) {
    putenv($k);
}

// plain env beats REDIRECT_*
putenv("BBSENGINE6_TEST_KEY=plain");
putenv("REDIRECT_BBSENGINE6_TEST_KEY=redirected");
check('env: getenv($key) wins over REDIRECT_<key>',
    env("BBSENGINE6_TEST_KEY") === "plain");

// only REDIRECT_<key> set -> returned
putenv("BBSENGINE6_TEST_KEY");
putenv("REDIRECT_BBSENGINE6_TEST_KEY=redirected");
check('env: falls through to REDIRECT_<key> when $key unset',
    env("BBSENGINE6_TEST_KEY") === "redirected");

// REDIRECT_<key> empty -> falls further (does not return empty)
putenv("BBSENGINE6_TEST_KEY");
putenv("REDIRECT_BBSENGINE6_TEST_KEY=");
putenv("REDIRECT_REDIRECT_BBSENGINE6_TEST_KEY=two_hops");
check("env: empty REDIRECT_<key> falls through to REDIRECT_REDIRECT_<key>",
    env("BBSENGINE6_TEST_KEY") === "two_hops");

// two-hop fallthrough
putenv("BBSENGINE6_TEST_KEY");
putenv("REDIRECT_BBSENGINE6_TEST_KEY");
putenv("REDIRECT_REDIRECT_BBSENGINE6_TEST_KEY=two_hops");
check("env: REDIRECT_REDIRECT_<key> reached when no unprefixed key",
    env("BBSENGINE6_TEST_KEY") === "two_hops");

// nothing set -> default
putenv("BBSENGINE6_TEST_KEY");
putenv("REDIRECT_BBSENGINE6_TEST_KEY");
putenv("REDIRECT_REDIRECT_BBSENGINE6_TEST_KEY");
check("env: nothing set returns default",
    env("BBSENGINE6_TEST_KEY", "def") === "def");

// --- getenv_redirect() -----------------------------------------------------

putenv("BBSENGINE6_TEST_KEY");
putenv("REDIRECT_BBSENGINE6_TEST_KEY");
putenv("REDIRECT_REDIRECT_BBSENGINE6_TEST_KEY");
check("getenv_redirect: nothing set returns false",
    getenv_redirect("BBSENGINE6_TEST_KEY") === false);

putenv("BBSENGINE6_TEST_KEY=plain");
check("getenv_redirect: returns unprefixed",
    getenv_redirect("BBSENGINE6_TEST_KEY") === "plain");

putenv("BBSENGINE6_TEST_KEY");
putenv("REDIRECT_BBSENGINE6_TEST_KEY=red");
check("getenv_redirect: returns REDIRECT_ when unprefixed unset",
    getenv_redirect("BBSENGINE6_TEST_KEY") === "red");

putenv("BBSENGINE6_TEST_KEY=plain");
putenv("REDIRECT_BBSENGINE6_TEST_KEY=red");
check("getenv_redirect: unprefixed wins",
    getenv_redirect("BBSENGINE6_TEST_KEY") === "plain");

putenv("BBSENGINE6_TEST_KEY=plain");
putenv("REDIRECT_BBSENGINE6_TEST_KEY=red");
check("getenv_redirect: maxhops=0 stops at unprefixed",
    getenv_redirect("BBSENGINE6_TEST_KEY", 0) === "plain");

putenv("BBSENGINE6_TEST_KEY");
putenv("REDIRECT_BBSENGINE6_TEST_KEY=red");
check("getenv_redirect: maxhops=1 reaches REDIRECT_",
    getenv_redirect("BBSENGINE6_TEST_KEY", 1) === "red");

putenv("BBSENGINE6_TEST_KEY");
putenv("REDIRECT_BBSENGINE6_TEST_KEY=red");
check("getenv_redirect: maxhops=0 cannot reach REDIRECT_",
    getenv_redirect("BBSENGINE6_TEST_KEY", 0) === false);

// --- vhost_label() with REDIRECT_<key> ------------------------------------

foreach (["TEOSLABEL",
          "REDIRECT_TEOSLABEL",
          "REDIRECT_REDIRECT_TEOSLABEL"] as $k) {
    putenv($k);
}
putenv("REDIRECT_TEOSLABEL=te_redirect");
check("vhost_label: returns REDIRECT_TEOSLABEL when TEOSLABEL unset",
    vhost_label() === "te_redirect");

putenv("TEOSLABEL=plain_label");
check("vhost_label: TEOSLABEL wins over REDIRECT_TEOSLABEL",
    vhost_label() === "plain_label");

// --- summary ---------------------------------------------------------------

echo "\n";
if ($failures === 0) {
    echo "OK    $total tests passed\n";
    exit(0);
} else {
    echo "FAIL  $failures of $total failed\n";
    exit(1);
}
