# ZOID6 State-Changing Endpoints CSRF Audit Report

**Date:** March 30, 2026

## Executive Summary
This audit identifies all PHP endpoints that handle state-changing operations (POST/PUT/DELETE) in the zoid6 application. The findings show a mixed security posture with some endpoints using the `handleform()` function (which includes CSRF protection) while others use direct `$_REQUEST`/`$_POST` access.

---

## PART 1: PHP Endpoints in `/home/opencode/data/work/zoid6/sites/engine/php/html/`

### 1. login.php
- **Description**: User authentication endpoint - validates username/password and creates session
- **HTTP Method(s)**: POST (form submission via handleform)
- **Uses handleform()**: YES
- **Data Modified**: 
  - Creates/updates session
  - Updates `engine.__member` table with lastlogin and lastloginfrom
- **CSRF Protection**: YES (handleform provides protection)
- **Priority**: HIGH (authentication endpoint)
- **Notes**: Form-based login uses handleform() wrapper at line 139

### 2. join.php
- **Description**: User registration endpoint - creates new member account
- **HTTP Method(s)**: POST (form submission via handleform)
- **Uses handleform()**: YES
- **Data Modified**:
  - Creates new record in `engine.__member` table
  - Sets password via setpassword()
  - Calls dbh->autoExecute() with MDB2_AUTOQUERY_INSERT at line 38
- **CSRF Protection**: YES (handleform provides protection)
- **Priority**: HIGH (creates new accounts)
- **Notes**: Wrapped with handleform() at line 96

### 3. member.php
- **Description**: Member profile management - view, edit, delete member accounts
- **HTTP Method(s)**: POST/GET (form submissions for edit, direct $_REQUEST["id"] for delete)
- **Uses handleform()**: PARTIALLY
  - edit() function uses handleform() at line 304
  - delete() function does NOT use handleform() - uses direct $_REQUEST["id"] at line 468
- **Data Modified**:
  - UPDATE operations: modifies engine.__member, flags via dbh->autoExecute() at line 412
  - DELETE operations: deletes from member table at line 469 using direct $_REQUEST
- **CSRF Protection**: 
  - EDIT: YES (via handleform)
  - DELETE: NO (direct $_REQUEST access without CSRF token)
- **Priority**: CRITICAL (delete lacks protection, edit requires verification)
- **Notes**: 
  - delete() function is vulnerable - processes deletion directly from $_REQUEST["id"] without form protection
  - edit() uses handleform with proper form processing at line 304

### 4. notify.php
- **Description**: Notification management - delete notifications, mark as read
- **HTTP Method(s)**: POST/GET
- **Uses handleform()**: NO
- **Data Modified**:
  - delete() function: deletes from __notify table at line 169 using direct $_REQUEST["notifyid"]
  - markread() function: updates __notify table at line 135
- **CSRF Protection**: NO (direct $_REQUEST access)
- **Priority**: CRITICAL
- **Notes**:
  - delete() at line 145-177 uses $_REQUEST["notifyid"] directly without CSRF protection
  - Has confirmation check but no CSRF token validation
  - markread() at line 130-142 updates records based on $notifyid parameter

### 5. logout.php
- **Description**: Session termination endpoint
- **HTTP Method(s)**: GET/POST
- **Uses handleform()**: NO
- **Data Modified**:
  - Clears session data
  - Calls clearcurrentmemberid() and removesessioncookie()
  - Session regeneration via session_regenerate_id(true)
- **CSRF Protection**: NO
- **Priority**: MEDIUM (stateless operation, but session-critical)
- **Notes**: Simple logout logic, uses sessions not direct data modification

### 6. flag.php
- **Description**: Flag/permission management system
- **HTTP Method(s)**: POST (form submission via handleform)
- **Uses handleform()**: YES (at line 63, though most functionality is commented out)
- **Data Modified**:
  - insert() function: creates new flag record via dbh->autoExecute() at line 100
- **CSRF Protection**: YES (handleform wrapper at line 63)
- **Priority**: MEDIUM (admin-only, most functionality disabled)
- **Notes**: Most add/edit/delete functionality is commented out; only insert is active

### 7. mantra.php
- **Description**: Content management - view, add, edit, delete mantra (text content)
- **HTTP Method(s)**: POST (form submission)
- **Uses handleform()**: PARTIALLY
  - insert() and update() functions are commented out (lines 233-370)
  - Current main() function only handles detail/summary operations
- **Data Modified**:
  - Originally designed to handle INSERT/UPDATE but functionality disabled
- **CSRF Protection**: YES (commented code uses handleform)
- **Priority**: LOW (core state-change functions disabled)
- **Notes**: State-changing operations are commented out; no active POST handling

---

## PART 2: PHP Endpoints in `/home/opencode/data/work/zoid6/sites/www/php/`

### 1. gfile.php
- **Description**: Document/file management - create, edit, delete documents
- **HTTP Method(s)**: POST/GET via form.process() or direct $_REQUEST access
- **Uses handleform()**: NO
- **Data Modified**:
  - add() -> insert(): CREATE in www.gfile at line 315
  - edit() -> update(): UPDATE in www.gfile at line 404
  - delete(): DELETE from www.gfile at line 460
- **CSRF Protection**: NO (uses direct $_REQUEST at lines 259, 335, 425, 453)
- **Priority**: CRITICAL (all CRUD operations lack CSRF protection)
- **Notes**:
  - Line 259: $_REQUEST["sigid"] in add()
  - Line 335: $_REQUEST["id"] in edit()
  - Line 425: $_REQUEST["id"] in delete()
  - Line 453: $_REQUEST["confirm"] in delete()
  - Uses form->process() callback but no CSRF tokens

