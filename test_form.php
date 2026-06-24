<?php
/**
 * test_form.php - Test the new Form library standalone
 * 
 * Run from bbsengine6/php directory:
 * cd /home/opencode/data/work/bbsengine6/php && php ../test_form.php
 */

require_once("/srv/www/bbsengine6/php/bootstrap.php");

require_once("Form/Form.php");
require_once("Form/Element.php");
require_once("Form/Rule/Rule.php");
require_once("Form/Rule/RuleRegistry.php");
require_once("Form/Rule/Required.php");
require_once("Form/Rule/Callback.php");
require_once("Form/Rule/Regex.php");
require_once("Form/Rule/Equals.php");
require_once("Form/Rule/NonEmpty.php");
require_once("Form/DataSource/Array.php");
require_once("Form/DataSource/PdoDataSource.php");
require_once("Form/Renderer/ArrayRenderer.php");
require_once("Form/Captcha/CaptchaProvider.php");
require_once("Form/Captcha/Factory.php");
require_once("Form/Captcha/Turnstile.php");
require_once("Form/Captcha/Hcaptcha.php");
require_once("Form/Captcha/Recaptcha.php");
require_once("Form/Captcha/None.php");

// Mock session functions
if (!function_exists('bbsengine6\util\csrfGetToken')) {
    function csrfGetToken() { return 'test-token-123'; }
}
if (!function_exists('bbsengine6\util\csrfCheckRequest')) {
    function csrfCheckRequest() { return true; }
}
if (!function_exists('bbsengine6\util\logentry')) {
    function logentry($msg) { echo "LOG: $msg\n"; }
}

// Mock config constants
if (!defined('config\CAPTCHA_PROVIDER')) {
    define("config\CAPTCHA_PROVIDER", 'none');
}
if (!defined('config\TURNSTILE_SITE_KEY')) {
    define("config\TURNSTILE_SITE_KEY", '');
}
if (!defined('config\TURNSTILE_SECRET_KEY')) {
    define("config\TURNSTILE_SECRET_KEY", '');
}
if (!defined('config\HCAPTCHA_SITE_KEY')) {
    define("config\HCAPTCHA_SITE_KEY", '');
}
if (!defined('config\HCAPTCHA_SECRET_KEY')) {
    define("config\HCAPTCHA_SECRET_KEY", '');
}
if (!defined('config\RECAPTCHA_SITE_KEY')) {
    define("config\RECAPTCHA_SITE_KEY", '');
}
if (!defined('config\RECAPTCHA_SECRET_KEY')) {
    define("config\RECAPTCHA_SECRET_KEY", '');
}

// Mock superglobals for testing
$_SERVER['REQUEST_METHOD'] = 'GET';
$_POST = [];
$_GET = [];

echo "=== Testing bbsengine6 Form Library ===\n\n";

// Test 1: Basic form creation
echo "Test 1: Basic form creation\n";
echo str_repeat("-", 40) . "\n";

$form = new \bbsengine6\Form\Form("test-form", "post", ["action" => "/test"]);
$form->setAttribute("enctype", "multipart/form-data");
$form->addHidden("mode")->setValue("NEEDINFO");
$form->addHidden("id")->setValue("NEEDINFO");
$form->addHidden("memberid")->setValue("NEEDINFO");
$form->addHidden("token")->setValue(csrfGetToken());
$form->addRecursiveFilter("trim");

echo "Created form: " . $form->getId() . "\n";
echo "Method: " . $form->getMethod() . "\n";
echo "Action: " . $form->getAttribute('action') . "\n\n";

// Test 2: Add elements
echo "Test 2: Add elements\n";
echo str_repeat("-", 40) . "\n";

$fieldset = $form->addElement("fieldset");
$fieldset->setLabel("Test Fieldset");

$textField = $fieldset->addElement("text", "username");
$textField->setLabel("Username");
$textField->addRule("required", "Username is required");
$textField->addRule("regex", "Username must be alphanumeric", '/^[a-zA-Z0-9_]+$/');

$passwordField = $fieldset->addElement("password", "password");
$passwordField->setLabel("Password");
$passwordField->addRule("required", "Password is required");

$hiddenField = $form->addHidden("token", "test-token-123");
echo "Added fieldset: " . $fieldset->getLabel() . "\n";
echo "Added text field: " . $textField->getName() . "\n";
echo "Added password field: " . $passwordField->getName() . "\n";
echo "Added hidden field: " . $hiddenField->getName() . " = " . $hiddenField->getValue() . "\n\n";

// Test 3: Test validation - empty form (should fail)
echo "Test 3: Validation with empty POST\n";
echo str_repeat("-", 40) . "\n";

