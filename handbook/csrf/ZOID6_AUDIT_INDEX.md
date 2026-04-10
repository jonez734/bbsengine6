# ZOID6 CSRF Audit - Documentation Index

## Overview
Comprehensive security audit of all state-changing endpoints in the zoid6 application, identifying CSRF vulnerabilities and protection status.

**Audit Date:** March 30, 2026  
**Auditor:** AI Code Analysis  
**Scope:** PHP POST/PUT/DELETE handlers and AJAX endpoints

---

## Quick Facts

- **Total Endpoints Analyzed:** 15 state-changing operations
- **Critical Vulnerabilities Found:** 6
- **High Priority Issues:** 4
- **Protected Endpoints:** 5
- **Missing Handlers:** 1 (/ping endpoint)

## Critical Issues Summary

| # | Endpoint | File | Issue | Risk |
|---|----------|------|-------|------|
| 1 | gfile.insert() | www/php/gfile.php | No CSRF token | Creates data |
| 2 | gfile.update() | www/php/gfile.php | No CSRF token | Modifies data |
| 3 | gfile.delete() | www/php/gfile.php | No CSRF token | Deletes data |
| 4 | member.delete() | engine/php/html/member.php | No CSRF token | Deletes accounts |
| 5 | notify.delete() | engine/php/html/notify.php | No CSRF token | Deletes notifications |
| 6 | notify.markread() | engine/php/html/notify.php | No CSRF token | Modifies notifications |

---

## Documentation Files

### 1. **ZOID6_CSRF_AUDIT_REPORT.md** (Main Report)
   - **Size:** 11 KB
   - **Format:** Markdown
   - **Contents:**
     - Executive Summary
     - Detailed analysis of each endpoint
     - HTTP methods and data modifications
     - handleform() usage documentation
     - Current protection status
     - AJAX calls analysis
     - Routing rules
     - Summary table with all endpoints
     - Critical findings and recommendations

   **Use This For:** Detailed technical review, implementation planning

### 2. **ZOID6_AUDIT_SUMMARY.txt** (Executive Summary)
   - **Size:** 10 KB
   - **Format:** Plain text (easy to read)
   - **Contents:**
     - Key findings at a glance
     - Vulnerability severity breakdown
     - Individual vulnerability descriptions with fixes
     - Protected endpoints list
     - Recommendations by priority
     - Implementation patterns
     - Testing recommendations
     - Conclusion and action items

   **Use This For:** Executive briefing, quick reference, priority planning

### 3. **ZOID6_ENDPOINTS_CSV.csv** (Data Export)
   - **Size:** 2 KB
   - **Format:** Comma-separated values
   - **Contents:**
     - File paths
     - Handler names
     - HTTP methods
     - handleform() usage
     - CSRF protection status
     - Data modified
     - Line numbers
     - Priority levels

   **Use This For:** Importing to spreadsheet, automated analysis, issue tracking

### 4. **ZOID6_AUDIT_INDEX.md** (This File)
   - **Size:** This document
   - **Format:** Markdown
   - **Contents:** Navigation and quick reference

   **Use This For:** Understanding audit structure and finding information

---

## How to Use These Documents

### For Security Managers
1. Read **ZOID6_AUDIT_SUMMARY.txt** first
2. Review the "Critical Vulnerabilities" section
3. Review "Recommendations by Priority"
4. Use findings to create remediation plan

### For Developers
1. Start with **ZOID6_ENDPOINTS_CSV.csv** for quick endpoint list
2. Read **ZOID6_CSRF_AUDIT_REPORT.md** for detailed technical info
3. Focus on endpoints marked "CRITICAL" or "HIGH"
4. Cross-reference line numbers for code navigation

### For Project Managers
1. Read **ZOID6_AUDIT_SUMMARY.txt** sections:
   - Key Findings
   - Critical Vulnerabilities
   - Recommendations by Priority
2. Use this to create project timeline
3. Reference **ZOID6_ENDPOINTS_CSV.csv** for scope

### For CI/CD Integration
1. Import **ZOID6_ENDPOINTS_CSV.csv** into issue tracking
2. Create tickets for each "CRITICAL" endpoint
3. Add security tests based on test recommendations
4. Track progress against implementation plan

---

## Protected Endpoints (No Action Needed)

These 5 endpoints use `handleform()` and have proper CSRF protection:

1. **engine/php/html/login.php** - User authentication
2. **engine/php/html/join.php** - User registration
3. **engine/php/html/member.php::edit()** - Member profile editing
4. **engine/php/html/flag.php::insert()** - Flag creation (admin)
5. **www/php/login.php** - Website authentication

---

## Critical Vulnerabilities Quick Reference

### Gfile.php (Document Management)
- **Location:** /home/opencode/data/work/zoid6/sites/www/php/gfile.php
- **Issues:**
  - Line 259: No CSRF check on add()
  - Line 335: No CSRF check on edit()
  - Line 425: No CSRF check on delete()
  - Line 453: No CSRF check on confirmation
- **Impact:** Complete document management compromise
- **Fix Priority:** CRITICAL (Week 1-2)

### Member.php (Account Management)
- **Location:** /home/opencode/data/work/zoid6/sites/engine/php/html/member.php
- **Issues:**
  - Line 468: delete() uses $_REQUEST["id"] without CSRF token
- **Impact:** Unauthorized member account deletion
- **Fix Priority:** CRITICAL (Week 1-2)

### Notify.php (Notifications)
- **Location:** /home/opencode/data/work/zoid6/sites/engine/php/html/notify.php
- **Issues:**
  - Line 147: delete() uses $_REQUEST["notifyid"] without CSRF token
  - Line 135: markread() updates without CSRF validation
- **Impact:** Notification system compromise
- **Fix Priority:** CRITICAL (Week 1-2)

### Missing Handler
- **Endpoint:** /ping
- **Expected Location:** /home/opencode/data/work/zoid6/sites/www/php/ping.php
- **Status:** NOT FOUND
- **Called By:** engine/js/js/ping.js (line 21)
- **Fix Priority:** MEDIUM (implement handler with CSRF protection)

---

## Implementation Patterns

### Recommended Pattern (Protected)
```php
$res = \bbsengine6\handleform($form, [$this, "handler"], "context");
if ($res === True) {
    logentry("success");
    return true;
}
```
**Status:** CSRF protected ✓

### Pattern to Avoid (Vulnerable)
```php
$id = isset($_REQUEST["id"]) ? intval($_REQUEST["id"]) : null;
$dbh->autoExecute("table", null, MDB2_AUTOQUERY_DELETE, "id=".$dbh->quote($id));
```
**Status:** NOT protected ✗

---

## Testing Checklist

Before deploying any fixes, verify:

- [ ] CSRF token validation works for all POST endpoints
- [ ] Tokens are properly regenerated after login
- [ ] Cross-origin requests are blocked
- [ ] Token expiration is enforced
- [ ] Authorization checks are performed
- [ ] SQL injection prevention is verified
- [ ] XSS prevention is tested
- [ ] Session fixation is prevented
- [ ] Logout properly clears all session data
- [ ] Automated tests pass

---

## File Locations

All audit documents are in: `/home/opencode/data/work/`

- ZOID6_CSRF_AUDIT_REPORT.md
- ZOID6_AUDIT_SUMMARY.txt
- ZOID6_ENDPOINTS_CSV.csv
- ZOID6_AUDIT_INDEX.md (this file)

Source code analyzed:
- `/home/opencode/data/work/zoid6/sites/engine/php/html/` (7 files)
- `/home/opencode/data/work/zoid6/sites/www/php/` (9 files)
- `/home/opencode/data/work/zoid6/sites/engine/js/js/` (JavaScript)

---

## Next Steps

1. **Week 1:** Review all documentation
2. **Week 2:** Create tickets for all CRITICAL issues
3. **Week 3-4:** Implement CSRF protection for gfile.php, member.php, notify.php
4. **Week 5:** Create /ping handler
5. **Month 2:** Standardize on handleform() pattern application-wide
6. **Month 3+:** Long-term improvements (REST API, middleware, etc.)

---

## Questions or Issues?

Refer to the detailed sections in **ZOID6_CSRF_AUDIT_REPORT.md** for:
- Technical details on specific endpoints
- Code line references
- Database table names
- Data flow analysis
- Detailed recommendations

Or check **ZOID6_AUDIT_SUMMARY.txt** for:
- Executive summaries
- Risk assessments
- Implementation patterns
- Testing procedures

---

*Audit completed: March 30, 2026*  
*Classification: Security Audit - Complete*
