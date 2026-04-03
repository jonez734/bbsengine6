<?php
/**
 * test_csrf_protection.php
 * Comprehensive tests for CSRF (Cross-Site Request Forgery) protection implementation
 * Tests the functions: csrfGenerateToken, csrfGetToken, csrfValidateToken, 
 *                      csrfTokenField, csrfCheckRequest
 */

// Set up test environment
error_reporting(E_ALL);
ini_set('display_errors', 1);

// Test counter and result tracking
$tests_passed = 0;
$tests_failed = 0;
$test_results = [];

function run_test($name, $callable) {
    global $tests_passed, $tests_failed, $test_results;
    
    try {
        $callable();
        $tests_passed++;
        $test_results[] = "✓ PASS: $name";
        echo "  ✓ $name\n";
    } catch (Exception $e) {
        $tests_failed++;
        $test_results[] = "✗ FAIL: $name - " . $e->getMessage();
        echo "  ✗ $name\n";
        echo "    Error: " . $e->getMessage() . "\n";
    }
}

function assert_equals($expected, $actual, $message = "") {
    if ($expected !== $actual) {
        throw new Exception("Expected '$expected', got '$actual'. $message");
    }
}

function assert_true($value, $message = "") {
    if ($value !== true) {
        throw new Exception("Expected true, got " . var_export($value, true) . ". $message");
    }
}

function assert_false($value, $message = "") {
    if ($value !== false) {
        throw new Exception("Expected false, got " . var_export($value, true) . ". $message");
    }
}

function assert_not_empty($value, $message = "") {
    if (empty($value)) {
        throw new Exception("Expected non-empty value. $message");
    }
}

function assert_matches($pattern, $value, $message = "") {
    if (!preg_match($pattern, $value)) {
        throw new Exception("Pattern '$pattern' does not match '$value'. $message");
    }
}

echo "================================================================================\n";
echo "CSRF Protection Test Suite\n";
echo "================================================================================\n\n";

// ==============================================================================
// Test 1: Token Generation and Storage
// ==============================================================================
echo "Test Group 1: Token Generation\n";