$_SERVER['REQUEST_METHOD'] = 'POST';
$_POST = [
    'test-form' => '1',
    'mode' => 'NEEDINFO',
    'id' => 'NEEDINFO',
    'memberid' => 'NEEDINFO',
    'token' => 'test-token-123',
    'username' => '',
    'password' => '',
];

$form2 = new \bbsengine6\Form\Form("test-form-2", "post", ["action" => "/test"]);
$form2->addHidden("mode")->setValue("NEEDINFO");
$form2->addHidden("id")->setValue("NEEDINFO");
$form2->addHidden("memberid")->setValue("NEEDINFO");
$form2->addHidden("token")->setValue("test-token-123");

$fs = $form2->addElement("fieldset");
$fs->setLabel("Login");
$u = $fs->addElement("text", "username");
$u->setLabel("Username");
$u->addRule("required", "Username is required");
$p = $fs->addElement("password", "password");
$p->setLabel("Password");
$p->addRule("required", "Password is required");

$isSubmitted = $form2->isSubmitted();
$isValid = $form2->validate();
echo "isSubmitted: " . ($isSubmitted ? "true" : "false") . "\n";
echo "validate(): " . ($isValid ? "true" : "false") . "\n";

$errors = $form2->getErrors();
echo "Errors count: " . count($errors) . "\n";
foreach ($errors as $field => $error) {
    echo "  - $field: $error\n";
}
echo "\n";

// Test 4: Test validation - valid data (should pass)
echo "Test 4: Validation with valid POST\n";
echo str_repeat("-", 40) . "\n";

$_POST = [
    'test-form-2' => '1',
    'mode' => 'NEEDINFO',
    'id' => 'NEEDINFO',
    'memberid' => 'NEEDINFO',
    'token' => 'test-token-123',
    'username' => 'testuser',
    'password' => 'password123',
];

$form3 = new \bbsengine6\Form\Form("test-form-3", "post", ["action" => "/test"]);
$form3->addHidden("mode")->setValue("NEEDINFO");
$form3->addHidden("id")->setValue("NEEDINFO");
$form3->addHidden("memberid")->setValue("NEEDINFO");
$form3->addHidden("token")->setValue("test-token-123");

$fs3 = $form3->addElement("fieldset");
$fs3->setLabel("Login");
$u3 = $fs3->addElement("text", "username");
$u3->setLabel("Username");
$u3->addRule("required", "Username is required");
$u3->addRule("regex", "Username must be alphanumeric", '/^[a-zA-Z0-9_]+$/');
$p3 = $fs3->addElement("password", "password");
$p3->setLabel("Password");
$p3->addRule("required", "Password is required");

$isSubmitted3 = $form3->isSubmitted();
$isValid3 = $form3->validate();
echo "isSubmitted: " . ($isSubmitted3 ? "true" : "false") . "\n";
echo "validate(): " . ($isValid3 ? "true" : "false") . "\n";

$errors3 = $form3->getErrors();
echo "Errors count: " . count($errors3) . "\n";
echo "\n";

// Test 5: Rendering
echo "Test 5: Form rendering\n";
echo str_repeat("-", 40) . "\n";

$form4 = new \bbsengine6\Form\Form("test-form-4", "post", ["action" => "/test"]);
$form4->addHidden("mode")->setValue("NEEDINFO");
$form4->addHidden("id")->setValue("NEEDINFO");
$form4->addHidden("memberid")->setValue("NEEDINFO");

$fs4 = $form4->addElement("fieldset");
$fs4->setLabel("Test");
$fs4->addElement("text", "name")->setLabel("Name");
$fs4->addElement("password", "pass")->setLabel("Password");
$fs4->addElement("submit", "submit", ["value" => "Go"]);

$renderer = \bbsengine6\Form\Renderer\ArrayRenderer::create();
$form4->render($renderer);
$output = $renderer->toArray();

echo "Form ID: " . $output['id'] . "\n";
echo "Method: " . $output['method'] . "\n";
echo "Elements count: " . count($output['elements']) . "\n";
echo "Required note: " . $output['required_note'] . "\n\n";

// Test 6: CAPTCHA factory
echo "Test 6: CAPTCHA Factory\n";
echo str_repeat("-", 40) . "\n";

$captcha = \bbsengine6\Form\Captcha\Factory::create('none');
echo "Provider (none): " . get_class($captcha) . "\n";
echo "Site key: '" . $captcha->getSiteKey() . "'\n";
echo "Rendered: '" . $captcha->render() . "'\n";
echo "Verify (empty token): " . ($captcha->verify('') ? "true" : "false") . "\n\n";