### 2. login.php (www version)
- **Description**: User authentication (www site version)
- **HTTP Method(s)**: POST
- **Uses handleform()**: YES (at line 153 in www version)
- **Data Modified**:
  - Creates session
  - Updates member lastlogin/lastloginfrom via autoExecute()
- **CSRF Protection**: YES
- **Priority**: HIGH
- **Notes**: Similar to engine version but with handleform() at line 153

### 3. lib.php
- **Description**: Utility library - NOT an endpoint
- **HTTP Method(s)**: N/A (includes file with helper functions)
- **Uses handleform()**: N/A
- **Data Modified**: N/A
- **CSRF Protection**: N/A
- **Priority**: N/A

---

## PART 3: JavaScript AJAX Calls

### Engine JS Files

**ping.js** - `/home/opencode/data/work/zoid6/sites/engine/js/js/ping.js`
- **Type**: POST
- **URL**: //www.zoidtechnologies.com/ping
- **Endpoint Handler**: NOT FOUND (no ping.php exists; htaccess rule references it but handler missing)
- **Data Sent**: JSON { localtimestamp, localtimezoneoffset }
- **Purpose**: Client sends local timezone and time to server
- **CSRF Protection**: UNKNOWN (handler not found)
- **Priority**: MEDIUM

**authenticated.js** - `/home/opencode/data/work/zoid6/sites/engine/js/js/authenticated.js`
- **Type**: GET (JSONP)
- **URL**: //zoidtechnologies.com/engine/get-topbar-authenticated?callback=?
- **Endpoint Handler**: NOT FOUND
- **Data Sent**: None (query string based)
- **Purpose**: Fetch authenticated user topbar fragment
- **CSRF Protection**: N/A (GET request)
- **Priority**: LOW

**tooltip.js** - `/home/opencode/data/work/zoid6/sites/engine/js/js/tooltip.js`
- **Type**: GET (AJAX)
- **URL**: Dynamic tooltip URLs
- **Endpoint Handler**: Multiple (fetchtooltip function at line 9)
- **Data Sent**: None
- **Purpose**: Fetch tooltip content dynamically
- **CSRF Protection**: N/A (GET request)
- **Priority**: LOW

---

## PART 4: Routing Rules (htaccess)

### /ping Endpoint
- **htaccess rule**: `RewriteRule ^ping[/]?$ /ping.php [last]` (in htaccess-dev only)
- **Handler file**: /home/opencode/data/work/zoid6/sites/www/php/ping.php (NOT FOUND)
- **Issue**: Handler missing - endpoint routes to non-existent file
- **Implementation**: POST request from ping.js but handler not found

---

## SUMMARY TABLE

| File Path | Handler | HTTP Method | handleform()? | CSRF Protection | Priority |
|-----------|---------|-------------|---------------|-----------------|----------|
| engine/php/html/login.php | validate() | POST | YES | YES | HIGH |
| engine/php/html/join.php | insert() | POST | YES | YES | HIGH |
| engine/php/html/member.php | edit() | POST | YES | YES | HIGH |
| engine/php/html/member.php | delete() | GET/POST | NO | **NO** | **CRITICAL** |
| engine/php/html/member.php | update() | POST | YES | YES | HIGH |
| engine/php/html/notify.php | delete() | POST/GET | NO | **NO** | **CRITICAL** |
| engine/php/html/notify.php | markread() | POST | NO | **NO** | **CRITICAL** |
| engine/php/html/logout.php | main() | GET | NO | N/A | MEDIUM |
| engine/php/html/flag.php | insert() | POST | YES | YES | MEDIUM |
| engine/php/html/mantra.php | insert()/update() | POST | YES | YES (disabled) | LOW |
| www/php/gfile.php | insert() | POST | NO | **NO** | **CRITICAL** |
| www/php/gfile.php | update() | POST | NO | **NO** | **CRITICAL** |
| www/php/gfile.php | delete() | POST | NO | **NO** | **CRITICAL** |
| www/php/login.php | validate() | POST | YES | YES | HIGH |
| engine/js/js/ping.js | (missing) | POST | N/A | **UNKNOWN** | MEDIUM |

---

## CRITICAL FINDINGS

### 1. CSRF Vulnerable Endpoints (No Protection)
1. **member.php::delete()** - Deletes member accounts without CSRF token
2. **notify.php::delete()** - Deletes notifications without CSRF token  
3. **notify.php::markread()** - Marks notifications as read without CSRF token
4. **gfile.php::add/insert()** - Creates documents without CSRF token
5. **gfile.php::edit/update()** - Updates documents without CSRF token
6. **gfile.php::delete()** - Deletes documents without CSRF token

### 2. Missing Endpoint Handler
- **ping.php** is referenced in htaccess but file does not exist
- ping.js sends POST request to /ping but handler not found

### 3. Inconsistent Protection
- Some endpoints use `handleform()` (with CSRF protection)
- Others use direct `$_REQUEST` access (no CSRF protection)
- Mixed patterns create maintenance risk

---

## RECOMMENDATIONS

### Immediate Actions (Critical)
1. Add CSRF protection to `member.php::delete()` 
2. Add CSRF protection to `notify.php::delete()` and `markread()`
3. Add CSRF protection to `gfile.php` (add/update/delete)
4. Implement missing `/ping` endpoint handler

### Short-term Actions (High Priority)
1. Standardize on `handleform()` or equivalent CSRF wrapper for all POST endpoints
2. Add CSRF token validation to all state-changing operations
3. Remove direct `$_REQUEST` access for sensitive operations
4. Audit logout functionality for session-specific security

### Long-term Actions (Medium Priority)
1. Consider REST API middleware with built-in CSRF protection
2. Implement centralized security middleware
3. Add automated testing for CSRF vulnerability
4. Document security requirements for new endpoints

