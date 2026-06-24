# bbsengine6 Security Policy

## Overview

This document outlines the security measures implemented in bbsengine6 PHP codebase.

## Security Fixes Applied (2025-06-16)

### 1. SQL Injection Prevention

**Files Affected:**
- `php/database.php`

**Changes:**
- Added `quoteIdentifier()` function to properly quote SQL identifiers (table/column names)
- Modified `insert()` to quote table name, column names, and returning clause
- Modified `update()` to quote table name, column names, and where clause

**Before (vulnerable):**
```php
$sql = "insert into $tablename(" . join(", ", $validColumns) . ")";
$sql .= " where $primarykey=:$primarykey";
```

**After (secure):**
```php
$quotedTable = quoteIdentifier($tablename);
$quotedColumns = array_map('bbsengine6\database\quoteIdentifier', $validColumns);
$sql = "insert into $quotedTable(" . join(", ", $quotedColumns) . ")";
$sql .= " where " . quoteIdentifier($primarykey) . "=:$primarykey";
```

### 2. Path Validation (ReDoS Prevention)

**Files Affected:**
- `php/engine.php`

**Changes:**
- Added `validateLabelPath()` function with pattern `^[a-zA-Z0-9._-]+$`
- Added validation to `getsubsigs()` - returns empty array on invalid path
- Added validation to `getsig()` - returns null on invalid path

**Purpose:** Prevents Regular Expression Denial of Service (ReDoS) attacks via malicious regex in SQL `~` operator (ltree matching).

### 3. Path Traversal Prevention

**Files Affected:**
- `php/blurb.php`

**Changes:**
- Added `$blurbid <= 0` validation in `getcontent()`
- Added `realpath()` containment check to ensure file stays within content directory

**Before (vulnerable):**
```php
$filepath = $contentdir . "/" . $blurbid . ".txt";
return file_get_contents($filepath);
```

**After (secure):**
```php
if ($blurbid <= 0) {
    return null;
}
$filepath = $contentdir . "/" . $blurbid . ".txt";
$realpath = realpath($filepath);
$realdir = realpath($contentdir);
if ($realpath === false || $realdir === false || strpos($realpath, $realdir) !== 0) {
    return null;
}
```

### 4. Transaction Safety

**Files Affected:**
- `php/database.php`

**Changes:**
- Added `inTransaction()` check before rollback to prevent errors

**Before (error-prone):**
```php
} catch (\Throwable $e) {
    $pdo->rollBack();
```

**After (robust):**
```php
} catch (\Throwable $e) {
    if (isset($pdo) && $pdo->inTransaction()) {
        $pdo->rollBack();
    }
```

### 5. CSRF Enhancement

**Files Affected:**
- `php/util.php`

**Changes:**
- Added optional `$requireOnGet` parameter to `csrfCheckRequest()`
- Default behavior maintained for backward compatibility

**Usage:**
```php
// Default: GET requests without token return true (backward compatible)
csrfCheckRequest();

// Strict: GET requests require token
csrfCheckRequest(requireOnGet: true);
```

## zoid6 Security Fixes

### SQL Injection in buildbreadcrumblist()

**Files Affected:**
- `zoid6/php/zoid6.php`
- `zoid6/php/libvulcan.php`
- `zoid6/sites/www/php/lib.php`

**Changes:**
- Added table name validation using `validateTableName()` from bbsengine6

## Reporting Security Issues

Please report security vulnerabilities to the maintainers via the project issue tracker.