// Test 7: Rule Registry
echo "Test 7: Rule Registry\n";
echo str_repeat("-", 40) . "\n";

// Built-in rules are hardcoded in getBuiltIn, not in the registry
echo "Built-in rules: required, callback, regex, eq, nonempty\n";
echo "Is 'required' registered (custom): " . (\bbsengine6\Form\Rule\RuleRegistry::isRegistered('required') ? "yes" : "no") . "\n";
echo "Resolve 'required': " . \bbsengine6\Form\Rule\RuleRegistry::resolve('required') . "\n\n";

// Test 8: Custom rule registration
echo "Test 8: Custom rule registration\n";
echo str_repeat("-", 40) . "\n";

class CustomRule extends \bbsengine6\Form\Rule\Rule {
    public function validate(mixed $value, array $formValues = []): bool {
        return $value === 'secret';
    }
}

\bbsengine6\Form\Rule\RuleRegistry::register('custom', CustomRule::class);
echo "Registered custom rule: custom -> CustomRule\n";
echo "Is 'custom' registered: " . (\bbsengine6\Form\Rule\RuleRegistry::isRegistered('custom') ? "yes" : "no") . "\n";
echo "Resolved class: " . \bbsengine6\Form\Rule\RuleRegistry::resolve('custom') . "\n\n";

// Test 9: Test custom rule
echo "Test 9: Test custom rule\n";
echo str_repeat("-", 40) . "\n";

$form5 = new \bbsengine6\Form\Form("test-form-5", "post", ["action" => "/test"]);
$fs5 = $form5->addElement("fieldset");
$code = $fs5->addElement("text", "code");
$code->setLabel("Secret Code");
$code->addRule("custom", "Code must be 'secret'");

$_POST = [
    'test-form-5' => '1',
    'code' => 'wrong',
];

$form5->validate();
$errors5 = $form5->getErrors();
echo "Code 'wrong' - valid: " . (count($errors5) === 0 ? "yes" : "no") . "\n";
echo "Error: " . ($errors5['code'] ?? 'none') . "\n";

$_POST['code'] = 'secret';
$form5->validate();
$errors5 = $form5->getErrors();
echo "Code 'secret' - valid: " . (count($errors5) === 0 ? "yes" : "no") . "\n\n";

echo "=== All tests completed ===\n";

echo "\n=== Test 10: PdoDataSource ===\n";
echo str_repeat("-", 40) . "\n";

$pdo = new \PDO("sqlite::memory:");
$pdo->exec("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, email TEXT)");

$pdo->exec("INSERT INTO users (id, username, email) VALUES (1, 'alice', 'alice@example.com')");
$pdo->exec("INSERT INTO users (id, username, email) VALUES (2, 'bob', 'bob@example.com')");

$ds = new \bbsengine6\Form\DataSource\PdoDataSource(
    $pdo,
    "SELECT username, email FROM users WHERE id = :id",
    ["id" => 1]
);

echo "hasValue('username'): " . ($ds->hasValue("username") ? "yes" : "no") . "\n";
echo "getValue('username'): " . $ds->getValue("username") . "\n";
echo "getValue('email'): " . $ds->getValue("email") . "\n";
echo "getValue('nonexistent'): " . ($ds->getValue("nonexistent") ?? "null") . "\n";
echo "getRowCount(): " . $ds->getRowCount() . "\n";

$ds2 = new \bbsengine6\Form\DataSource\PdoDataSource(
    $pdo,
    "SELECT id, username FROM users"
);
echo "getAllRows() count: " . count($ds2->getAllRows()) . "\n";

$ds3 = new \bbsengine6\Form\DataSource\PdoDataSource(
    $pdo,
    "SELECT * FROM users WHERE id = :id",
    ["id" => 999]
);
echo "Non-existent row - getRowCount(): " . $ds3->getRowCount() . "\n";
echo "Non-existent row - hasValue('username'): " . ($ds3->hasValue("username") ? "yes" : "no") . "\n";

$form6 = new \bbsengine6\Form\Form("test-form-6", "post", ["action" => "/test"]);
$fs6 = $form6->addElement("fieldset");
$username = $fs6->addElement("text", "username");
$username->setLabel("Username");
$email = $fs6->addElement("text", "email");
$email->setLabel("Email");

$form6->addDataSource($ds);
$form6->populateFromDataSources();

echo "Form values after datasource:\n";
echo "  username: " . ($username->getValue() ?? "null") . "\n";
echo "  email: " . ($email->getValue() ?? "null") . "\n";

echo "\n=== PdoDataSource tests completed ===\n";
