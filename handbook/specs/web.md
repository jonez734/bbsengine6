# bbsengine6 Web Layer Specification

**Version:** 0.0.1.dev  
**Last Updated:** 2026-02-23

This document describes the complete web layer architecture, including PHP endpoints, Smarty template integration, JavaScript interaction, and connection to the Python backend.

## Table of Contents

1. [Web Layer Architecture](#web-layer-architecture)
2. [PHP Module Specifications](#php-module-specifications)
3. [HTTP Endpoints](#http-endpoints)
4. [Smarty Template System](#smarty-template-system)
5. [JavaScript Integration](#javascript-integration)
6. [Request/Response Lifecycle](#requestresponse-lifecycle)
7. [Web-to-Python Integration](#web-to-python-integration)

---

## Web Layer Architecture

The web layer provides HTTP access to bbsengine6 functionality through Apache web server and PHP.

### Component Stack

```
Browser (HTTP Client)
     ↓
Apache Web Server (www.conf, .htaccess)
     ↓
PHP Request Handler (index.php, login.php, etc.)
     ↓
PHP Engine (engine.php)
     ↓ ┌─ Smarty Template Engine (skin/tmpl/)
     ├─ PHP Database Layer (database.php)
     ├─ PHP Session Layer (session.php)
     └─ PHP Member Library (libmember.php)
     ↓
PostgreSQL Database
     
Optional:
JavaScript (client-side)
     ↓
jQuery / AJAX
     ↓
PHP Endpoints (JSON responses)
```

### Architecture Diagram

```
┌────────────────────────────────────────────────────────────┐
│                 Web Browser                                │
│ (HTML rendering, JavaScript execution, CSS styling)        │
└──────────────────────────┬─────────────────────────────────┘
                           │ HTTP Request
                           ▼
┌────────────────────────────────────────────────────────────┐
│              Apache Web Server                             │
│ ├─ /www/org/index.php                                      │
│ ├─ /www/org/login.php                                      │
│ ├─ /www/org/register.php                                   │
│ ├─ /www/org/handbook.php                                   │
│ ├─ /www/org/post.php                                       │
│ ├─ /www/org/archive.php                                    │
│ └─ [various other endpoints]                               │
│                                                             │
│ .htaccess: URL rewriting, routing, security headers        │
└──────────────────────────┬─────────────────────────────────┘
                           │
                           ▼
┌────────────────────────────────────────────────────────────┐
│              PHP Application Layer                         │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ engine.php (Main engine)                             │ │
│  │  ├─ Bootstrap configuration                          │ │
│  │  ├─ Session initialization                           │ │
│  │  ├─ Page routing & template loading                  │ │
│  │  ├─ Data assembly for templates                      │ │
│  │  └─ Response rendering                               │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ database.php │  │ session.php   │  │libmember.php │    │
│  │              │  │               │  │              │    │
│  │ - connect()  │  │ - start()     │  │- getbyid()   │    │
│  │ - query()    │  │ - login()     │  │- getbylogin()    │
│  │ - fetch()    │  │ - logout()    │  │- authenticate()  │
│  │ - insert()   │  │ - getcurrent()│  │- getflags()      │
│  │ - update()   │  │               │  │              │    │
│  │ - delete()   │  │               │  │              │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ util.php (Utilities)                                 │ │
│  │  ├─ toboolean()                                      │ │
│  │  ├─ pluralize()                                      │ │
│  │  ├─ formatdate()                                     │ │
│  │  ├─ escaphtml()                                      │ │
│  │  └─ [other utilities]                                │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐ │
│  │ Input Helpers (HTML_QuickForm2 extensions)           │ │
│  │  ├─ InputDate.php                                    │ │
│  │  ├─ InputDateTime.php                                │ │
│  │  ├─ InputEmail.php                                   │ │
│  │  └─ InputUrl.php                                     │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                             │
└──────────────────────────┬─────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
    ┌─────────┐    ┌──────────────┐   ┌─────────────┐
    │ Smarty  │    │ PostgreSQL   │   │ JavaScript  │
    │Template │    │ Database     │   │ (client)    │
    │ Engine  │    │              │   │             │
    └─────────┘    └──────────────┘   └─────────────┘
```

---

## PHP Module Specifications

### engine.php - Main PHP Engine

**Purpose:** Central request handler, page rendering, template integration

**File Size:** 1506 lines

**Namespace:** `bbsengine6`

#### Key Classes & Functions

```php
/**
 * Display a page with Smarty template rendering
 * 
 * @param string $page Page name (maps to template file)
 * @param array $data Data to pass to template
 * @return void
 */
function displaypage($page, $data = array()) : void
  "Maps page name to Smarty template and renders with data"
  "Template resolution: skin/tmpl/{page}.tpl"
  "Executes: load template → apply data → render → echo HTML"

/**
 * Set the current site context
 * 
 * @param string $site Site name ('org', 'com', etc.)
 * @return void
 */
function setcurrentsite($site) : void
  "Set which site is currently being accessed"
  "Used for multi-site deployments"

/**
 * Get the current site context
 * 
 * @return string Site name
 */
function getcurrentsite() : string
  "Return current site name"

/**
 * Initialize Smarty template engine
 * 
 * @return Smarty Smarty instance
 */
function initsmarty() : Smarty
  "Create and configure Smarty instance"
  "Sets: template dir, cache dir, compile dir, plugins dir"
  "Registers: custom modifiers, functions, plugins"

/**
 * Get Smarty instance
 * 
 * @return Smarty Smarty instance
 */
function getsmarty() : Smarty
  "Return cached Smarty instance"
```

**Dependencies:**
- Smarty >= 3.0
- PEAR Log
- HTML_QuickForm2
- libmember.php
- database.php
- util.php

**Request Lifecycle:**
```
1. PHP script included engine.php
2. engine.php requires bootstrap.php
3. Database connection initialized
4. Session started
5. displaypage($page, $data) called
6. Smarty template loaded and compiled
7. Data passed to template
8. HTML rendered and sent to browser
```

---

### database.php - PHP Database Layer

**Purpose:** PostgreSQL query execution, connection management

**File Size:** ~300 lines

#### Functions

```php
/**
 * Execute a database query
 * 
 * @param string $sql SQL query string
 * @param array $params Query parameters
 * @return PDOStatement
 */
function query($sql, $params = array()) : PDOStatement
  "Execute SELECT/INSERT/UPDATE/DELETE query"
  "Uses prepared statements for security"

/**
 * Fetch single row as associative array
 * 
 * @param string $sql SQL query
 * @param array $params Query parameters
 * @return array|false
 */
function fetch($sql, $params = array())
  "Execute query and return first row or false"

/**
 * Fetch all rows
 * 
 * @param string $sql SQL query
 * @param array $params Query parameters
 * @return array Array of rows
 */
function fetchall($sql, $params = array()) : array
  "Execute query and return all rows"

/**
 * Insert record
 * 
 * @param string $table Table name
 * @param array $data Column → value map
 * @return int|false Last insert ID or false
 */
function insert($table, $data)
  "Build INSERT statement and execute"
  "Returns: LASTVAL() or false on error"

/**
 * Update record
 * 
 * @param string $table Table name
 * @param array $data Columns to update
 * @param array $where WHERE conditions
 * @return int Number of rows updated
 */
function update($table, $data, $where) : int
  "Build UPDATE statement and execute"

/**
 * Delete record
 * 
 * @param string $table Table name
 * @param array $where WHERE conditions
 * @return int Number of rows deleted
 */
function delete($table, $where) : int
  "Build DELETE statement and execute"

/**
 * Get PostgreSQL connection
 * 
 * @return PDO PostgreSQL connection
 */
function getconnection() : PDO
  "Return database connection (creates if needed)"

/**
 * Begin transaction
 * 
 * @return void
 */
function beginTransaction() : void
  "Start database transaction"

/**
 * Commit transaction
 * 
 * @return void
 */
function commit() : void
  "Commit current transaction"

/**
 * Rollback transaction
 * 
 * @return void
 */
function rollback() : void
  "Rollback current transaction"
```

**Security Features:**
- Prepared statements with parameter binding
- SQL injection prevention
- Error handling with proper exception catching

**Configuration:**
```php
define('DB_HOST', getenv('BBSENGINE_DB_HOST') ?: 'localhost');
define('DB_PORT', getenv('BBSENGINE_DB_PORT') ?: 5432);
define('DB_NAME', getenv('BBSENGINE_DB_NAME') ?: 'bbsengine');
define('DB_USER', getenv('BBSENGINE_DB_USER') ?: 'bbsengine');
define('DB_PASS', getenv('BBSENGINE_DB_PASSWORD') ?: '');
```

---

### session.php - PHP Session Management

**Purpose:** HTTP session handling, member authentication

**File Size:** ~200 lines

#### Functions

```php
/**
 * Start PHP session
 * 
 * @return bool
 */
function start() : bool
  "Initialize session, check authentication"
  "Returns: true if session started, false on error"

/**
 * Authenticate and log in user
 * 
 * @param string $loginid Login ID
 * @param string $password Password (plaintext)
 * @return bool
 */
function login($loginid, $password) : bool
  "Authenticate credentials and create session"
  "Sets: $_SESSION['memberid'], $_SESSION['moniker']"

/**
 * Log out user
 * 
 * @return bool
 */
function logout() : bool
  "Destroy session and clear cookies"

/**
 * Check if user is logged in
 * 
 * @return bool
 */
function isloggedin() : bool
  "Return true if session has valid memberid"

/**
 * Get logged-in member ID
 * 
 * @return int|null Member ID or null
 */
function getcurrentmemberid() : ?int
  "Return $_SESSION['memberid'] or null"

/**
 * Get logged-in member moniker
 * 
 * @return string|null
 */
function getcurrentmoniker() : ?string
  "Return $_SESSION['moniker'] or null"

/**
 * Get full member object
 * 
 * @return array|null Member array or null
 */
function getcurrentmember() : ?array
  "Return full member record with all data"
```

**Session Variables Stored:**
```php
$_SESSION = array(
  'memberid' => 123,
  'moniker' => 'john.doe',
  'loginid' => 'john.doe',
  'email' => 'john@example.com',
  'flags' => array(
    'admin' => false,
    'moderator' => false,
    'verified' => true
  ),
  'started' => 1708700400,  // Unix timestamp
  'lastactivity' => 1708700400
);
```

**Cookie Settings:**
```php
session_set_cookie_params([
  'lifetime' => 3600,           // 1 hour
  'path' => '/',
  'domain' => '.bbsengine.org',
  'secure' => true,
  'httponly' => true,
  'samesite' => 'Lax'
]);
```

---

### libmember.php - Member Utilities

**Purpose:** Member lookup, authentication, permissions

**File Size:** ~250 lines

#### Functions

```php
/**
 * Authenticate member by credentials
 * 
 * @param string $loginid Login ID
 * @param string $password Password (plaintext)
 * @return array|false Member array if valid, false otherwise
 */
function authenticate($loginid, $password)
  "Look up member by loginid and verify password"
  "Returns: member record array or false"

/**
 * Get member by ID
 * 
 * @param int $memberid Member ID
 * @return array|false
 */
function getbyid($memberid)
  "Query member by primary key"
  "Returns: member array or false"

/**
 * Get member by login ID
 * 
 * @param string $loginid Login ID
 * @return array|false
 */
function getbyloginid($loginid)
  "Query member by unique login ID"
  "Returns: member array or false"

/**
 * Get member by moniker
 * 
 * @param string $moniker Display name
 * @return array|false
 */
function getbymoniker($moniker)
  "Query member by display name"
  "Returns: member array or false"

/**
 * Get member flags (permissions)
 * 
 * @param string $moniker Member moniker
 * @return array Flags array
 */
function getflags($moniker) : array
  "Return member's permission flags"
  "Example: array('admin' => false, 'moderator' => true)"

/**
 * Check if member has flag
 * 
 * @param string $moniker Member moniker
 * @param string $flag Flag name
 * @return bool
 */
function hasflag($moniker, $flag) : bool
  "Return true if member has flag enabled"

/**
 * Create new member
 * 
 * @param array $data Member data (loginid, moniker, email, password)
 * @return int|false Member ID or false
 */
function create($data)
  "Insert new member record"
  "Requires: loginid, moniker, email, password (plaintext, will be hashed)"

/**
 * Update member
 * 
 * @param int $memberid Member ID
 * @param array $data Columns to update
 * @return bool
 */
function update($memberid, $data) : bool
  "Update member record"

/**
 * Delete member
 * 
 * @param int $memberid Member ID
 * @return bool
 */
function delete($memberid) : bool
  "Delete member account"

/**
 * Hash password
 * 
 * @param string $password Plaintext password
 * @return string Bcrypt hash
 */
function hashpassword($password) : string
  "Hash password with bcrypt"

/**
 * Verify password
 * 
 * @param string $password Plaintext password
 * @param string $hash Stored hash
 * @return bool
 */
function verifypassword($password, $hash) : bool
  "Verify plaintext password against stored hash"
```

**Member Data Structure:**
```php
$member = array(
  'id' => 123,
  'loginid' => 'john.doe',
  'moniker' => 'John Doe',
  'email' => 'john@example.com',
  'password' => '$2y$10$...',  // bcrypt hash
  'credits' => 500,
  'flags' => array(
    'admin' => false,
    'moderator' => false,
    'verified' => true
  ),
  'attrs' => array(
    'bio' => 'Software developer',
    'signature' => 'John Doe'
  ),
  'ui' => array('term', 'web'),
  'datecreated' => '2026-01-01T00:00:00',
  'dateupdated' => '2026-02-23T18:40:00',
  'lastlogin' => '2026-02-23T18:40:00'
);
```

---

### util.php - PHP Utilities

**Purpose:** Helper functions for common operations

#### Functions

```php
function toboolean($value) : bool
  "Convert value to boolean (y/n, true/false, 1/0)"

function pluralize($amount, $singular, $plural) : string
  "Return singular or plural form"
  "Example: pluralize(5, 'message', 'messages') → '5 messages'"

function formatdate($timestamp, $format = 'Y-m-d H:i:s') : string
  "Format timestamp as string"

function formatdatetime($timestamp) : string
  "Format as datetime (e.g., '2026-02-23 06:40 PM')"

function escapehtml($text) : string
  "HTML escape special characters"

function striphtml($text) : string
  "Remove HTML tags"

function truncate($text, $length = 100, $suffix = '...') : string
  "Truncate text to length with ellipsis"

function slugify($text) : string
  "Convert text to URL slug (lowercase, hyphenated)"

function sanitize($text) : string
  "Remove potentially dangerous characters"

function sendmail($to, $subject, $body, $headers = array()) : bool
  "Send email message"

function random_string($length = 32) : string
  "Generate random string for tokens, nonces"
```

---

### Input Helper Classes

#### InputDate.php

```php
class InputDate extends HTML_QuickForm2_Element_Input
  "HTML5 date input element"
  
  Properties:
    type = 'date'
    format = 'Y-m-d'
    
  Methods:
    getValue() : string
      "Return date value in YYYY-MM-DD format"
    
    setValue($value) : void
      "Set date value"
    
    validate() : bool
      "Validate date is valid"
```

#### InputDateTime.php

```php
class InputDateTime extends HTML_QuickForm2_Element_Input
  "HTML5 datetime-local input element"
  
  Properties:
    type = 'datetime-local'
    format = 'Y-m-d\TH:i'
    
  Methods:
    getValue() : string
      "Return datetime value in ISO 8601 format"
    
    validate() : bool
      "Validate datetime is valid"
```

#### InputEmail.php

```php
class InputEmail extends HTML_QuickForm2_Element_Input
  "HTML5 email input with server-side validation"
  
  Properties:
    type = 'email'
    
  Methods:
    validate() : bool
      "Validate email format and optionally verify delivery"
```

#### InputUrl.php

```php
class InputUrl extends HTML_QuickForm2_Element_Input
  "HTML5 URL input with validation"
  
  Properties:
    type = 'url'
    
  Methods:
    validate() : bool
      "Validate URL format"
```

---

## HTTP Endpoints

### Endpoint: /index.php - Homepage

**Method:** GET  
**Authentication:** Optional

**Purpose:** Display homepage with site information, login prompt, news feed

**Parameters:**
- None required

**Response:**
- HTML page with header, navigation, content area, footer
- JavaScript injected for interactivity
- Stylesheets linked from skin/

**Template:** `skin/tmpl/index.tpl`

**Smarty Variables:**
```php
$data = array(
  'site_title' => 'BBSEngine.org',
  'site_description' => 'A classic Bulletin Board System',
  'featured_posts' => array(...),
  'recent_activity' => array(...),
  'is_logged_in' => bool,
  'current_member' => array(...)
);
```

---

### Endpoint: /login.php - User Login

**Method:** GET (display form) | POST (submit credentials)

**Authentication:** None required

**Purpose:** Authenticate user and create session

**GET Parameters:**
- `redirect` - URL to redirect to after login (optional)

**POST Parameters:**
- `loginid` - Username
- `password` - Password (HTTPS only)
- `remember` - Keep logged in (sets longer cookie) (optional)

**Response (GET):**
- HTML login form with email and password inputs
- Remember me checkbox
- Link to registration page

**Response (POST Success):**
- Redirect to home or `redirect` parameter
- Set session cookies

**Response (POST Failure):**
- Reload form with error message
- No sensitive information in error (for security)

**Template:** `skin/tmpl/login.tpl`

**PHP Code Flow:**
```php
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
  $loginid = $_POST['loginid'] ?? null;
  $password = $_POST['password'] ?? null;
  
  if (libmember\authenticate($loginid, $password)) {
    session\login($loginid, $password);
    $redirect = $_GET['redirect'] ?? '/index.php';
    header("Location: {$redirect}");
  } else {
    $error = 'Invalid login ID or password';
    engine\displaypage('login', array('error' => $error));
  }
}
```

---

### Endpoint: /register.php - User Registration

**Method:** GET (display form) | POST (submit registration)

**Authentication:** None required

**Purpose:** Create new user account

**POST Parameters:**
- `loginid` - Username (alphanumeric, 3-32 chars)
- `moniker` - Display name
- `email` - Email address (validated)
- `password` - Password (min 8 chars)
- `password_confirm` - Password confirmation
- `captcha` - CAPTCHA response (reCAPTCHA v3)

**Response (GET):**
- HTML registration form
- CAPTCHA widget
- Link to login page

**Response (POST Success):**
- Account created
- Confirmation email sent
- Redirect to login page

**Response (POST Failure):**
- Validation errors displayed
- Form prefilled with submitted data

**Validation:**
- loginid: unique, alphanumeric + underscore, 3-32 chars
- moniker: 1-64 chars
- email: valid format, verified deliverable
- password: minimum 8 characters
- CAPTCHA: score > 0.5

**Template:** `skin/tmpl/register.tpl`

---

### Endpoint: /post.php - Create/View Posts

**Method:** GET (view/reply form) | POST (submit post)

**Authentication:** Required (member login)

**Purpose:** View message thread and post reply

**GET Parameters:**
- `id` - Message/thread ID
- `folder` - Folder ID (optional)

**POST Parameters:**
- `parentid` - Parent message ID
- `subject` - Post subject
- `body` - Post content
- `to` - Recipient (optional)

**Response (GET):**
- Message thread with parent and replies
- Reply form at bottom

**Response (POST):**
- Validate content
- Insert new blurb/message
- Redirect to thread view

**Template:** `skin/tmpl/post.tpl`

---

### Endpoint: /handbook.php - Documentation

**Method:** GET

**Authentication:** Optional

**Purpose:** Display handbook documentation

**GET Parameters:**
- `chapter` - Chapter ID (e.g., 'getting-started')
- `section` - Section within chapter (optional)

**Response:**
- HTML documentation page
- Table of contents sidebar
- Navigation breadcrumbs

**Template:** `skin/tmpl/handbook.tpl`

**Data Sources:**
- Static handbook markdown converted to HTML
- Or dynamically loaded from /handbook/ directory

---

### Endpoint: /archive.php - Message Archive

**Method:** GET

**Authentication:** Optional

**Purpose:** Browse archived messages

**GET Parameters:**
- `folder` - Folder ID
- `page` - Page number (for pagination)
- `sort` - Sort field (date, author, subject)
- `order` - ASC or DESC

**Response:**
- Paginated list of messages
- Search/filter options

**Template:** `skin/tmpl/archive.tpl`

**Query:**
```sql
SELECT * FROM engine.__blurb
WHERE folderid = ?
ORDER BY {sort} {order}
LIMIT 20 OFFSET (page - 1) * 20
```

---

### Endpoint: /download.php - File Downloads

**Method:** GET

**Authentication:** Optional (depends on file)

**Purpose:** Serve downloadable files

**GET Parameters:**
- `file` - File ID or filename (sanitized)

**Response:**
- Binary file data with appropriate headers
- Content-Type set based on extension
- Content-Disposition: attachment

**Security:**
- Path traversal prevention (sanitize filename)
- Authentication check per file
- Logging of downloads

---

### Endpoint: /gencaptchaimage.php - CAPTCHA Generation

**Method:** GET

**Authentication:** None

**Purpose:** Generate CAPTCHA image for form validation

**Response:**
- PNG image with distorted text
- Session stores answer for validation

**Alternative:**
- Can use reCAPTCHA v3 instead (no image needed)

---

### Endpoint: /bbsenginedotorg.php - Engine Info

**Method:** GET

**Authentication:** None

**Purpose:** Display information about bbsengine6

**Response:**
- Features overview
- Architecture description
- Download links
- Links to this documentation

**Template:** `skin/tmpl/bbsenginedotorg.tpl`

---

## Smarty Template System

### Template Directory Structure

```
skin/tmpl/
├── index.tpl              # Homepage
├── login.tpl              # Login form
├── register.tpl           # Registration form
├── post.tpl               # Message view/reply
├── handbook.tpl           # Documentation
├── archive.tpl            # Message archive
├── layout.tpl             # Master layout
├── header.tpl             # Page header
├── footer.tpl             # Page footer
├── topbar.tpl             # Navigation bar
├── sidebars/
│   ├── left.tpl
│   └─ right.tpl
└─ components/
    ├─ message.tpl        # Message display
    ├─ form.tpl           # Form rendering
    └─ pagination.tpl     # Pagination controls
```

### Smarty Syntax & Features

**Variable Substitution:**
```smarty
{$variable}
{$array['key']}
{$object->property}
{$smarty.session.memberid}  # Session variable
```

**Conditionals:**
```smarty
{if $is_logged_in}
  Welcome back, {$current_member.moniker}!
{else}
  Please <a href="/login.php">log in</a>
{/if}
```

**Loops:**
```smarty
{foreach from=$messages item=$msg}
  <div class="message">
    <strong>{$msg.from}</strong>: {$msg.subject}
  </div>
{/foreach}
```

**Custom Modifiers:**
```smarty
{$text|markdown}    # Convert markdown to HTML
{$value|wpprop}     # WordPress-style property formatting
```

**Custom Functions:**
```smarty
{teos var="username"}  # Custom TEOS function
```

### Template Variables Passed from PHP

**Available in All Templates:**
```php
$smarty->assign(array(
  'site_name' => 'BBSEngine.org',
  'is_logged_in' => bool,
  'current_member' => array(...),
  'current_page' => 'index',
  'errors' => array(...),
  'messages' => array(...)
));
```

**Authentication Checks:**
```smarty
{if $is_logged_in}
  {* Show logged-in user content *}
{else}
  {* Show guest content *}
{/if}
```

---

## JavaScript Integration

### JavaScript Files

**Core:**
- `js/bbsengine6.js` - Main engine
- `js/clock.js` - Real-time clock widget
- `js/jquery.smoothState.js` - jQuery plugin for AJAX

**Topbar Components:**
- `js/topbar.js` - Main topbar container
- `js/topbar-alert.js` - Alert notifications
- `js/topbar-loginlogout.js` - Auth UI
- `js/topbar-nav.js` - Navigation menu
- `js/topbar-greetings.js` - User greeting
- `js/topbar-credits.js` - Credit display
- `js/topbar-notify.js` - Notifications
- `js/topbar-join.js` - Register button

**Features:**
- `js/initsmoothstate.js` - Smooth page transitions
- `js/inittinymce.js` - Rich text editor
- `js/checkcurrentmemberid.js` - Verify user session
- `js/redirectpage.js` - Page redirection

### JavaScript Features

**Event Handlers:**
- Click handlers for navigation
- Form submission handling
- AJAX requests for async operations

**DOM Manipulation:**
- Insert elements for notifications
- Update topbar with current user info
- Toggle UI elements based on auth state

**AJAX Communication:**
```javascript
$.ajax({
  url: '/api/messages.php',
  method: 'GET',
  dataType: 'json',
  success: function(data) {
    // Update DOM with results
    renderMessages(data.messages);
  },
  error: function(xhr) {
    // Display error message
    showError('Failed to load messages');
  }
});
```

**Smooth Page Transitions:**
```javascript
// Using smoothState plugin
$(document).smoothState({
  onBefore: function() {
    // Show loading indicator
  },
  onAfter: function() {
    // Hide loading, update DOM
    // Re-initialize plugins
  }
});
```

### Client-Side Validation

**JavaScript Validation:**
```javascript
function validateLoginForm(form) {
  var loginid = form.loginid.value.trim();
  var password = form.password.value;
  
  if (!loginid) {
    showError('Login ID required');
    return false;
  }
  
  if (password.length < 6) {
    showError('Password too short');
    return false;
  }
  
  return true;
}

// Form submit handler
$('#loginForm').on('submit', function(e) {
  if (!validateLoginForm(this)) {
    e.preventDefault();
  }
});
```

---

## Request/Response Lifecycle

### Typical Request Flow

```
1. User clicks link/button in browser
   ├─ JavaScript intercepts if AJAX-enabled
   └─ Otherwise normal page navigation

2. HTTP Request sent to Apache
   POST /login.php
   Host: bbsengine.org
   Cookie: PHPSESSID=...
   Content-Type: application/x-www-form-urlencoded
   
   loginid=john.doe&password=secret

3. Apache routes to PHP script
   ├─ Loads /www/org/login.php
   └─ Requires engine.php

4. PHP Execution
   ├─ Bootstrap (database connection)
   ├─ Session initialization
   ├─ Request processing
   │  ├─ Parse POST data
   │  ├─ Validate (CSRF token, etc.)
   │  ├─ Call libmember\authenticate()
   │  │  └─ Database query
   │  ├─ Call session\login()
   │  │  └─ Set session variables
   │  └─ Prepare response data
   └─ Call engine\displaypage()

5. Template Rendering
   ├─ Load skin/tmpl/login.tpl
   ├─ Assign data to template
   ├─ Smarty compilation
   └─ HTML output

6. Response sent to browser
   HTTP/1.1 302 Found
   Set-Cookie: PHPSESSID=...; secure; httponly; samesite=Lax
   Location: /index.php
   Content-Type: text/html; charset=utf-8
   
   [HTML body]

7. Browser receives response
   ├─ Process cookies
   ├─ Parse HTML
   ├─ Load CSS from skin/
   ├─ Load JavaScript
   ├─ Render page
   └─ Execute JavaScript
```

---

## Web-to-Python Integration

### Architecture

The web layer is **secondary** in bbsengine6. The primary application is the Python-based terminal interface. The web layer can optionally call Python backend for certain operations.

```
Web Layer (PHP)
  ├─ Handle HTTP requests
  ├─ Manage sessions
  ├─ Render templates
  │
  └─ Optional: Call Python backend
     ├─ For complex operations
     ├─ For long-running tasks
     └─ For advanced features
```

### Integration Methods

#### Method 1: Direct Database Access

Both PHP and Python access the same PostgreSQL database, so web layer can directly query:

```php
// PHP directly queries database
$messages = database\fetchall(
  "SELECT * FROM engine.__blurb WHERE folderid = ?",
  array($folder_id)
);

// Same data available to Python via database.py
messages = database.query(args, 
  "SELECT * FROM engine.__blurb WHERE folderid = ?",
  (folder_id,))
```

**Pros:**
- No IPC overhead
- Immediate data access
- Simple to implement

**Cons:**
- Both layers must understand schema
- No business logic reuse

#### Method 2: Python subprocess calls

PHP can invoke Python scripts for complex operations:

```php
// PHP calls Python script
$output = shell_exec(
  "python3 -m bbsengine6.console member --getbyloginid=john.doe"
);
$member = json_decode($output, true);
```

**Pros:**
- Leverage Python business logic
- Consistent with terminal interface

**Cons:**
- Process startup overhead
- IPC complexity
- Harder to debug

#### Method 3: REST API (Future)

Possible future integration:

```php
// PHP makes HTTP request to Python API
$response = file_get_contents('http://localhost:5000/api/members/123');
$member = json_decode($response, true);
```

**Pros:**
- Clean separation of concerns
- Scalable
- Can be deployed separately

**Cons:**
- Network overhead
- Must maintain API
- More infrastructure

### Current Integration Status

**Today:** Web layer uses **direct database access** for all operations.

**Future:** Consider REST API if web layer expands significantly.

---

## Security Considerations

### HTTPS

- All login pages must be HTTPS
- Set Strict-Transport-Security header
- Redirect HTTP → HTTPS

### CSRF Protection

- Generate CSRF token per session
- Validate token on form submissions
- Regenerate after successful login

### SQL Injection

- All queries use prepared statements
- Parameter binding via PDO
- Input validation on all user data

### Password Security

- Hash with bcrypt (min 10 rounds)
- Never store plaintext
- Verify against hash with password_verify()

### Session Security

- Session cookies: secure, httponly, samesite=Lax
- Session timeout: 1 hour inactivity
- Regenerate session ID after login

### Output Escaping

- htmlspecialchars() on all user data in HTML
- JSON encoding for JSON responses
- Content-Type headers set correctly

---

*Web Layer Specification for bbsengine6*