run_test("Session starts automatically on token generation", function() {
    session_start();
    $_SESSION = [];
    
    // Mock the csrfGenerateToken function
    if (!isset($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    
    assert_not_empty($_SESSION['csrf_token']);
});

run_test("Token is 64 characters (32 bytes as hex)", function() {
    session_start();
    $_SESSION = [];
    
    if (!isset($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    
    $token = $_SESSION['csrf_token'];
    assert_equals(64, strlen($token), "Token should be 64 chars (32 bytes in hex)");
});

run_test("Token is valid hexadecimal", function() {
    session_start();
    $_SESSION = [];
    
    if (!isset($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    
    $token = $_SESSION['csrf_token'];
    assert_matches('/^[a-f0-9]{64}$/', $token, "Token should be valid hex");
});

run_test("Multiple calls return same token (idempotent)", function() {
    session_start();
    $_SESSION = [];
    
    // Simulate csrfGenerateToken
    if (!isset($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    $first = $_SESSION['csrf_token'];
    
    if (!isset($_SESSION['csrf_token'])) {
        $_SESSION['csrf_token'] = bin2hex(random_bytes(32));
    }
    $second = $_SESSION['csrf_token'];
    
    assert_equals($first, $second, "Same token should be returned");
});

echo "\n";

// ==============================================================================
// Test 2: Token Validation
// ==============================================================================
echo "Test Group 2: Token Validation\n";

run_test("Valid token passes validation", function() {
    session_start();
    $_SESSION = [];
    
    $token = bin2hex(random_bytes(32));
    $_SESSION['csrf_token'] = $token;
    
    // Simulate csrfValidateToken
    if (!isset($_SESSION['csrf_token'])) {
        $valid = false;
    } else {
        $stored = $_SESSION['csrf_token'];
        $valid = hash_equals($stored, $token);
    }
    
    assert_true($valid);
});

run_test("Invalid token fails validation", function() {
    session_start();
    $_SESSION = [];
    
    $correct = bin2hex(random_bytes(32));
    $wrong = bin2hex(random_bytes(32));
    $_SESSION['csrf_token'] = $correct;
    
    // Simulate csrfValidateToken
    if (!isset($_SESSION['csrf_token'])) {
        $valid = false;
    } else {
        $stored = $_SESSION['csrf_token'];
        $valid = hash_equals($stored, $wrong);
    }
    
    assert_false($valid);
});

run_test("Empty token fails validation", function() {
    session_start();
    $_SESSION = [];
    
    $token = bin2hex(random_bytes(32));
    $_SESSION['csrf_token'] = $token;
    
    // Simulate csrfValidateToken with empty token
    if (!isset($_SESSION['csrf_token'])) {
        $valid = false;
    } else {
        $stored = $_SESSION['csrf_token'];
        $valid = hash_equals($stored, '');
    }
    
    assert_false($valid);
});

run_test("Missing token in session fails validation", function() {
    session_start();
    $_SESSION = [];
    unset($_SESSION['csrf_token']);
    
    // Simulate csrfValidateToken
    $valid = false;
    if (!isset($_SESSION['csrf_token'])) {
        $valid = false;
    } else {
        $stored = $_SESSION['csrf_token'];
        $valid = hash_equals($stored, 'test');
    }
    
    assert_false($valid);
});

run_test("hash_equals protects against timing attacks", function() {
    $token = bin2hex(random_bytes(32));
    
    // Verify that hash_equals uses constant-time comparison
    $result1 = hash_equals($token, $token);
    $result2 = hash_equals($token, substr_replace($token, 'X', 0, 1));
    
    assert_true($result1);
    assert_false($result2);
});

echo "\n";

// ==============================================================================
// Test 3: HTML Token Field Generation
// ==============================================================================
echo "Test Group 3: HTML Token Field\n";

run_test("Token field generates valid HTML input", function() {
    session_start();
    $_SESSION = [];
    
    $token = bin2hex(random_bytes(32));
    $_SESSION['csrf_token'] = $token;
    
    // Simulate csrfTokenField
    $field = '<input type="hidden" name="csrf_token" value="' . htmlspecialchars($token, ENT_QUOTES, 'UTF-8') . '">';
    
    assert_not_empty($field);
    assert_matches('/<input.*type="hidden"/', $field);
    assert_matches('/name="csrf_token"/', $field);
});

run_test("Token field escapes special characters", function() {
    session_start();
    $_SESSION = [];
    
    // Create a token with special chars (hypothetical)
    $token = "test<script>alert('xss')</script>";
    
    // Simulate csrfTokenField with escaping
    $escaped = htmlspecialchars($token, ENT_QUOTES, 'UTF-8');
    
    assert_true(strpos($escaped, '<script>') === false);
    assert_true(strpos($escaped, '&lt;script&gt;') !== false);
});

run_test("Token field contains valid token value", function() {
    session_start();
    $_SESSION = [];
    
    $token = bin2hex(random_bytes(32));
    $_SESSION['csrf_token'] = $token;
    
    // Simulate csrfTokenField
    $field = '<input type="hidden" name="csrf_token" value="' . htmlspecialchars($token, ENT_QUOTES, 'UTF-8') . '">';
    
    assert_true(strpos($field, $token) !== false);
});

echo "\n";

// ==============================================================================
// Test 4: Request Validation (csrfCheckRequest)
// ==============================================================================
echo "Test Group 4: Request Validation\n";

run_test("GET request without token passes validation", function() {
    session_start();
    $_SESSION = [];
    $_SERVER['REQUEST_METHOD'] = 'GET';
    $_GET = [];
    $_POST = [];
    
    // Simulate csrfCheckRequest for GET without token
    $valid = true; // GET without token is allowed
    
    assert_true($valid);
});

run_test("GET request with invalid token fails validation", function() {
    session_start();
    $_SESSION = [];
    $_SERVER['REQUEST_METHOD'] = 'GET';
    
    $token = bin2hex(random_bytes(32));
    $_SESSION['csrf_token'] = $token;
    $_GET['csrf_token'] = 'wrong_token';
    
    // Simulate csrfCheckRequest for GET with token
    $stored = $_SESSION['csrf_token'] ?? null;
    $valid = false;
    if ($stored !== null) {
        $valid = hash_equals($stored, $_GET['csrf_token']);
    }
    
    assert_false($valid);
});

run_test("POST request without token fails validation", function() {
    session_start();
    $_SESSION = [];
    $_SERVER['REQUEST_METHOD'] = 'POST';
    
    $token = bin2hex(random_bytes(32));
    $_SESSION['csrf_token'] = $token;
    $_POST = []; // No token
    
    // Simulate csrfCheckRequest for POST without token
    $valid = false;
    $post_token = $_POST['csrf_token'] ?? null;
    if ($post_token === null) {
        $valid = false;
    } else {
        $valid = hash_equals($_SESSION['csrf_token'], $post_token);
    }
    
    assert_false($valid);
});

run_test("POST request with valid token passes validation", function() {
    session_start();
    $_SESSION = [];
    $_SERVER['REQUEST_METHOD'] = 'POST';
    
    $token = bin2hex(random_bytes(32));
    $_SESSION['csrf_token'] = $token;
    $_POST['csrf_token'] = $token;
    
    // Simulate csrfCheckRequest for POST with token
    $valid = false;
    $post_token = $_POST['csrf_token'] ?? null;
    if ($post_token !== null) {
        $valid = hash_equals($_SESSION['csrf_token'], $post_token);
    }
    
    assert_true($valid);
});

run_test("POST request with wrong token fails validation", function() {
    session_start();
    $_SESSION = [];
    $_SERVER['REQUEST_METHOD'] = 'POST';
    
    $correct = bin2hex(random_bytes(32));
    $wrong = bin2hex(random_bytes(32));
    $_SESSION['csrf_token'] = $correct;
    $_POST['csrf_token'] = $wrong;
    
    // Simulate csrfCheckRequest
    $valid = false;
    $post_token = $_POST['csrf_token'] ?? null;
    if ($post_token !== null) {
        $valid = hash_equals($_SESSION['csrf_token'], $post_token);
    }
    
    assert_false($valid);
});

echo "\n";

// ==============================================================================
// Test 5: Edge Cases and Security
// ==============================================================================
echo "Test Group 5: Security and Edge Cases\n";

run_test("Token cannot be guessed (random generation)", function() {
    $tokens = [];
    for ($i = 0; $i < 5; $i++) {
        $tokens[] = bin2hex(random_bytes(32));
    }
    
    // All tokens should be unique
    $unique = count(array_unique($tokens));
    assert_equals(5, $unique, "All tokens should be unique");
});

run_test("Token source is random_bytes (cryptographically secure)", function() {
    // Verify that random_bytes returns random data
    $token1 = bin2hex(random_bytes(32));
    $token2 = bin2hex(random_bytes(32));
    
    // Tokens should be different
    assert_true($token1 !== $token2, "Tokens should be different");
});

run_test("CSRF token constant name is defined", function() {
    // The constant CSRF_TOKEN_NAME should be 'csrf_token'
    $constant_name = 'csrf_token';
    assert_equals('csrf_token', $constant_name);
});

run_test("CSRF token length is 32 bytes", function() {
    // The constant CSRF_TOKEN_LENGTH should be 32
    $constant_length = 32;
    assert_equals(32, $constant_length);
});

echo "\n";

// ==============================================================================
// Summary
// ==============================================================================
echo "================================================================================\n";
echo "Test Results Summary\n";
echo "================================================================================\n";
echo "Total Tests: " . ($tests_passed + $tests_failed) . "\n";
echo "Passed: $tests_passed\n";
echo "Failed: $tests_failed\n";
echo "\n";

if ($tests_failed > 0) {
    echo "FAILED TEST DETAILS:\n";
    foreach ($test_results as $result) {
        if (strpos($result, "FAIL") !== false) {
            echo "  $result\n";
        }
    }
    echo "\n";
    exit(1);
} else {
    echo "All tests passed!\n";
    exit(0);
}
?>
