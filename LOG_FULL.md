<!--
GENERATED FILE — DO NOT EDIT BY HAND.

Produced by the `log` Makefile target (`make log`). Equivalent
to LOG.md (same `git log --pretty=...` output, full commit
bodies) except this file's leading commit is from a different
branch tip at regeneration time. The companion file
LOG_SUMMARY.md is the same history grouped by date, subject-only.
-->
* f416127 2026-03-30 Group LOG_SUMMARY by date with date headers (HEAD -> main) [J (eff)]
| Group LOG_SUMMARY by date with date headers
| 
* 523cda2 2026-03-30 Add Makefile log target to generate LOG_FULL.md and LOG_SUMMARY.md (github/main) [J (eff)]
| Add Makefile log target to generate LOG_FULL.md and LOG_SUMMARY.md
| 
* 474cbc3 2026-03-30 security: remove hardcoded reCAPTCHA keys, use environment variables instead [J (eff)]
| security: remove hardcoded reCAPTCHA keys, use environment variables instead
| 
* e05b90a 2026-03-30 Update bbsengine6: Enable getdate-next dependency and fix Makefile to use PYTHON variable [J (eff)]
| Update bbsengine6: Enable getdate-next dependency and fix Makefile to use PYTHON variable
| 
* 5abfd05 2026-03-29 Fix remaining .spec references to .md in console.md related documentation section [J (eff)]
| Fix remaining .spec references to .md in console.md related documentation section
| 
* 2840f02 2026-03-29 Update references from .spec to .md file extensions in handbook documentation [J (eff)]
| Update references from .spec to .md file extensions in handbook documentation
| 
* 872b641 2026-03-29 Rename handbook spec files from .spec to .md extension [J (eff)]
| Rename handbook spec files from .spec to .md extension
| 
* c6a4432 2026-03-29 bbsengine6: added .gitattributes (*.spec as markdown) [Jeff MacDonald]
| bbsengine6: added .gitattributes (*.spec as markdown)
| 
* ddf14b5 2026-03-29 Add comprehensive console module specification suite [J (eff)]
| Add comprehensive console module specification suite
| 
| - Create console.spec master index with TOC and quick links
| - Add 13 modular section files in console/ subdirectory:
|   * overview.spec: File inventory and standard interface
|   * architecture.spec: Design patterns, execution flow, and layering
|   * core-library.spec: lib.py module discovery framework
|   * main-console.spec: Database initialization stages and interactive menu
|   * member-management.spec: Member CRUD and editing interface
|   * member-approval.spec: New member approval workflow
|   * session-management.spec: Active session display and monitoring
|   * database-checks.spec: Database verification (11 modules grouped by category)
|   * notify.spec: Notification system (stub with design documentation)
|   * email.spec: Email configuration (incomplete with design intent)
|   * data-flows.spec: Complete workflows with call sequences
|   * dependencies.spec: Import maps and module relationships
|   * comprehensive.spec: Consolidated 975-line detailed reference
| 
| - Update bbsengine6/handbook/specs/index.spec to link console spec
| - ~5,200 lines of documentation covering all 21 console modules
| - High-level signatures, design patterns, transaction boundaries
| - Error handling and recovery procedures documented
| - Multiple entry points: quick index, modular sections, comprehensive reference
| 
* d893afe 2026-03-29 Refactor console check modules for clean, robust code [J (eff)]
| Refactor console check modules for clean, robust code
| 
| Improvements to all check*.py modules:
| 
| **Major Cleanups:**
| - checkdatabase.py: Remove 52 lines of dead/unreachable code after return statements
| - checkschema.py: Remove redundant schema grant logic (already in schema.sql)
| - checkloginid.py: Complete rewrite - replace test/example code with proper module
|   implementing machine account validation via DBus/AccountsService
| - checkextensions.py: Clean up commented-out debug/sample code
| - Remove debug echo statements from checkfunctions.py, checkflag.py, checkroles.py
| 
| **Code Quality & Standardization:**
| - Add missing module docstring to checkclasses.py
| - Add module docstring to checknotify.py
| - Standardize connection handling: convert kwargs.pop() to kwargs.get() pattern
| - Replace print() with io.echo() for consistent output handling
| - Fix malformed f-string in checkdatabase.py (missing 'f' prefix)
| - Remove commented debug/test code blocks throughout
| - Clean up inline comments and unnecessary debug output
| 
| **Validation:**
| - All files pass ruff linting checks
| - Code properly formatted with ruff formatter
| - No functional behavior changes - purely code quality improvements
| 
* c6b0963 2026-03-29 Update database.spec - document that args parameter is optional in connect() [J (eff)]
| Update database.spec - document that args parameter is optional in connect()
| 
* 2d88cb3 2026-03-29 Fix notify.count() error 110 regression - make args optional in database.connect() [J (eff)]
| Fix notify.count() error 110 regression - make args optional in database.connect()
| 
| The previous commit (8988863) introduced error 110 spam during idle in the member
| console menu by requiring 'args' parameter when calling database.connect(). The
| args parameter is only needed for debug logging, not for core functionality.
| 
| Changes:
| - Make args parameter optional in database.connect() by wrapping debug logging
|   in 'if args and args.debug is True:' checks
| - Remove the args=None check in notify.count() that was failing with error 110
| - Update docstring to document that args is optional
| 
| This restores the original design where args is only for logging flags like
| --debug and --verbose. The function now handles None gracefully without requiring
| callers to check or pass args when unavailable.
| 
* 8988863 2026-03-29 Fix connection pool exhaustion in notify.count by using database.connect context manager [J (eff)]
| Fix connection pool exhaustion in notify.count by using database.connect context manager
| 
| Previously, notify.count() manually called pool.getconn() followed by
| conn.close(), which destroys the connection instead of returning it to
| the pool. Over time this exhausted all available connections, causing
| PoolTimeout errors after brief idle periods.
| 
| Now uses the database.connect() context manager which properly returns
| connections via pool.putconn() in its __exit__ method, matching the
| pattern used elsewhere in the codebase (e.g., member.py).
| 
* 1fafd23 2026-03-29 Fix 'connection is closed' error in member edit by moving commit inside with block [J (eff)]
| Fix 'connection is closed' error in member edit by moving commit inside with block
| 
* 6fe2ea2 2026-03-29 Fix enum type detection to prevent duplicate creation errors [J (eff)]
| Fix enum type detection to prevent duplicate creation errors
| 
| Add typeexists() function that uses to_regtype() to properly detect
| PostgreSQL enum types. Update checknotify.py to check enum types
| separately from classes, fixing 'type already exists' error for
| notify_urgency_enum.
| 
* bbf5f4e 2026-03-29 fix: propagate pool/args to inputchoice in member console menu [J (eff)]
| fix: propagate pool/args to inputchoice in member console menu
| 
* 83232d8 2026-03-29 fix: propagate pool/conn/args to notify.count() and log pool warning once [J (eff)]
| fix: propagate pool/conn/args to notify.count() and log pool warning once
| 
* f133db0 2026-03-28 fix: add UNIQUE INDEX to map_member_flag table for UPSERT support [J (eff)]
| fix: add UNIQUE INDEX to map_member_flag table for UPSERT support
| 
| The ON CONFLICT clause in PostgreSQL requires a unique constraint or index on
| the conflict columns. The map_member_flag table previously had no constraint,
| causing 'InvalidColumnReference' errors when using database.upsert().
| 
| ## Solution
| 
| Added a UNIQUE INDEX instead of a PRIMARY KEY to align with the established
| codebase pattern for join tables (see map_group_member, map_sigop_sigpath).
| This preserves the design philosophy of not having explicit PKs on join tables
| while enabling atomic INSERT...ON CONFLICT operations.
| 
| ## Changes
| 
| 1. **Updated table schema** (py/src/bbsengine6/sql/map_member_flag.sql):
|    - Added UNIQUE INDEX idx_map_member_flag on (moniker, name)
|    - Enables ON CONFLICT for UPSERT operations
|    - Semantically correct: each member has one value per flag
| 
| 2. **Created migration script** (handbook/migrations/001_add_unique_index_to_map_member_flag.sql):
|    - Safe, idempotent migration for existing databases
|    - Removes duplicates (if any) before adding index
|    - Includes comprehensive error handling and logging
| 
| ## Impact
| 
| - New databases will have UNIQUE INDEX from table creation
| - Existing databases need to run migration 001
| - setflag() and database.upsert() calls now work correctly
| - Atomic insert-or-update operations fully supported
| 
| ## Testing
| 
| All 17 transaction tests passing:
| - Moniker change detection and cascade flow
| - Flag updates with correct ordering
| - Foreign key constraint prevention
| - Transaction atomicity and consistency
| 
* b6b4766 2026-03-28 fix: refactor member updates to use atomic UPSERT and explicit cascade ordering [J (eff)]
| fix: refactor member updates to use atomic UPSERT and explicit cascade ordering
| 
| Fix foreign key constraint violations and transaction abort errors that occurred
| when updating member records with flag changes, particularly during moniker changes.
| 
| ## Problem
| 
| When updating a member's moniker while also changing flags, the code would:
| 1. Try to set flags to a NEW moniker that doesn't exist yet → FK constraint violation
| 2. Use DELETE+INSERT pattern for setflag() that could poison transaction on failure
| 
| ## Solution
| 
| 1. **Atomic UPSERT pattern:** Introduced database.upsert() - a generic, reusable function
|    that works for any table and performs INSERT...ON CONFLICT...DO UPDATE atomically.
|    This replaces the fragile DELETE+INSERT pattern in setflag().
| 
| 2. **Explicit cascade ordering:** When a moniker changes and flags exist:
|    - Update flags FIRST using the OLD moniker (guaranteed to exist)
|    - Then update member record to new moniker
|    - PostgreSQL CASCADE automatically migrates flag FK references
| 
| 3. **Transaction management:** All operations in a single atomic transaction owned by
|    the caller, preventing FK violations and transaction abort states.
| 
| ## Changes
| 
| - database.py: Added generic upsert() function (lines 393-495)
|   * Works with any table, conflict columns, update columns
|   * Handles mogrify, commit, conn/pool parameters
|   * Fully documented with examples
| 
| - member.py: Refactored insert/update/setflag operations
|   * setflag() now returns bool instead of None
|   * setflag() uses database.upsert() for atomic insert-or-update
|   * update() reorders operations: flags-first (if moniker changing) → member → cascade
|   * _update_member_flags() handles bool return values gracefully
|   * All member operations work within single transaction
| 
| - tests/test_member_transactions.py: Added 17 comprehensive tests
|   * 5 tests for moniker change scenarios
|   * Tests verify correct ordering, cascade flow, multiple flags
|   * All 17 tests passing
| 
| ## Testing
| 
| All 17 transaction tests pass, verifying:
| - Moniker change detection and cascade flow
| - Flag updates with old moniker before FK change
| - Foreign key constraint prevention
| - Transaction atomicity and consistency
| - No FK violations during member updates
| 
| Fixes #196
| 
* e9a216a 2026-03-28 docs: update specs for primary key change handling and transaction management [J (eff)]
| docs: update specs for primary key change handling and transaction management
| 
| Update three specification files to document the new explicit cascade ordering
| pattern for primary key changes, transaction management improvements, and the
| new _update_member_flags() helper function.
| 
| ## Changes
| 
| ### handbook/specs/member.spec
| - Document new _update_member_flags() helper function
| - Update update() function documentation with moniker change handling details
| - Update insert() function documentation with transaction management
| - Clarify setflag() transaction behavior (conn vs pool)
| - Add new 'Transaction Management' section explaining:
|   * Overview of atomic transactions for insert/update
|   * Moniker change special case (explicit map_member_flag cascade)
|   * Example transaction flows
|   * Atomic commit guarantee
| 
| ### handbook/specs/database.spec
| - Expand update() documentation with parameter explanations
| - Document updatepk parameter and its purpose
| - Add note about required explicit handling of dependent tables
| - Expand insert() documentation with parameter explanations
| - Document commit parameter behavior
| - Add note about commit=False for multi-step transactions
| 
| ### handbook/specs/decisions.spec
| - Add Decision 9: Explicit Cascade Ordering for Primary Key Changes
| - Explain the catch-22 problem with PostgreSQL CASCADE constraints
| - Document why other alternatives (constraint deferral, surrogate keys) were rejected
| - Show implementation pattern with code example
| - Update table of contents to include Decision 9
| - Update summary table to include PK changes decision
| 
| This documentation serves as future reference for why the explicit cascade
| ordering pattern is necessary and how it prevents FK constraint violations
| during primary key changes.
| 
* 3965378 2026-03-28 fix: handle moniker changes as special case with explicit transaction management [J (eff)]
| fix: handle moniker changes as special case with explicit transaction management
| 
| This commit implements Option C from the analysis of FK constraint violations
| when changing member monikers. The issue occurred because setflag() was called
| with a new moniker before the __member record was updated.
| 
| ## Changes
| 
| ### 1. New Helper Function: _update_member_flags()
| - Reusable function for managing member flags in map_member_flag table
| - Takes flags_dict and applies them to a given moniker
| - Returns True/False for success/failure
| - Logs and fails on errors (exceptions propagate)
| - Can be called from both insert() and update() flows
| 
| ### 2. Modified member.update()
| - Detects if moniker is changing (old vs new moniker values)
| - If moniker IS changing:
|   * Explicitly UPDATE map_member_flag records to new moniker FIRST
|   * Then update __member with updatepk=True (allows PK change)
|   * PostgreSQL CASCADE constraints handle other related tables automatically
| - Calls _update_member_flags() for any flag value changes
| - Uses commit=False in database.update() to keep transaction open
| - Explicit conn.commit() at end to commit entire transaction atomically
| 
| ### 3. Modified member.insert()
| - Changed to keep transaction open (commit=False in database.insert)
| - Extracts flags_dict before insert
| - After inserting member, calls _update_member_flags() to insert flags
| - Explicit conn.commit() at end to commit entire transaction atomically
| - Proper error handling with rollback capability for callers
| 
| ### 4. Transaction Management in memberapproval.py
| - Added explicit transaction management (database.connect context managers)
| - Each setflag/update operation now wrapped in try/except with rollback
| - Fixes previous issue where operations could partially complete
| - Also fixes typo: currrentmoniker -> currentmoniker
| - Also fixes bug: memberid parameter -> m["moniker"]
| 
| ## Transaction Safety
| 
| All database operations now follow this pattern:
| 1. Pass conn with commit=False to preserve transaction
| 2. All related operations (member + flags) complete in single transaction
| 3. Explicit conn.commit() only after all operations succeed
| 4. Exception propagation allows caller to rollback on error
| 
| All FK constraints on __member.moniker are set to ON UPDATE CASCADE,
| so other tables are automatically updated when moniker changes.
| 
| ## Testing
| 
| Changes maintain backward compatibility:
| - insert() can still be called without explicit conn (auto-commits)
| - update() requires conn (as before)
| - All existing call sites continue to work
| - New transaction isolation prevents partial updates
| 
* 8cd6ad2 2026-03-28 fix: disable notification checking in inputstring() tight input loop [J (eff)]
| fix: disable notification checking in inputstring() tight input loop
| 
| The notification check in getch_str() calls notify.count(moniker) which
| performs a database query on every keypress. In inputstring()'s aggressive
| 15ms polling loop, this causes 66+ database queries per second, creating
| timing issues that manifest as cursor display glitches and delayed key
| processing.
| 
| Changes:
| - Add check_notifications parameter to getch_str() (default: True for backward compat)
| - inputstring() disables notification checking by passing check_notifications=False
| - Add INPUTSTRING_GETCH_TIMEOUT named constant to replace magic number 0.015
| - Fix fire_events parameter passing in _proc_char() calls
| 
| This allows inputinteger() and any other functions using inputstring()
| to benefit automatically. Functions waiting for single character input
| (inputchoice, inputboolean) are unaffected since they use the default
| 1.0s timeout and don't have tight polling loops.
| 
| Fixes: Cursor positioning glitch ('m' covered by cursor in 'jam'),
| control key input not being recognized (Ctrl+E printing 'E' instead of
| executing end-of-line command).
| 
* 4f28ea6 2026-03-28 Fix: Remove double JSON conversion in member.buildrec() [J (eff)]
| Fix: Remove double JSON conversion in member.buildrec()
| 
| Fixes TypeError: Object of type Jsonb is not JSON serializable
| 
| The buildrec() function was calling json.dumps(database.convert_for_jsonb(v))
| which created a non-serializable Jsonb object. This was a misuse of tools:
| json.dumps() is for Python→JSON conversion, not for database type wrapping.
| 
| SOLUTION (Option C - Recommended):
| Let database.py handle all JSON/JSONB conversions through proper separation
| of concerns:
|   - buildrec(): Transform data structure (keep dicts as dicts)
|   - database.update(): Handle type conversion (wrap dicts in Jsonb)
|   - psycopg3: Serialize to database
| 
| CHANGES:
| - member.py:76: Removed json.dumps() and convert_for_jsonb() calls
|   Now simply: m[k] = v (keep dict as-is)
| 
| - member.py: Enhanced buildrec() docstring explaining its purpose and
|   limitations. Added comments clarifying why json.dumps() is removed.
| 
| - database.py:21: Enhanced convert_for_jsonb() documentation with examples
|   of correct and incorrect usage patterns. Documented that this function
|   should handle all JSON/JSONB conversions for database operations.
| 
| TESTING:
| - Added 18 unit tests for buildrec() function behavior
| - Added 11 integration tests for complete member update workflow
| - All 29 new tests PASS ✓
| - All 145 existing relevant tests still PASS ✓
| - Zero regressions
| 
| DOCUMENTATION:
| - Created JSON_HANDLING_GUIDE.md with best practices for JSON handling
| - Clear layer responsibilities (application vs database vs psycopg3)
| - Common patterns and debugging checklist
| 
| KEY PRINCIPLE:
| 'Database conversions are handled by database.py.
|  Never call json.dumps() before passing data to database functions.'
| 
* b7aaf80 2026-03-28 Rename timedelta_() to timedeltastr() for better readability [J (eff)]
| Rename timedelta_() to timedeltastr() for better readability
| 
| - Renamed utility function from timedelta_() to timedeltastr() in util.py
| - Updated function calls in console/session.py (lines 62, 65)
| - Added comprehensive docstring with parameter descriptions and usage example
| - Fixes AttributeError: module 'bbsengine6.util' has no attribute 'timedelta'
| 
* 8b8b31b 2026-03-28 Implement empyre connection pooling pattern in notify.count() [J (eff)]
| Implement empyre connection pooling pattern in notify.count()
| 
| - Add **kwargs parameter to accept optional 'pool' and 'conn' arguments
| - Implement three-tier connection priority: explicit conn > pool > fail
| - Use nested _work() function following notify.py convention
| - Log moniker context in error messages for better debugging
| - Use pool.getconn() and db_conn.close() pattern from empyre
| - Ensure connection is returned to pool via finally block
| - Return 0 strictly when no pool available (Option B: BC preserved)
| - All existing tests pass (37 unit tests + 5 integration tests)
| - Enables new calling pattern: count(moniker, pool=pool)
| - Maintains backward compatibility with existing code
| 
* 5dc57c4 2026-03-28 Fix dict/tuple row access in notify.py for psycopg3 cursor compatibility [J (eff)]
| Fix dict/tuple row access in notify.py for psycopg3 cursor compatibility
| 
| - Fixed type_row[0] to use dict access type_row["default_urgency"]
| - Fixed cur.fetchone()[0] to use dict access cur.fetchone()["id"]
| - Added database.convert_for_jsonb() calls for template_vars and data parameters
|   to properly convert dicts to JSONB for PostgreSQL insertion
| - These changes enable notify.send() to work with dict_row cursors (default)
| - Proves notify.count() works end-to-end without errors (all 5 tests pass)
| 
* 3603350 2026-03-28 docs: update NOTIFY_TESTING.md with automatic setup instructions [J (eff)]
| docs: update NOTIFY_TESTING.md with automatic setup instructions
| 
| - Add section on Automatic Database Setup
|   * Explain conftest.py fixtures (db_connection, schema_init, create_test_users, test_transaction)
|   * Document environment variable BBSENGINE6_DBNAME
|   * Show first run vs. subsequent run commands
| 
| - Add TestNotificationCount to test classes section
| 
| - Add 'How conftest.py Works' section explaining:
|   * Session-scoped fixtures (run once per session)
|   * Function-scoped fixtures (run before/after each test)
|   * Helper functions for SQL loading
| 
| - Enhance troubleshooting section with new scenarios:
|   * Database connection errors (how to verify)
|   * 'relation does not exist' errors (need BBSENGINE6_DBNAME env var)
|   * 'already exists' warnings (normal on re-runs)
|   * Transaction isolation issues
| 
* 5b7b864 2026-03-28 feat: add pytest conftest for automatic notify schema initialization and fix database connection [J (eff)]
| feat: add pytest conftest for automatic notify schema initialization and fix database connection
| 
| - Create py/tests/conftest.py with session-scoped fixtures for database setup
|   * db_connection: persistent connection to zoid6test database
|   * schema_init: smart initialization (only 7 notify-specific SQL files)
|   * create_test_users: creates test users alice, bob
|   * test_transaction: function-scoped auto-use fixture for transaction isolation
| 
| - Smart approach: only initializes missing notify tables, skips existing schema
| 
| - Fix notify.py to use dynamic database name
|   * Add _DEFAULT_DBNAME environment variable (BBSENGINE6_DBNAME)
|   * Default to 'bbsengine6' for production, allows 'zoid6test' for testing
|   * Replace all 16 hardcoded 'dbname=postgres' with dynamic f-string
| 
| - Add test for notify.count() function
|   * TestNotificationCount class with 4 test methods
|   * Validates count() returns integer for test users
| 
| - Properly quotes schema-qualified table names using sql.Identifier()
|   * Ensures 'engine.__notify' and other double-underscore tables are found
|   * Fixes 'relation does not exist' errors in previous phase
| 
* ec3baa3 2026-03-28 fix: use sql.Identifier() for properly quoting schema-qualified table names in notify.py and session.py [J (eff)]
| fix: use sql.Identifier() for properly quoting schema-qualified table names in notify.py and session.py
| 
| - Add _table_identifier() helper function to both files to properly handle schema-qualified identifiers like 'engine.__notify'
| - Refactor all raw SQL strings to use sql.SQL() for SQL keywords and sql.Identifier() for column/table names
| - Fixes identifier quoting issues where double-underscore table names were not being quoted, causing 'engine.__notify does not exist' errors
| - Updated getmembersession() to use proper identifier quoting
| - Updated set() function UPDATE statements to properly quote identifiers and table name
| - Updated garbagecollect() to use proper identifier quoting
| - All changes follow the pattern established in database.py's _table_identifier() pattern
| 
* c5b9770 2026-03-28 Fix testsession.py test mocks to use timezone-aware datetimes [J (eff)]
| Fix testsession.py test mocks to use timezone-aware datetimes
| 
| - Update all test session mocks to include expiry field with timezone-aware datetime
| - Update test fixtures for get() and getmembersession() to include expiry
| - Fix mock cursor.fetchone() to return proper session dicts with expiry
| - Update test assertions to account for multiple execute() calls in set/write tests
| - Remove incorrect commit assertion from garbagecollect test
| 
| Tests now pass with timezone-aware datetime requirement.
| 
* 0a5de77 2026-03-28 Fix timezone-aware datetime in test fixtures [J (eff)]
| Fix timezone-aware datetime in test fixtures
| 
| - Update testsession.py test fixtures to use timezone-aware datetime.now(timezone.utc)
| - Update test_notify.py test fixtures to use timezone-aware datetime.now(timezone.utc)
| - Update test_notify_integration.py test data to use timezone-aware datetime.now(timezone.utc)
| - Update example_notify.py example code to use timezone-aware datetime.now(timezone.utc)
| - Import timezone from datetime module in all files
| 
| Ensures all test fixtures and example code use consistent timezone-aware datetimes.
| 
* 2bf987a 2026-03-28 Fix timezone-aware datetime in notify.py [J (eff)]
| Fix timezone-aware datetime in notify.py
| 
| - Update Notification dataclass created_at default factory to use timezone-aware datetime.now(timezone.utc)
| - Update send() function to create timezone-aware notifications
| - Update _add_to_user_queue() function to create timezone-aware notifications
| - Import timezone from datetime module
| 
| Ensures all notification timestamps are consistently timezone-aware for proper database storage.
| 
* 5883820 2026-03-28 Fix timezone-aware datetime comparisons in session.py [J (eff)]
| Fix timezone-aware datetime comparisons in session.py
| 
| - Update is_valid() to use timezone-aware datetime.now(timezone.utc) for comparison with database timestamps
| - Update updatelastactivity() to create timezone-aware expiry datetime
| - Update buildsession() to create timezone-aware expiry datetime
| - Import timezone from datetime module
| 
| This fixes TypeError when comparing offset-naive and offset-aware datetimes with database timestamptz values.
| 
* cfffb8c 2026-03-28 refactor: rename currentsessionid functions with type annotations [J (eff)]
| refactor: rename currentsessionid functions with type annotations
| 
| - Rename _get_currentsessionid() to getcurrentsessionid()
| - Rename _set_currentsessionid() to setcurrentsessionid()
| - Update all internal references throughout session.py
| - Fix AttributeError in console/main.py:159
| - Update test file to use new function names
| - Add comprehensive type annotations to all public functions
| - Add Namespace import from argparse
| - Ignore ANN401 (Any types) in ruff config for kwargs and connections
| - All currentsessionid tests pass successfully
| 
* f8486cd 2026-03-28 Security: add path validation to folder module [J (eff)]
| Security: add path validation to folder module
| 
| - Add _validate_path() to prevent ReDoS and path traversal
| - Fix ruff E721: use isinstance() instead of type() == str
| - Fix ruff F841: unused variable and cursor bug
| - Fix buildlist() signature bug
| - Add path validation to all SQL queries using regex matching
| - Fix resource leaks in foldercompleter and noneexist()
| - Add module docstring with security considerations
| 
* 443716e 2026-03-28 security: improve session.py with thread safety and expiry validation [J (eff)]
| security: improve session.py with thread safety and expiry validation
| 
| - Use uuid.uuid4() for cryptographically secure session IDs
| - Add threading.local() for thread-safe currentsessionid storage
| - Add is_valid() helper to validate session expiry
| - Validate expiry in read(), get(), set(), and write() functions
| - Fix mutable default argument data={} to data=None
| - Add null check for buildsession() return value
| 
* 69f24f1 2026-03-28 Fix: query base tables directly in get_notifications instead of views [J (eff)]
| Fix: query base tables directly in get_notifications instead of views
| 
* 324e471 2026-03-28 Add checknotify console module and integrate with setup [J (eff)]
| Add checknotify console module and integrate with setup
| 
| - Add console/checknotify.py to create notify tables/views
| - Add checknotify wrapper to lib.py
| - Integrate checknotify into stage_one in main.py
| - Update notify.py to render templates at display time (not pre-rendered)
| 
* 81058d4 2026-03-27 fix: use echo_traceback in exception handlers [J (eff)]
| fix: use echo_traceback in exception handlers
| 
* f6090a6 2026-03-27 fix: add echo_traceback to notify.py exception handlers [J (eff)]
| fix: add echo_traceback to notify.py exception handlers
| 
* 02b34f4 2026-03-27 refactor: rename get_notification_count() to notify.count() [J (eff)]
| refactor: rename get_notification_count() to notify.count()
| 
* b0fa7cd 2026-03-27 feat: integrate notifications into getch() with F2 key display and bell sound [J (eff)]
| feat: integrate notifications into getch() with F2 key display and bell sound
| 
| - Add get_notification_count() to notify.py for retrieving unread count
| - Add notifycount() wrapper to member.py with auto-detected current user
| - Add 6 customizable notification skin colors to echo.py
| - Add get_notification_status() helper to screen.py for bottombar display
| - Integrate notification support into getch_str():
|   * Auto-detect pending notifications before input wait
|   * Emit bell once per session when notifications found
|   * Handle F2 key to display formatted notifications
|   * Reset bell flag after viewing
|   * Use thread-local storage for auto-detection
| - Update io_getch.spec with notification behavior documentation
| 
| Notifications display with [URGENCY] timestamp, recipient, and message.
| All colors are configurable via echo variables (notify.*color).
| Fully backward compatible - no changes to function signatures.
| 
* 35cbd51 2026-03-27 Implement notification system (notify.py) with SQL schema and 37 tests [J (eff)]
| Implement notification system (notify.py) with SQL schema and 37 tests
| 
| Implements comprehensive user notification system with:
| 
| Core Features:
| - Single unified send() function with flexible recipient targeting
| - Thread-safe in-memory queues for active sessions
| - Database persistence with full audit trail
| - Safe template-based messaging with variable substitution
| - Configurable notification types with rate limiting
| - One-way blocking relationships between users
| - Freeform group targeting with special @everyone support
| 
| Database Schema (7 tables + 4 views + 1 ENUM):
| - __notify: Core notification storage with bigserial IDs
| - __notify_recipient: Per-recipient delivery/read tracking
| - __notify_block: One-way blocking relationships
| - __notify_group: Group membership for targeting
| - __notify_type: Type registration with rate limits
| - __notify_rate_limit: Per-user rate limit tracking (DB-accessible)
| - Views: notify, notify_unread, notify_urgent, notify_blocked
| - ENUM: notify_urgency_enum (ROUTINE, IMPORTANT, URGENT, CRITICAL)
| 
| Public API (17 Functions):
| - send(): Unified notification dispatch
| - get_notifications(), get_queue(), get_urgent(): Consumption
| - mark_read(), mark_delivered(): Status tracking
| - register_type(), get_types(), set_rate_limit(): Type management
| - create_group(), add_to_group(), remove_from_group(), get_group_members(): Groups
| - block(), unblock(), is_blocked(), get_blocked(): Blocking
| 
| Testing:
| - 37 comprehensive unit tests covering validation, data structures, and queue operations
| - All tests passing
| - Full input validation with comprehensive error messages
| 
| Code Quality:
| - Follows bbsengine6 naming conventions (short singular table names, engine.__ prefix)
| - Thread-safe design with locks for shared state
| - Comprehensive input validation for all user inputs
| - Proper resource cleanup with context managers
| - Formatted and linted with ruff
| 
* 929636a 2026-03-27 Add notification system specification (notify.spec) [J (eff)]
| Add notification system specification (notify.spec)
| 
| Comprehensive specification for new bbsengine6.notify module:
| 
| - Single unified notify.send() function with flexible recipient targeting
| - Support for moniker targets, @group targets, and special @everyone
| - Magic @everyone expansion to active sessions + explicit group support
| - Template-based messaging with safe variable substitution
| - Urgency levels (ROUTINE, IMPORTANT, URGENT, CRITICAL)
| - Rate limiting with database-tracked limits
| - One-way blocking model for recipient privacy
| - 17 public API functions organized by purpose
| - 7 database tables + 4 views + 1 ENUM type
| - Comprehensive error handling and validation
| - Thread-safe design for concurrent access
| - Website integration queries provided
| - 638 lines of detailed specification
| 
* c09e9b9 2026-03-27 Add threading-based async event system for keyboard input [J (eff)]
| Add threading-based async event system for keyboard input
| 
| - Implement KeyEvent, EventHandler, KeyEventBus, EventDispatcher classes
| - Support both push (callbacks) and pull (queue) event consumption models
| - Thread-safe event firing with no blocking of main input thread
| - Optional callback timeout support to prevent slow handlers
| - Event filtering, history tracking, and error handling
| - Full backward compatibility - events disabled by default
| - 73 comprehensive unit and integration tests (all passing)
| - Comprehensive spec documenting architecture and API
| 
| Events auto-fire from getch_str() and propagate through all input functions
| (inputstring, inputchoice, etc) with source tracking.
| 
* 09d139a 2026-03-27 Fix F841 unused variables and F401 unused imports [J (eff)]
| Fix F841 unused variables and F401 unused imports
| 
| Auto-fixed many unused variables using ruff --fix.
| Removed unused imports from various modules.
| 
* 77aa1f9 2026-03-27 Fix F821 undefined name errors [J (eff)]
| Fix F821 undefined name errors
| 
| - Add import bbsengine6 as bbsengine to testsetarea.py
| - Add import psycopg to checkdatabase.py (used in exception handler)
| - Fix SystemBus() -> dbus.SystemBus() in checkloginid.py
| - Add os and tempfile imports to editor.py
| - Add FormItem base class to form.py
| - Add util import to input.py, fix verifyFileExistsReadable reference
| 
* 4af1549 2026-03-27 Fix LSP errors: replace ttyio with bbsengine6.io, remove unused imports [J (eff)]
| Fix LSP errors: replace ttyio with bbsengine6.io, remove unused imports
| 
| - Replace ttyio.echo/inputchar/inputstring with io.* in console/email.py
| - Replace ttyio.echo with io.echo in getdate.py and testsigcompleter.py
| - Remove unused psycopg imports from console check modules
| - Remove unused util imports from console check modules
| - Fix bug: rename _editemail to _edit in email.py
| 
* b5168d5 2026-03-25 Add multi-character hotkey support to Listbox class [J (eff)]
| Add multi-character hotkey support to Listbox class
| 
| - Add hotkey attribute to ListboxItem for registering item hotkeys
| - Add LISTBOX_ONKEY_BUFFER_LEN constant (5 chars max)
| - Add hotkeys parameter and _key_buffer for multi-char key buffering
| - Add _build_hotkey_map() to map hotkey strings to items
| - Add _navigate_to_item() to navigate to item (including page changes)
| - Modify onkey() to buffer keys, match exact hotkeys, and handle KEY_ESC
| 
* 2bed5f5 2026-03-24 Fix listbox item display by disabling wordwrap in echo calls [J (eff)]
| Fix listbox item display by disabling wordwrap in echo calls
| 
| The _display_item() and _display_blank_line() methods were calling io.echo()
| without specifying wordwrap=False. Since io.echo() defaults to wordwrap=True,
| descriptions containing text that exceeds the terminal width would get
| incorrectly wrapped, causing cosmetic issues where descriptions appear split
| over multiple lines in the listbox display.
| 
| This fixes project 9719 and similar cases where descriptions get displayed
| wrong in the project monitor listbox.
| 
* d7e4607 2026-03-24 Fix Article2PresidentListboxItem.display() signature to match ListboxItem contract [J (eff)]
| Fix Article2PresidentListboxItem.display() signature to match ListboxItem contract
| 
* dd7fccf 2026-03-23 Add robust type checking and error handling to expandrange() and collapserange() [J (eff)]
| Add robust type checking and error handling to expandrange() and collapserange()
| 
| - Both functions now accept str or list input
| - Added proper TypeError for invalid input types
| - Added ValueError for negative numbers
| - expandrange() autocorrects reversed ranges (e.g., '5-1' -> [1-5])
| - collapserange() automatically sorts input
| - Added comprehensive unit tests covering all cases
| 
* e14f447 2026-03-23 Add io.terminal.title() function, remove {settitle} echo command [J (eff)]
| Add io.terminal.title() function, remove {settitle} echo command
| 
* 6ef9c6e 2026-03-23 Bump version to 0.0.1.dev202603231010 [J (eff)]
| Bump version to 0.0.1.dev202603231010
| 
* 131790b 2026-03-23 demo_listbox_static_itemheight2: disable custom display function [J (eff)]
| demo_listbox_static_itemheight2: disable custom display function
| 
* c49732f 2026-03-22 - bbsengine6.listbox: cleaned up some debugging [Jeff MacDonald]
| - bbsengine6.listbox: cleaned up some debugging
| 
* 4e8b55c 2026-03-22 Comment out logentry() calls in listbox.py for cleaner output [J (eff)]
| Comment out logentry() calls in listbox.py for cleaner output
| 
* a1a2713 2026-03-22 Fix rendered_length() counting ACS control codes as visible characters [J (eff)]
| Fix rendered_length() counting ACS control codes as visible characters
| 
| Split ACS token kind into ACS_ON, ACS_OFF, and ACS_CHAR to distinguish
| control sequences (\x1b(0, \x1b(B) from visible ACS characters (e.g., 'x').
| Only count ACS_CHAR tokens in rendered_length().
| 
| This fixes listbox item padding appearing 1 character short after ACS
| commands like {acs:vline} were processed.
| 
| Added tests/unit/test_rendered_length.py with 8 tests covering:
| - Plain text matching len()
| - Color commands ignored
| - ACS characters counted correctly
| - Emojis counted
| - Mixed content handling
| - Whitespace handling
| - Variable expansion ignored
| 
* 2375dda 2026-03-22 Format code with ruff [J (eff)]
| Format code with ruff
| 
* 906fad8 2026-03-22 Fix listbox item width rendering with ANSI-aware padding [J (eff)]
| Fix listbox item width rendering with ANSI-aware padding
| 
| - echo.py: Make echo_iter() honor the wordwrap parameter by setting
|   _terminal_state.wordwrap, allowing rendered_length() to work correctly.
|   Also add guard to prevent false wordwrap when cursor_col >= width.
| 
| - listbox.py: Replace ljust() with rendered_length() for ANSI-aware padding.
|   Add truncation with '...' for content that exceeds contentwidth.
| 
* 2e149a8 2026-03-21 Pass parsed prgargs to module main function [J (eff)]
| Pass parsed prgargs to module main function
| 
| This ensures --roll and other CLI arguments are properly passed to module main()
| 
* c6f02ca 2026-03-21 Document buildargs() subparser parameter for CLI subcommands [J (eff)]
| Document buildargs() subparser parameter for CLI subcommands
| 
| Update the module spec to document the new optional 'subparser' parameter
| in buildargs(args=None, subparser=None, **kwargs). When a parent application
| uses argparse subparsers to implement git-style subcommands, it passes a
| subparser instance to buildargs(). Modules should add CLI arguments to the
| subparser using subparser.add_argument() and return None.
| 
| This allows dynamic CLI argument registration without hardcoding argparse
| arguments in the parent parser, keeping module-specific args co-located with
| each module's code.
| 
* e0bfe18 2026-03-20 Add convert_for_jsonb() helper and execute() wrapper for safe JSONB encoding [J (eff)]
| Add convert_for_jsonb() helper and execute() wrapper for safe JSONB encoding
| 
| - Add convert_for_jsonb() function that recursively converts type objects,
|   datetime instances, and other non-serializable types for JSONB storage
| - Add execute() wrapper that auto-converts params before passing to psycopg
| - Update database.update() and database.insert() to use convert_for_jsonb()
| - Update bbsengine6.member.buildrec() to use convert_for_jsonb()
| - Add comprehensive tests for convert_for_jsonb() and execute() (20 new tests)
| - Fixes 'Object of type type is not JSON serializable' error when datetime
|   type objects are stored in player attributes
| 
* fb531b7 2026-03-20 Fix JSON serialization: recursively convert datetime in dicts/lists [J (eff)]
| Fix JSON serialization: recursively convert datetime in dicts/lists
| 
* 1506a19 2026-03-20 database: fix JSON serialization for type objects and Jsonb wrappers [J (eff)]
| database: fix JSON serialization for type objects and Jsonb wrappers
| 
| - Add isinstance(v, type) check to handle type objects
| - Add isinstance(v, Jsonb) check to handle Jsonb wrapper objects
| - Add safety check for other non-serializable types
| 
* 869a944 2026-03-20 Correct product name and version in all spec files [J (eff)]
| Correct product name and version in all spec files
| 
| Product name is "bbsengine6" (not "bbsengine6 v0.0.1.dev").
| Version is "0.0.1.dev" (not "v0.0.1.dev"). Update all 8 spec files
| accordingly. Also fix file tree in index.spec to show index.spec
| as the master spec index under handbook/specs/.
| 
* 55a194b 2026-03-20 Strip bbsengine6- prefix from spec filenames, update product name to bbsengine6 v0.0.1.dev [J (eff)]
| Strip bbsengine6- prefix from spec filenames, update product name to bbsengine6 v0.0.1.dev
| 
| Rename 7 spec files: bbsengine6-*.spec → *.spec (architecture,
| decisions, dependencies, flows, modules, web, index). Update all
| product name/version strings in 9 spec files from "BBSEngine v6.0" /
| "BBSEngine6" / "**Version:** 6.0" to "bbsengine6 v0.0.1.dev" /
| "**Version:** v0.0.1.dev". Update all 24 cross-reference links in
| index.spec from specs/bbsengine6-*.spec to specs/*.spec. Update file
| tree diagram to reflect new directory layout.
| 
* 89df3cb 2026-03-20 Move handbook/*.spec to handbook/specs/, update cross-references [J (eff)]
| Move handbook/*.spec to handbook/specs/, update cross-references
| 
| All 7 root-level .spec files moved into handbook/specs/ alongside
| the existing module-specific specs (BESTPRACTICE, database, listbox,
| member, module, util). Update all relative paths in bbsengine6.spec
| from "filename.spec" to "specs/filename.spec" and reflect the new
| directory structure in the file tree diagram.
| 
* 89ed64a 2026-03-20 Update handbook specs to reflect current module.py architecture [J (eff)]
| Update handbook specs to reflect current module.py architecture
| 
| - Create handbook/specs/module.spec as canonical spec for module.py
|   covering all 8 functions (4 public, 2 private helpers, validate_function,
|   _is_help_request, _create_help_from_docstring), the correct execution flow,
|   and the runmodule alias
| - Fix bbsengine6-modules.spec: correct execution flow removes validate_function()
|   from the check()/run() path (uses _check_params() + inspect.signature()
|   instead), fix file size ~322→~359, add missing functions
| - Fix bbsengine6-architecture.spec: correct module flow diagram to show
|   _check_params() validation and --help/-h handling
| - Replace module.md stub with concise module system reference
| 
* e2639e6 2026-03-20 specs: remove non-existent bbsengine6/modules/ path references [J (eff)]
| specs: remove non-existent bbsengine6/modules/ path references
| 
| bbsengine6 has no modules/ directory. The module system uses
| importlib.import_module() with the full Python module name from
| sys.path -- these specs had stale references likely copied from asimov.
| 
| - bbsengine6-modules.spec: fix load() docstring to describe actual
|   import_module() behavior instead of 'bbsengine6.modules.<modulepath>'
| - bbsengine6-architecture.spec: rewrite Module File Structure section
|   to clarify modules are discovered via sys.path, remove fake path
| - bbsengine6-flows.spec: update module.load() sequence to reflect
|   actual import_module() via sys.path
| 
* 612c0fc 2026-03-20 util.py: add thread safety, fix bugs, and add spec [J (eff)]
| util.py: add thread safety, fix bugs, and add spec
| 
| - logentry(): add threading.Lock for handler registration; lazy-init
|   default_handler to avoid import-time failure on systems without /dev/log
| - diceroll(): use random.SystemRandom() for thread-safe randomness
| - heading(): fix float division bug (int(w-2)/2 -> (w-2)//2)
| - datestamp(): use isinstance() instead of type() comparisons; add
|   assertion guard for strftime target
| - getremoteaddr(): fix None dereference on missing SSH_CONNECTION
| - load_sql(): raise ImportError instead of silent None on missing backport
| - inputpassword(): remove dead commented-out code
| - filedisplay(): remove unused more/args locals
| - diceroll(): remove unused avg/median locals
| - Move all imports to top of module; fix E402/E401 violations
| - Remove unused syslog import
| - Add type hints throughout
| - Add handbook/specs/util.spec with thread-safety analysis
| - Update bbsengine6.spec TOC and file structure reference
| 
* 10abc8c 2026-03-20 Add member.spec to handbook [J (eff)]
| Add member.spec to handbook
| 
* 37368bd 2026-03-20 member.py: add thread safety, column allowlist, and standardize error handling [J (eff)]
| member.py: add thread safety, column allowlist, and standardize error handling
| 
| - Replace global currentid/currentmoniker with threading.local() for thread safety
| - Add ALLOWED_MEMBER_COLUMNS and _validate_fields() to prevent SQL injection
| - Replace all 'raise' and 'return False' with io.echo_traceback() and return None
| - Fix bugs: setattrs passing wrong arg, getflags calling database.connect(pool) instead of (args, pool)
| - Remove dead code in checkpassword and unreachable return in update
| - Clean up unused imports and variables
| 
* 9ac00ef 2026-03-19 Remove redundant conn.commit() calls - auto_commit handles this [J (eff)]
| Remove redundant conn.commit() calls - auto_commit handles this
| 
* d97e03a 2026-03-19 Fix INTRANS: add auto_commit=True to database.connect() [J (eff)]
| Fix INTRANS: add auto_commit=True to database.connect()
| 
| Now database.connect() auto-commits by default before returning
| connection to pool. Set auto_commit=False for multi-statement
| transactions that need explicit commit control.
| 
| This is backwards compatible - existing code that manually commits
| will still work (double commit is fine).
| 
* fad7bf3 2026-03-19 Add database.with_connection utility for consistent connection handling [J (eff)]
| Add database.with_connection utility for consistent connection handling
| 
| This utility handles conn/pool logic and ensures commits happen,
| preventing INTRANS errors when connections are returned to pool.
| 
* dc57dd9 2026-03-19 Fix JSON serialization: handle type objects and datetime in database.update [J (eff)]
| Fix JSON serialization: handle type objects and datetime in database.update
| 
| - Convert any type objects (like datetime.datetime) to strings
| - Use isinstance() instead of type() for better type checking
| - Apply same fix to datetime.datetime instances
| 
* 95c112b 2026-03-19 Fix JSON serialization: handle datetime type objects in player.buildrec [J (eff)]
| Fix JSON serialization: handle datetime type objects in player.buildrec
| 
| The issue was that when attribute values are datetime types (not instances),
| they need to be converted to ISO format strings before JSON serialization.
| 
| Also handles datetime.datetime instances.
| 
* 6d7d143 2026-03-19 Fix database.exists to commit after query [J (eff)]
| Fix database.exists to commit after query
| 
* 2a83d0e 2026-03-19 Fix duplicate pool.putconn call that caused error [J (eff)]
| Fix duplicate pool.putconn call that caused error
| 
* 0b20648 2026-03-19 Add pool caching to fix 'connection to wrong pool' error [J (eff)]
| Add pool caching to fix 'connection to wrong pool' error
| 
| The issue was that each call to getpool() created a new pool. When
| different parts of the code created separate pools and then tried to
| return connections, they would return to the wrong pool.
| 
| Now getpool() caches pools by DSN so the same pool is reused.
| 
* 089a783 2026-03-19 Revert pool caching, fix test to use mock [J (eff)]
| Revert pool caching, fix test to use mock
| 
* 1846b28 2026-03-19 Fix INTRANS: commit after getcurrentmoniker gets own connection [J (eff)]
| Fix INTRANS: commit after getcurrentmoniker gets own connection
| 
| The issue was that when getcurrentmoniker() received neither conn nor pool,
| it would get its own connection from the pool, run a query, but NOT commit
| before returning the connection to the pool. This left the connection in
| INTRANS state.
| 
| Also cleaned up debug logging.
| 
* 449ba8d 2026-03-19 Add traceback to debug second getcurrentmoniker call [J (eff)]
| Add traceback to debug second getcurrentmoniker call
| 
* 7ae7065 2026-03-19 Add debug logging to trace INTRANS [J (eff)]
| Add debug logging to trace INTRANS
| 
* 526a833 2026-03-19 Fix: use pop() to remove conn from kwargs, restore after getcurrentmoniker [J (eff)]
| Fix: use pop() to remove conn from kwargs, restore after getcurrentmoniker
| 
| Using pop() prevents 'multiple values for keyword argument conn' error
| when conn is passed both explicitly and in **kwargs.
| 
* 977ff9f 2026-03-19 Fix INTRANS: pass conn to getcurrentmoniker in getmembersession [J (eff)]
| Fix INTRANS: pass conn to getcurrentmoniker in getmembersession
| 
| The issue was that getmembersession() called member.getcurrentmoniker()
| without passing the connection. This caused getcurrentmoniker to get
| its own connection from the pool, run a query, and return the connection
| to the pool without committing, causing INTRANS rollback.
| 
| Also cleaned up debug logging added during investigation.
| 
* 1e9e313 2026-03-19 Add debug logging to trace second connection in getcurrentmoniker [J (eff)]
| Add debug logging to trace second connection in getcurrentmoniker
| 
* 3154bfd 2026-03-19 Add debug logging to trace INTRANS issue [J (eff)]
| Add debug logging to trace INTRANS issue
| 
| - session.start: log txstatus before/after commit
| - database.connect: log txstatus when returning connection to pool
| 
* 39330ba 2026-03-19 Add debug logging to trace INTRANS issue [J (eff)]
| Add debug logging to trace INTRANS issue
| 
* 513be8d 2026-03-19 Refactor session module: consistent conn/pool handling pattern [J (eff)]
| Refactor session module: consistent conn/pool handling pattern
| 
| All session functions now follow the same pattern:
| 1. If conn is provided, use it directly
| 2. If conn is None, check pool
| 3. If pool is provided, get conn from pool with context manager
| 4. If neither conn nor pool, error out with message
| 
| This ensures:
| - Connections are always properly managed
| - Commits happen before connections are returned to pool
| - Consistent error handling across all functions
| 
* 91d32c1 2026-03-19 Fix INTRANS rollback: ensure conn passed to inner functions and commits [J (eff)]
| Fix INTRANS rollback: ensure conn passed to inner functions and commits
| 
| The root cause of INTRANS rollbacks was:
| 1. getmembersession() and read() got their own connections, ran queries,
|    but didn't commit before returning the connection to the pool
| 2. start() and updatelastactivity() called inner functions without passing
|    the connection, so those functions got their own connections
| 
| Fixes:
| - getmembersession(): add conn.commit() when getting own connection
| - read(): add conn.commit() when getting own connection
| - start(): pass conn to getmembersession(), read(), database.insert()
| - updatelastactivity(): pass conn to read() and write()
| 
* 65b1c8e 2026-03-19 Add comprehensive tests for session module [J (eff)]
| Add comprehensive tests for session module
| 
| Tests cover:
| - session.build() - creating session dicts
| - session.buildsession() - creating new sessions
| - session.set() - setting session data, commit behavior, reset vs append
| - session.get() - retrieving session data with defaults
| - session.write() - updating sessions with commit
| - session.read() - reading sessions with currentsessionid fallback
| - session.garbagecollect() - cleanup behavior
| - session.count() - counting sessions
| - connection management - ensuring commits happen
| 
| Also fixed: session.write() now returns True on success
| 
* dcac5bb 2026-03-19 Fix INTRANS rollback: add conn.commit() when existing session found [J (eff)]
| Fix INTRANS rollback: add conn.commit() when existing session found
| 
| When getmembersession() returns an existing session, start() was setting
| currentsessionid but not committing the transaction before returning the
| connection to the pool. This left the connection in INTRANS state.
| 
| Also includes previous fixes from commit 526da84:
| - session.set(): proper connection management with commit
| - session.read(): use context manager for connection
| - session.write(): fix undefined _work() reference
| - session.start(): fix database.insert() missing table name
| 
* 526da84 2026-03-19 Fix INTRANS connection rollback in session management [J (eff)]
| Fix INTRANS connection rollback in session management
| 
| - session.set(): Add missing conn.commit() and proper connection management
| - session.read(): Use context manager to ensure connection is returned to pool
| - session.write(): Fix undefined _work() reference, restructure connection handling
| - session.start(): Fix database.insert() call missing table name
| 
| These fixes ensure connections are properly committed and returned to the pool,
| preventing psycopg INTRANS state rollbacks.
| 
* 3ee8820 2026-03-19 Fix database.update() to wrap dict/list values in Jsonb for jsonb columns [J (eff)]
| Fix database.update() to wrap dict/list values in Jsonb for jsonb columns
| 
* 91f14f3 2026-03-18 database: add commit param to insert(), default commit=True for update() and insert() [J (eff)]
| database: add commit param to insert(), default commit=True for update() and insert()
| 
| - insert(): add commit=True parameter; refactor _work() to capture return
|   value, then commit, then return — avoids early returns from cursor context
| - update(): change commit default from False to True
| - SQL f-strings reformatted to sql.SQL() composition (ruff format)
| 
* d10115c 2026-03-18 Update database.spec: document connect() uses getconn/putconn, raises if pool is None, shows correct usage pattern [J (eff)]
| Update database.spec: document connect() uses getconn/putconn, raises if pool is None, shows correct usage pattern
| 
* 9ba6307 2026-03-18 Use pool kwarg passed to connect() instead of calling getpool(). Raise if pool is None. [J (eff)]
| Use pool kwarg passed to connect() instead of calling getpool(). Raise if pool is None.
| 
* b8a5853 2026-03-18 Fix connect() to use getconn/putconn — was returning pool.connection() directly which is a GeneratorContextManager, not a Connection. Restore context manager pattern with proper connection lifecycle. [J (eff)]
| Fix connect() to use getconn/putconn — was returning pool.connection() directly which is a GeneratorContextManager, not a Connection. Restore context manager pattern with proper connection lifecycle.
| 
* e19803a 2026-03-18 Add exception handling to connect() for robust error reporting [J (eff)]
| Add exception handling to connect() for robust error reporting
| 
* 8cb3a0b 2026-03-18 Rollback connect() to non-generator, add robust pool cleanup in tests [J (eff)]
| Rollback connect() to non-generator, add robust pool cleanup in tests
| 
* 05f51c0 2026-03-18 Add SQL injection tests for database functions [J (eff)]
| Add SQL injection tests for database functions
| 
| - Test parse_dsn, mogrifysql, _table_identifier with malicious input
| - Integration tests verify graceful failure with real database
| - All 82 tests pass, pg_class table verified intact
| 
* 5d523c3 2026-03-18 Add database.py tests with Unix socket and TCP support [J (eff)]
| Add database.py tests with Unix socket and TCP support
| 
| - Add testdatabase.py with 65 tests for database functions
| - Fix make_dsn() to omit empty string values from DSN
| - Support both Unix socket and TCP connections
| - Use getpass.getuser() instead of hardcoded username
| 
* da18e56 2026-03-18 Use f-strings for sql.SQL composition in database.py [J (eff)]
| Use f-strings for sql.SQL composition in database.py
| 
* bb33566 2026-03-18 database.py: fix connection leaks, closures, and error handling [J (eff)]
| database.py: fix connection leaks, closures, and error handling
| 
| - Convert connect() to context manager that returns connections to pool
| - Fix mogrifysql() SQL injection vulnerability with safe escaping
| - Fix insert() closure bug by moving _work() after query/dat construction
| - Standardize error handling with echo_traceback() returning False
| - Update spec to reflect context manager pattern and error handling
| 
* 320d35f 2026-03-16 - bbsengine6/io/screen.py: commented out debuging echo() calls [Jeff MacDonald]
| - bbsengine6/io/screen.py: commented out debuging echo() calls
| 
* 2f9df9d 2026-03-15 Fix missing quote in listbox.item.highlighted skin key [J (eff)]
| Fix missing quote in listbox.item.highlighted skin key
| 
* dda7c02 2026-03-15 Convert dict and list values to Jsonb in insert [J (eff)]
| Convert dict and list values to Jsonb in insert
| 
* 98129a5 2026-03-15 Add debug logging for right() callable in setbottombar [J (eff)]
| Add debug logging for right() callable in setbottombar
| 
* f433622 2026-03-15 Improve error messages in module check for main function [J (eff)]
| Improve error messages in module check for main function
| 
* 300c2a3 2026-03-15 Bump version to 0.0.1.dev202603142153 [J (eff)]
| Bump version to 0.0.1.dev202603142153
| 
* c9280ea 2026-03-15 Add getdate module for parsing date expressions [J (eff)]
| Add getdate module for parsing date expressions
| 
* dfe5b80 2026-03-15 Add listbox skin variables and type validation to echo [J (eff)]
| Add listbox skin variables and type validation to echo
| 
| - Add listbox.boxcolor, listbox.titlecolor, listbox.item.normal,
|   listbox.item.highlighted, listbox.item.disabled, listbox.bgcolor
|   to _skin dict for runtime variable access
| - Add type check in tokenize() to warn if text is not str
| 
* a02343c 2026-03-12 Add demo_article2_givenyear - list presidents by year in 4 mutually exclusive groups [J (eff)]
| Add demo_article2_givenyear - list presidents by year in 4 mutually exclusive groups
| 
* dc671cd 2026-03-12 Update version; add inputchar alias for inputchoice in io module [J (eff)]
| Update version; add inputchar alias for inputchoice in io module
| 
* f4fbcef 2026-03-12 session: Fix _work() call signature in start(); remove dead code [J (eff)]
| session: Fix _work() call signature in start(); remove dead code
| 
* 5e4fabb 2026-03-12 Refactor setpassword to use connection pattern; fix getcurrentmoniker call in setflag [J (eff)]
| Refactor setpassword to use connection pattern; fix getcurrentmoniker call in setflag
| 
* b452b56 2026-03-12 Remove extra blank line in database.py [J (eff)]
| Remove extra blank line in database.py
| 
* df402ed 2026-03-11 Add init() function to listbox for color variable setup [J (eff)]
| Add init() function to listbox for color variable setup
| 
* 0443e1d 2026-03-10 Update version config and pyproject.toml [J (eff)]
| Update version config and pyproject.toml
| 
* 9dfb7cd 2026-03-10 bbsengine6/io: export getch from getch module [J (eff)]
| bbsengine6/io: export getch from getch module
| 
* 4d87a3c 2026-03-10 Add noqa for Jsonb import - used externally via database.Jsonb() [J (eff)]
| Add noqa for Jsonb import - used externally via database.Jsonb()
| 
* 01a30de 2026-03-10 Fix schema-qualified table names in database.update() and database.insert() [J (eff)]
| Fix schema-qualified table names in database.update() and database.insert()
| 
| - Add _table_identifier() helper to properly handle schema.table names
| - psycopg.sql.Identifier('empyre.__player') creates literal identifier with dots
| - Now uses sql.Identifier('empyre', '__player') to generate correct SQL
| - Fixes 'relation does not exist' error when saving player data
| 
* 3446dc6 2026-03-10 Export inputstring/inputinteger/inputboolean/inputchoice from io module [J (eff)]
| Export inputstring/inputinteger/inputboolean/inputchoice from io module
| 
* 4f9947d 2026-03-08 Export setvar/getvar/register_emoji/register_emojis from io module [J (eff)]
| Export setvar/getvar/register_emoji/register_emojis from io module
| 
* 23be3c6 2026-03-07 Add inputdate.py module using getdate-next package [J (eff)]
| Add inputdate.py module using getdate-next package
| 
* 2633446 2026-03-04 Sync io with asimov.io: add deprecation headers, update imports/signatures [J (eff)]
| Sync io with asimov.io: add deprecation headers, update imports/signatures
| 
* 33a46c9 2026-02-27 Fix listbox item padding and demo prompts [J (eff)]
| Fix listbox item padding and demo prompts
| 
| - Change ljust padding fill char from '.' to ' '
| - Remove spurious io.echo prompts before listbox.run() calls
| - Update .run() prompts to match the prompts that were removed
| 
* aadad0e 2026-02-27 Fix listbox item padding to use space instead of dot [J (eff)]
| Fix listbox item padding to use space instead of dot
| 
* aefa822 2026-02-27 Fix listbox title centering regression [J (eff)]
| Fix listbox title centering regression
| 
| Remove spurious '*' character that was being appended to centered
| titles when title length and width had the same parity, causing the
| title line to overflow past the right border.
| 
* 6ada53d 2026-02-26 Update listbox width calculations, fix title centering, update demo specs [jam]
| Update listbox width calculations, fix title centering, update demo specs
| 
* fc2819a 2026-02-26 Fix listbox title centering alignment [jam]
| Fix listbox title centering alignment
| 
* 9647e79 2026-02-26 Fix listbox width calculations for borders and title [jam]
| Fix listbox width calculations for borders and title
| 
* 1d10eee 2026-02-25 Update spec: add bottom bar, helper functions, None value handling [Jeff MacDonald]
| Update spec: add bottom bar, helper functions, None value handling
| 
| - Document compose_person_name() and setbottombar() helper functions
| - Document bottom bar navigation showing president and category
| - Document [debug] indicator when --debug flag is set
| - Note that None values are shown blank in debug mode
| 
* 11b81cf 2026-02-25 Add compose_person_name() helper function [Jeff MacDonald]
| Add compose_person_name() helper function
| 
| Composes display name from available name parts (name_common, name_given,
| name_sur) in order of preference. Returns '[NEEDINFO]' with warning if no
| name parts available.
| 
* 4bb13cc 2026-02-25 Update demo_listbox_masterdetail: add args param, skip None values, fix attractions listbox, return to categories [Jeff MacDonald]
| Update demo_listbox_masterdetail: add args param, skip None values, fix attractions listbox, return to categories
| 
* c2c2624 2026-02-25 Update spec with echovars documentation [Jeff MacDonald]
| Update spec with echovars documentation
| 
* aadfe0a 2026-02-25 Update listbox with echovars and fix attraction queries [Jeff MacDonald]
| Update listbox with echovars and fix attraction queries
| 
| - Add echovars for listbox: boxcolor, titlecolor, item.* (normal, highlighted, disabled)
| - Remove titlebox blank lines, reduce TITLE_BOX_HEIGHT from 4 to 2
| - Fix attraction_join SQL to use correct key columns (person_key, key)
| - Change item colors to use {white} and {inverse}
| 
* e771a81 2026-02-25 Update demo_listbox_masterdetail: add listboxes for detail views [Jeff MacDonald]
| Update demo_listbox_masterdetail: add listboxes for detail views
| 
| - Add listbox for edu, elector, attractions, attraction_* detail selection
| - Show single items directly without listbox
| - Display all columns with labelcolor/valuecolor formatting
| - Include attraction_hour and attraction_social_media in attractions
| - Fix various table/column name mismatches
| 
* 4e9529c 2026-02-25 Add demo_listbox_masterdetail: master-detail view for US Presidents [Jeff MacDonald]
| Add demo_listbox_masterdetail: master-detail view for US Presidents
| 
| - Two-listbox design: president list (master) + category list (detail)
| - Dynamic category discovery based on available data per president
| - Supports: person, edu, elector, attractions, attraction_*, etc.
| - Handles different key column names per table (person_key, key, place_key)
| - Special handling for attraction_join with multiple keys
| 
* 1346b55 2026-02-25 feat: add new PHP modules, Python utilities, templates, and tests [Jeff MacDonald]
| feat: add new PHP modules, Python utilities, templates, and tests
| 
* 9ab5dbd 2026-02-25 docs: add LOG.md and NOTES.md [Jeff MacDonald]
| docs: add LOG.md and NOTES.md
| 
* f6b5db4 2026-02-25 chore: add .gitignore patterns for build artifacts and caches [Jeff MacDonald]
| chore: add .gitignore patterns for build artifacts and caches
| 
* 4d82c36 2026-02-25 misc: various updates across php, python, and skin modules [Jeff MacDonald]
| misc: various updates across php, python, and skin modules
| 
* 7d71b3f 2026-02-24 feat(getch): add timeout=None to block indefinitely; add height comparison to demo [Jeff MacDonald]
| feat(getch): add timeout=None to block indefinitely; add height comparison to demo
| 
* 954a4f3 2026-02-24 docs: add spec files for demo_listbox_*.py demos [Jeff MacDonald]
| docs: add spec files for demo_listbox_*.py demos
| 
* 3500a13 2026-02-24 fix: swap reset and restorecursor in finally block [Jeff MacDonald]
| fix: swap reset and restorecursor in finally block
| 
* 3ca2f14 2026-02-24 fix: add database and schema existence checks, use database.buildargs() [Jeff MacDonald]
| fix: add database and schema existence checks, use database.buildargs()
| 
* 6501b8b 2026-02-24 fix: add robust error handling for database pool and connections [Jeff MacDonald]
| fix: add robust error handling for database pool and connections
| 
* 4acc154 2026-02-24 fix: use database.getpool() to create connection pool in demo [Jeff MacDonald]
| fix: use database.getpool() to create connection pool in demo
| 
* 724199a 2026-02-24 fix: syntax error in ListboxCursor - positional args must be keyword args [Jeff MacDonald]
| fix: syntax error in ListboxCursor - positional args must be keyword args
| 
* 630ecf3 2026-02-24 feat: add ListboxCursor subclass for database cursor lazy-loading [Jeff MacDonald]
| feat: add ListboxCursor subclass for database cursor lazy-loading
| 
| - Create listboxcursor.py with ListboxCursor that extends Listbox
| - Supports scrollable database cursor for lazy-loading pages
| - Update demo to use new ListboxCursor and custom_keys dict
| - Rename demo_listbox_database to demo_listbox_cursor
| - Use 'selected' status instead of 'select'
| - Fix io.getterminalheight() to io.terminal.height()
| 
* f4383fc 2026-02-24 listbox: add _highlight_item(), ListboxResult('redraw'), and fix lint [Jeff MacDonald]
| listbox: add _highlight_item(), ListboxResult('redraw'), and fix lint
| 
| - Add _highlight_item(item_index) method for lightweight re-highlighting
| - Add ListboxResult('redraw') for custom key handlers to trigger full redraw
| - Update _display() to automatically highlight current item
| - Add prompt attribute accessible to key handlers
| - Update return types for key handlers (bool | ListboxResult | None)
| - Fix lint in __init__.py (unused import)
| - Fix lint in blurb.py (duplicate import, undefined vars)
| - Update listbox.spec documentation
| 
* 9ab873a 2026-02-24 test: add unit tests for {cha} cursor horizontal absolute command [Jeff MacDonald]
| test: add unit tests for {cha} cursor horizontal absolute command
| 
| - Add testechocha.py with 5 test cases for {cha} echo command
| - Document {cha} command in bbsengine6-modules.spec
| 
* feaa8a8 2026-02-24 Make listbox prompt a required positional argument and standardize demo formatting [Jeff MacDonald]
| Make listbox prompt a required positional argument and standardize demo formatting
| 
| - Changed listbox.run() to require prompt as positional argument (no default)
| - Updated demo_listbox_static.py, demo_listbox_static_itemheight2.py, and demo_listbox_database.py to:
|   - Define prompt variable for each demo (basename + colon + space)
|   - Pass prompt to lb.run() as required argument
|   - Use ListboxResult.status and .item attributes consistently
|   - Format result output with {promptcolor} and {valuecolor} echovars
| - Fixed lint errors: removed unused imports/variables, fixed None comparisons
| - Added best practice: io.echo() calls MUST use f-strings for escape sequence processing
| - Disabled F541 linter rule (f-string without placeholders) in ruff.toml for echo commands
| - Updated listbox.spec to document prompt as required argument
| 
* c7cfe4b 2026-02-24 fix: key_pageup rings bell when on first item of first page [Jeff MacDonald]
| fix: key_pageup rings bell when on first item of first page
| 
* 297caf1 2026-02-24 fix: key_pageup/pagedown jump to first/last item instead of bell [Jeff MacDonald]
| fix: key_pageup/pagedown jump to first/last item instead of bell
| 
* a739073 2026-02-24 feat: add itemheight support to listbox with multi-line items [Jeff MacDonald]
| feat: add itemheight support to listbox with multi-line items
| 
| - Add itemheight parameter to support variable height items
| - Add _position_from_prompt() helper for cursor positioning
| - Fix key handlers (key_up, key_down, key_home, key_end, key_pageup, key_pagedown)
| - Add demo with itemheight=3 and 28 items for incomplete pages
| 
* fac3796 2026-02-24 refactor: rename BORDER_HLINE_WIDTH to BORDER_CORNER_WIDTH [Jeff MacDonald]
| refactor: rename BORDER_HLINE_WIDTH to BORDER_CORNER_WIDTH
| 
* 00f7a79 2026-02-24 refactor: rename BORDER_LINE_WIDTH to BORDER_HLINE_WIDTH for clarity [Jeff MacDonald]
| refactor: rename BORDER_LINE_WIDTH to BORDER_HLINE_WIDTH for clarity
| 
| - More descriptive name that explicitly indicates it's for horizontal line width
| - Updated all references in listbox.py and listbox.spec
| 
* 9a8a087 2026-02-24 refactor: replace border width magic numbers with BORDER_WIDTH_LEFT and BORDER_WIDTH_RIGHT [Jeff MacDonald]
| refactor: replace border width magic numbers with BORDER_WIDTH_LEFT and BORDER_WIDTH_RIGHT
| 
| - Replaced 3*2 and 6 with BORDER_WIDTH_LEFT (3) and BORDER_WIDTH_RIGHT (3)
| - Replaced all contentwidth - 2 with contentwidth - BORDER_LINE_WIDTH
| - Added BORDER_LINE_WIDTH = 2 constant for border line width calculations
| - Updated listbox.spec to document new border width constants
| - Allows for asymmetric borders if left and right widths need to differ
| 
* cf94a56 2026-02-24 refactor: replace magic number 4 with CONTENT_PADDING constant in listbox [Jeff MacDonald]
| refactor: replace magic number 4 with CONTENT_PADDING constant in listbox
| 
| - Added CONTENT_PADDING = 4 class constant to document the padding used for item content
| - Updated _display_item() to use self.CONTENT_PADDING instead of hardcoded 4
| - Updated _display_blank_line() to use self.CONTENT_PADDING instead of hardcoded 4
| - Updated listbox.spec to document CONTENT_PADDING constant
| - Fixed f-string linting issues (removed unnecessary f prefix from strings without placeholders)
| 
* a7e5c67 2026-02-23 docs: add integration tests and finalize features [Jeff MacDonald]
| docs: add integration tests and finalize features
| 
* e21af08 2026-02-23 feat: add shell completion with argcomplete [Jeff MacDonald]
| feat: add shell completion with argcomplete
| 
| Phase 3: Shell Completion (#5)
| 
| Changes:
| - setup.py: Add argcomplete dependency
| 
| - console/__main__.py: Integrate argcomplete
|   - Imports argcomplete if available (graceful fallback if not)
|   - Calls argcomplete.autocomplete() for shell completion
| 
| - shell_completion/install_completion.sh: Installation script
|   - Installs bash completion
|   - Installs zsh completion
|   - Provides instructions for manual setup
| 
| Usage:
|   pip install argcomplete
|   make install-completion
|   # Or: bash shell_completion/install_completion.sh
| 
| After installation:
|   zoidoffice m<TAB>           # Completes to: member, memberapproval
|   zoidoffice --<TAB>         # Completes global args
|   zoidoffice member --<TAB>  # Completes module args (if defined)
| 
* e03cd98 2026-02-23 feat: implement dynamic module discovery with caching [Jeff MacDonald]
| feat: implement dynamic module discovery with caching
| 
| Phase 2: Dynamic Module Discovery (#1)
| 
| Changes:
| - console/lib.py: Add discover_console_modules() function
|   - Scans bbsengine6.console package for .py files
|   - Validates modules: must have main() and docstring
|   - Extracts first line of docstring as help text
| 
| - console/lib.py: Add caching behavior
|   - Cache in normal mode (fast)
|   - Refresh in debug mode (for development)
|   - clear_module_cache() function to force refresh
| 
| - console/lib.py: Update build_subcommand_parser()
|   - Now uses dynamic discovery instead of hardcoded list
|   - Passes args for debug mode detection
| 
| Benefits:
| - New console modules automatically appear in CLI
| - No need to maintain hardcoded subcommand list
| - Only includes properly documented modules
| 
| Tests:
| - tests/feature_1/: Comprehensive unittest suite
|   - test_discovery.py: Discovery and validation tests
| 
* b329043 2026-02-23 feat: add module-specific argument support [Jeff MacDonald]
| feat: add module-specific argument support
| 
| Phase 1: Module-Specific Arguments (#2)
| 
| Changes:
| - console/__main__.py: Use parse_known_args() to separate argv at subcommand
| - module.py: Update run() to handle clean argv without subcommand name
| - console/lib.py: Update handle_subcommand() to pass argv and add documentation
| - skel/__main__.py: Update help handling
| 
| Enables:
| - zoidoffice member --filter sysop
| - zoidoffice member --add --amount 100
| - Any custom arguments via module's buildargs()
| 
| Backward compatible:
| - All existing modules work unchanged
| - Modules returning None from buildargs() still work
| - Global args still available at console level
| 
| Tests:
| - tests/feature_2/: Comprehensive unittest suite
|   - test_argument_separation.py: argv splitting logic
|   - test_custom_args.py: custom argument parsing
|   - test_backward_compatibility.py: verify no breaking changes
| 
* ed1c9a6 2026-02-23 feat: comprehensive help handling with argparse subcommands [Jeff MacDonald]
| feat: comprehensive help handling with argparse subcommands
| 
| - module.py: Add help request detection and auto-generate help from docstrings
|   - _is_help_request(): Check if argv contains --help or -h
|   - _create_help_from_docstring(): Create parser from module docstring
|   - Enhanced SystemExit handling: distinguish help (exit 0) from errors (exit ≠ 0)
| 
| - console/lib.py: Add argparse subcommand support
|   - build_subcommand_parser(): Create parser with member, session, memberapproval
|   - handle_subcommand(): Route subcommands to appropriate modules
| 
| - console/__main__.py: Refactor to use subcommands and return to menu on error
|   - Support both subcommand (zoidoffice member) and no-arg (zoidoffice) modes
|   - Don't exit on errors, return to menu for interactive use
| 
| - skel/__main__.py: Add explicit help handling without exiting
| 
| - Module docstrings: Add documentation to all console check modules
|   - checkroles, checksuperuser, checkextensions, checkschema
|   - checkfunctions, checkdatabase, checkflag, checkwebserverrole
|   - memberapproval, session
| 
| This enables:
| - zoidoffice --help (shows all subcommands)
| - zoidoffice member --help (shows member help with auto-generated parser)
| - zoidoffice payment --help (shows help from module docstring if no buildargs)
| - Proper error handling without forced exits
| 
* 282723c 2026-02-23 Add comprehensive BBSEngine v6.0 master specification [Jeff MacDonald]
| Add comprehensive BBSEngine v6.0 master specification
| 
| - bbsengine6.spec: Master index and overview
| - bbsengine6-architecture.spec: Layered and domain architecture
| - bbsengine6-modules.spec: Complete module specifications with signatures
| - bbsengine6-flows.spec: Data flows and workflow sequences
| - bbsengine6-web.spec: Web layer architecture and integration
| - bbsengine6-dependencies.spec: Dependency matrix and rationale
| - bbsengine6-decisions.spec: Architectural decisions and alternatives
| 
| Total: 178 KB of comprehensive system documentation
| Audience: Developers and architects
| Focus: Structure only (not performance details)
| Scope: Terminal backend primary, web layer secondary but thoroughly documented
| 
* 1f6e179 2026-02-23 Remove backup files (tag: v202602231857) [Jeff MacDonald]
| Remove backup files
| 
* 706a1f9 2026-02-23 Update handbook and js files [Jeff MacDonald]
| Update handbook and js files
| 
* 25991bd 2026-02-23 Rename listbox_next to listbox [Jeff MacDonald]
| Rename listbox_next to listbox
| 
* 81cbf68 2026-02-23 Rename listbox_next to listbox [Jeff MacDonald]
| Rename listbox_next to listbox
| 
* a5f907c 2026-02-23 Move spec files to handbook/specs/ [Jeff MacDonald]
| Move spec files to handbook/specs/
| 
* c030ab1 2026-02-23 Update spec with docstring requirement note [Jeff MacDonald]
| Update spec with docstring requirement note
| 
* 46af116 2026-02-23 Add docstrings to key handler methods [Jeff MacDonald]
| Add docstrings to key handler methods
| 
* b5ba922 2026-02-23 Add docstrings to database.py functions [Jeff MacDonald]
| Add docstrings to database.py functions
| 
* f645ffa 2026-02-23 Update spec: commit() now properly calls conn.commit() [Jeff MacDonald]
| Update spec: commit() now properly calls conn.commit()
| 
* 4882cb9 2026-02-23 Fix commit() to properly call conn.commit() [Jeff MacDonald]
| Fix commit() to properly call conn.commit()
| 
* 32e10cf 2026-02-23 Fix remaining issues: update() return type, commit() dead code, make_dsn() attribute check, parse_dsn() error handling, buildargs() mutable default, cursor() annotations. Move spec to handbook/specs/ [Jeff MacDonald]
| Fix remaining issues: update() return type, commit() dead code, make_dsn() attribute check, parse_dsn() error handling, buildargs() mutable default, cursor() annotations. Move spec to handbook/specs/
| 
* e15b306 2026-02-23 Standardize error handling - return False on pool/conn errors, consistent return types [Jeff MacDonald]
| Standardize error handling - return False on pool/conn errors, consistent return types
| 
* 96b3e44 2026-02-23 Fix SQL injection in update(), insert(), createrol() - use sql.Identifier() [Jeff MacDonald]
| Fix SQL injection in update(), insert(), createrol() - use sql.Identifier()
| 
* f3c87de 2026-02-23 Lint database.py, add type annotations, add database.spec [Jeff MacDonald]
| Lint database.py, add type annotations, add database.spec
| 
* f3518d4 2026-02-23 Refactor key handlers into dict with private methods [Jeff MacDonald]
| Refactor key handlers into dict with private methods
| 
* 98bb3cf 2026-02-23 Add custom key handler demo to listbox_next [Jeff MacDonald]
| Add custom key handler demo to listbox_next
| 
* 3a51c07 2026-02-23 Add custom_keys parameter for handling custom key callbacks; add data field to ListboxResult [Jeff MacDonald]
| Add custom_keys parameter for handling custom key callbacks; add data field to ListboxResult
| 
* 640486b 2026-02-23 Fix KEY_HOME and KEY_END cursor positioning; use f-strings for all echo() calls [Jeff MacDonald]
| Fix KEY_HOME and KEY_END cursor positioning; use f-strings for all echo() calls
| 
* 2dc2af2 2026-02-23 Use {cursorup} for KEY_UP after redraw, simplify {cud} to no args (tag: v202602231454) [Jeff MacDonald]
| Use {cursorup} for KEY_UP after redraw, simplify {cud} to no args
| 
* d655d52 2026-02-23 Add onkey() return True/False for handled/not handled; add cursor movement {cud:1} after redrawing items [Jeff MacDonald]
| Add onkey() return True/False for handled/not handled; add cursor movement {cud:1} after redrawing items
| 
* b51924f 2026-02-23 Add _terminal_state_stack_enabled flag for VT-compliant save/restore cursor behavior [Jeff MacDonald]
| Add _terminal_state_stack_enabled flag for VT-compliant save/restore cursor behavior
| 
* 4985c3d 2026-02-23 Fix cursor positioning and _display_item defaults [Jeff MacDonald]
| Fix cursor positioning and _display_item defaults
| 
* e052dd1 2026-02-23 Update spec: highlight uses end='', document cursor handling [Jeff MacDonald]
| Update spec: highlight uses end='', document cursor handling
| 
* 130fe23 2026-02-23 Fix left border to use ' {vline} ' with adjusted contentwidth [Jeff MacDonald]
| Fix left border to use ' {vline} ' with adjusted contentwidth
| 
* eb4ca59 2026-02-23 Set normalcolor and cic in demo for highlighting [Jeff MacDonald]
| Set normalcolor and cic in demo for highlighting
| 
* f0474f8 2026-02-23 Highlight current item after displaying box [Jeff MacDonald]
| Highlight current item after displaying box
| 
* 9bf79d7 2026-02-23 Remove extra echo() call that was adding blank lines [Jeff MacDonald]
| Remove extra echo() call that was adding blank lines
| 
* f96a5a6 2026-02-23 Revert to contentwidth-3 for content area [Jeff MacDonald]
| Revert to contentwidth-3 for content area
| 
* 3de8a3d 2026-02-23 Fix content area width: contentwidth-1 [Jeff MacDonald]
| Fix content area width: contentwidth-1
| 
* 80d03e6 2026-02-23 Title box is 4 lines, middle border connects to content [Jeff MacDonald]
| Title box is 4 lines, middle border connects to content
| 
* bb02eee 2026-02-23 Fix title box bottom to use corners instead of tees [Jeff MacDonald]
| Fix title box bottom to use corners instead of tees
| 
* d1f9ee2 2026-02-23 Fix middle border: rtee on left, ltee on right [Jeff MacDonald]
| Fix middle border: rtee on left, ltee on right
| 
* c21049e 2026-02-23 Fix contentwidth-2 for inner content alignment [Jeff MacDonald]
| Fix contentwidth-2 for inner content alignment
| 
* 8511968 2026-02-23 Fix hline width: contentwidth - 2 instead of +4 [Jeff MacDonald]
| Fix hline width: contentwidth - 2 instead of +4
| 
* b6a836f 2026-02-23 Update spec: leading space instead of trailing in border definitions [Jeff MacDonald]
| Update spec: leading space instead of trailing in border definitions
| 
* 51d9556 2026-02-23 Change trailing space to leading space in border functions [Jeff MacDonald]
| Change trailing space to leading space in border functions
| 
* 632f630 2026-02-23 Update spec: add hline to constructor, fix contentwidth-3 [Jeff MacDonald]
| Update spec: add hline to constructor, fix contentwidth-3
| 
* ea1220d 2026-02-23 Fix contentwidth in _display_item, move hline to constructor [Jeff MacDonald]
| Fix contentwidth in _display_item, move hline to constructor
| 
* 77dd655 2026-02-23 Add _display_top_border, update spec with border functions [Jeff MacDonald]
| Add _display_top_border, update spec with border functions
| 
* a9d9cc1 2026-02-23 Rename _display_content_top to _display_middle_border [Jeff MacDonald]
| Rename _display_content_top to _display_middle_border
| 
* 3729551 2026-02-23 Rename _display_content_bottom to _display_bottom_border [Jeff MacDonald]
| Rename _display_content_bottom to _display_bottom_border
| 
* 2e91deb 2026-02-23 Update spec Height Calculation with f-string border definitions [Jeff MacDonald]
| Update spec Height Calculation with f-string border definitions
| 
* e5b8a44 2026-02-23 Fix echo calls - remove end='' for display, keep for bell [Jeff MacDonald]
| Fix echo calls - remove end='' for display, keep for bell
| 
* 633c0d5 2026-02-23 Add demo_listbox_next_static demo [Jeff MacDonald]
| Add demo_listbox_next_static demo
| 
* 3284138 2026-02-23 Implement listbox_next module from spec [Jeff MacDonald]
| Implement listbox_next module from spec
| 
* 9a88713 2026-02-23 Add onkey method to Listbox class, move all key handling into it [Jeff MacDonald]
| Add onkey method to Listbox class, move all key handling into it
| 
* 451327e 2026-02-22 Reorder ListboxResult with status first, item defaults to None [Jeff MacDonald]
| Reorder ListboxResult with status first, item defaults to None
| 
* 67b9985 2026-02-22 Add ListboxResult NamedTuple for structured return values [Jeff MacDonald]
| Add ListboxResult NamedTuple for structured return values
| 
* 750db5d 2026-02-22 Use echo_command syntax for savecursor/restorecursor [Jeff MacDonald]
| Use echo_command syntax for savecursor/restorecursor
| 
* a4847ab 2026-02-22 Add savecursor after prompt, restorecursor on item selection [Jeff MacDonald]
| Add savecursor after prompt, restorecursor on item selection
| 
* 0df1aea 2026-02-22 Rename cic dict to itemcolors [Jeff MacDonald]
| Rename cic dict to itemcolors
| 
* e44bbcd 2026-02-22 Add io.setvar() calls for cic echovar [Jeff MacDonald]
| Add io.setvar() calls for cic echovar
| 
* 153d1e5 2026-02-22 Document cic as a dict for item color states [Jeff MacDonald]
| Document cic as a dict for item color states
| 
* b16c94a 2026-02-22 Use 'enabled' instead of 'non-disabled' throughout [Jeff MacDonald]
| Use 'enabled' instead of 'non-disabled' throughout
| 
* f390d2c 2026-02-22 Use 'enabled' instead of 'non-disabled' in KEY_END [Jeff MacDonald]
| Use 'enabled' instead of 'non-disabled' in KEY_END
| 
* de5d8ec 2026-02-22 Add cic echovar for current item color [Jeff MacDonald]
| Add cic echovar for current item color
| 
* 8ec7bec 2026-02-22 Add listbox_next widget specification [Jeff MacDonald]
| Add listbox_next widget specification
| 
* bfe1b3f 2026-02-22 listbox: add compose() method and multi-line support [Jeff MacDonald]
| listbox: add compose() method and multi-line support
| 
| - Add WIDTH_OVERHEAD constant (9) to ListboxItem
| - Add compose() classmethod to transform records to display data
| - Support multi-line items by splitting on \n in display()
| - Counter starts at 0, pk defaults to counter value
| - Remove height parameter from Listbox constructor
| - Rename demos to demo_listbox_static and demo_listbox_database
| 
* 1b1f3ac 2026-02-21 Sync spec with asimov.io: add register_emojis section and unicode codepoints [Jeff MacDonald]
| Sync spec with asimov.io: add register_emojis section and unicode codepoints
| 
* 5091cb6 2026-02-21 Sync emoji comments with asimov.io format [Jeff MacDonald]
| Sync emoji comments with asimov.io format
| 
| Add emoji glyphs and @since comments to all emojis,
| matching asimov.io format. Remove old @see comments.
| 
* 04be0de 2026-02-21 Add register_emojis, move empyre emojis to project [Jeff MacDonald]
| Add register_emojis, move empyre emojis to project
| 
| - Add register_emoji/register_emojis functions
| - Remove empyre-only emojis (dragon, tree, wood, cityscape, desert, farmer) from core
| - Update mm emojis to say 'for murdermotel' (bellhop-bell, hotel, mousetrap, axe)
| - Add maint emoji with 'for empyre, murdermotel' comment
| - Update spec with register_emojis example
| 
* 5f30f93 2026-02-21 Mark emoji table as sample in echo_commands.spec [Jeff MacDonald]
| Mark emoji table as sample in echo_commands.spec
| 
* 9106663 2026-02-21 Implement literal braces {{ and }} in bbsengine6.io.echo [Jeff MacDonald]
| Implement literal braces {{ and }} in bbsengine6.io.echo
| 
| Add tokenizer support for {{ and }} to output literal brace characters
| without triggering command parsing. Update spec with dedicated section.
| 
* 74f0d02 2026-02-19 io: add type annotations to input functions (tag: v202602211051) [Jeff MacDonald]
| io: add type annotations to input functions
| 
| - inputstring: positional-only args /, oldvalue:str, etc.
| - getch: timeout:float, debug:bool
| - inputinteger: return int|list|None
| - inputchoice: default:str|None
| - inputboolean: default:str|None
| 
* 1fdcc6e 2026-02-19 io: sync spec files from asimov [Jeff MacDonald]
| io: sync spec files from asimov
| 
* 92eb250 2026-02-19 build: disable gitlab push in release target [Jeff MacDonald]
| build: disable gitlab push in release target
| 
* a51e7bc 2026-02-19 io: update inputstring and core modules from asimov (tag: v202602192015) [Jeff MacDonald]
| io: update inputstring and core modules from asimov
| 
| - inputstring.py:
|   - Add Completer class for stateful completion
|   - Support **kwargs passed to inputstring() -> completer()
|   - Fix scrolling issues when printing completion matches
|   - Enforce positional-only args for prompt and oldvalue
|   - Rename oldString back to oldvalue for compatibility
| - getch.py: Add KEY_TAB mapping
| - echo.py: Minor cleanup and color fix
| - screen.py: Fix imports
| - util.py: Update logger name default to 'asimov'
| - common.py: Update imports
| 
* 5c6f934 2026-02-19 bbsengine6/io: refactored getch, added getstr, updated common/echo/inputstring/util [Jeff MacDonald]
| bbsengine6/io: refactored getch, added getstr, updated common/echo/inputstring/util
| 
* c8a78f3 2026-02-13 - bbsengine6/io/screen.py: fixed a bug in init() regarding the 'args' argument and a default value [Jeff MacDonald]
| - bbsengine6/io/screen.py: fixed a bug in init() regarding the 'args' argument and a default value
| 
* 7643a65 2026-01-08 - bbsengine6/sql: renamed sigview to folderview [Jeff MacDonald]
| - bbsengine6/sql: renamed sigview to folderview
| 
* cb1de2c 2025-12-24 - bbsengine6: renamed sig.sql to folder.sql [Jeff MacDonald]
| - bbsengine6: renamed sig.sql to folder.sql
| 
* e7625ff 2025-12-24 - bbsengine6: added php/bootstrap.php [Jeff MacDonald]
| - bbsengine6: added php/bootstrap.php
| 
* 5b33036 2025-12-14 - bbsengine6/io/screen.py: copied from asimov/io/ [Jeff MacDonald]
| - bbsengine6/io/screen.py: copied from asimov/io/
| 
* 6183f21 2025-12-14 - bbsengine6/io/echo.py:   * fixed cuu, cud, cuf, cub ('repeat' was being handled wrong)   * added start of literalopen/close handling. does not work yet.   * added 'settitle' echo command   * changed tokenize() to accept **kwargs   * changed terminal_state to a single instance instead of a list   * decsc and decrc update internal vars   * added 'level' as kwarg to echo(). calls common.logentry(). sets up a prefix which uses echo vars level.info, level.debug, etc   * added rendered_length() which is used by inputstring() for displaying the prompt and positioning the cursor correctly. [Jeff MacDonald]
| - bbsengine6/io/echo.py:
|   * fixed cuu, cud, cuf, cub ('repeat' was being handled wrong)
|   * added start of literalopen/close handling. does not work yet.
|   * added 'settitle' echo command
|   * changed tokenize() to accept **kwargs
|   * changed terminal_state to a single instance instead of a list
|   * decsc and decrc update internal vars
|   * added 'level' as kwarg to echo(). calls common.logentry(). sets up a prefix which uses echo vars level.info, level.debug, etc
|   * added rendered_length() which is used by inputstring() for displaying the prompt and positioning the cursor correctly.
| 
* 038290d 2025-12-14 - bbsengine6/io/inputstring.py:   * added/removed/updated comments   * if trying to move left when curpos is 0, ring the bell.   * if trying to move right when curpos is at the end of buffer, ring the bell   * yank has been written but not tested   * if verify() fails, call refresh_input_view()   * updated handle_tab_manager()   * added oldvalue as 2nd positional arg of inputstring() [Jeff MacDonald]
| - bbsengine6/io/inputstring.py:
|   * added/removed/updated comments
|   * if trying to move left when curpos is 0, ring the bell.
|   * if trying to move right when curpos is at the end of buffer, ring the bell
|   * yank has been written but not tested
|   * if verify() fails, call refresh_input_view()
|   * updated handle_tab_manager()
|   * added oldvalue as 2nd positional arg of inputstring()
| 
* 51d718e 2025-12-14 - bbsengine6/io/terminal.py:   * added size(), columns(), and lines()   * height and width are now aliases   * commented out title() (it is now an echo command, and commenting this out fixed a circular ref with .echo)   * removed savecursor() [Jeff MacDonald]
| - bbsengine6/io/terminal.py:
|   * added size(), columns(), and lines()
|   * height and width are now aliases
|   * commented out title() (it is now an echo command, and commenting this out fixed a circular ref with .echo)
|   * removed savecursor()
| 
* 7530775 2025-12-14 - bbsengine6/io/inputinteger.py: cast oldvalue to str [Jeff MacDonald]
| - bbsengine6/io/inputinteger.py: cast oldvalue to str
| 
* 0f57894 2025-12-14 - bbsengine6/io/getch.py: added **kwargs for future use [Jeff MacDonald]
| - bbsengine6/io/getch.py: added **kwargs for future use
| 
* 3681511 2025-12-14 - bbsengine6/io/const.py: added OSC (terminal title, amongst other functions), MAX_TERMINAL_WIDTH, and FALLBACK_TERMINAL_WIDTH [Jeff MacDonald]
| - bbsengine6/io/const.py: added OSC (terminal title, amongst other functions), MAX_TERMINAL_WIDTH, and FALLBACK_TERMINAL_WIDTH
| 
* bca3395 2025-12-14 - bbsengine6/io/common.py: moved terminal_size(), terminal_columns(), and terminal_lines() into io/screen.py [Jeff MacDonald]
| - bbsengine6/io/common.py: moved terminal_size(), terminal_columns(), and terminal_lines() into io/screen.py
| 
* e1c7baf 2025-12-14 - bbsengine6/io/__init__.py: split the input functions and their support into separate files [Jeff MacDonald]
| - bbsengine6/io/__init__.py: split the input functions and their support into separate files
| 
* f7a4808 2025-12-07 - bbsengine6/io/inputboolean.py: import echo() [Jeff MacDonald]
| - bbsengine6/io/inputboolean.py: import echo()
| 
* 50d87e0 2025-12-07 - bbsengine6/io/inputchoice.py: import echo() and getch() [Jeff MacDonald]
| - bbsengine6/io/inputchoice.py: import echo() and getch()
| 
* d4f8c26 2025-12-07 - bbsengine6/io/__init__.py: import of getch() and commented out import of 'input' [Jeff MacDonald]
| - bbsengine6/io/__init__.py: import of getch() and commented out import of 'input'
| 
* 8bff9ca 2025-12-07 - bbsengine6/io/getch.py: removed an extra blank line [Jeff MacDonald]
| - bbsengine6/io/getch.py: removed an extra blank line
| 
* 8f9e437 2025-12-07 - bbsengine6/io/: sync with asimov/io/ [Jeff MacDonald]
| - bbsengine6/io/: sync with asimov/io/
| 
* 8003e3f 2025-12-05 - bbsengine6/common.py: fixed logentry() to behave better if a logging level is not in the table: use logging.NOTSET [Jeff MacDonald]
| - bbsengine6/common.py: fixed logentry() to behave better if a logging level is not in the table: use logging.NOTSET
| 
* a80f101 2025-12-03 - bbsengine6/io/echo.py:   * fixed a 'repeat bug' in cuu, cuf   * updated _handle_decstbm so it is properly 1-based   * fixed the 'reset top and bottom margins' feature   * fixed _handle_bel() typo (BEL vs BELL)   * fixed reset:all by clearing token.args   * {decstbm:1,1} can be shortened to {decstbm} (reset margins) [Jeff MacDonald]
| - bbsengine6/io/echo.py:
|   * fixed a 'repeat bug' in cuu, cuf
|   * updated _handle_decstbm so it is properly 1-based
|   * fixed the 'reset top and bottom margins' feature
|   * fixed _handle_bel() typo (BEL vs BELL)
|   * fixed reset:all by clearing token.args
|   * {decstbm:1,1} can be shortened to {decstbm} (reset margins)
| 
* 5f34923 2025-12-03 - bbsengine6/io/: split up each function in input.py into their own files, updated __init__ to match. [Jeff MacDonald]
| - bbsengine6/io/: split up each function in input.py into their own files, updated __init__ to match.
| 
* 2e4468d 2025-12-03 - bbsengine6/io/inputstring.py: fixed up whitespace issues [Jeff MacDonald]
| - bbsengine6/io/inputstring.py: fixed up whitespace issues
| 
* 03220e6 2025-12-02 - bbsengine6/session.py: if no conn, check for a pool [Jeff MacDonald]
| - bbsengine6/session.py: if no conn, check for a pool
| 
* f8078c2 2025-12-02 - bbsengine6/io/keymap.py: copied from asimov/io/ [Jeff MacDonald]
| - bbsengine6/io/keymap.py: copied from asimov/io/
| 
* 2a6e5a1 2025-12-02 - bbsengine6/io/input.py: updated 'curdisplay' to use cha instead of cursorhpos [Jeff MacDonald]
| - bbsengine6/io/input.py: updated 'curdisplay' to use cha instead of cursorhpos
| 
* 63d91d3 2025-12-02 - bbsengine6/io/__init__.py: updated to use asimov's inputstring and echo [Jeff MacDonald]
| - bbsengine6/io/__init__.py: updated to use asimov's inputstring and echo
| 
* fa2e190 2025-12-02 - bbsengine6/io/echo.py: changed 'bottombarcolor' and commented out a few print() calls [Jeff MacDonald]
| - bbsengine6/io/echo.py: changed 'bottombarcolor' and commented out a few print() calls
| 
* 9cf05cc 2025-12-02 - added inputstring and util from asimov/io/ [Jeff MacDonald]
| - added inputstring and util from asimov/io/
| 
* 55e71ce 2025-12-02 - bbsengine6/io/getch.py: copied from asimov/io/ [Jeff MacDonald]
| - bbsengine6/io/getch.py: copied from asimov/io/
| 
* 4a7f721 2025-11-30 no changes? [Jeff MacDonald]
| no changes?
| 
* 3cf5ff5 2025-11-30 - copied asimov.io.common to bbsengine6 [Jeff MacDonald]
| - copied asimov.io.common to bbsengine6
| 
* 831ef22 2025-11-30 - bbsengine6/smarty/: added function.teos, modifier.markdown, and modifier.wpprop [Jeff MacDonald]
| - bbsengine6/smarty/: added function.teos, modifier.markdown, and modifier.wpprop
| 
* 0810b17 2025-11-29 - copied some bits of asimov.io into bbsengine6 (echo) [Jeff MacDonald]
| - copied some bits of asimov.io into bbsengine6 (echo)
| 
* 1196619 2025-11-29 - bbsengine6/module.py: reworked by adding _check_params() helper and a 'for' loop to validate function signatures. added optional version() function in modules [Jeff MacDonald]
| - bbsengine6/module.py: reworked by adding _check_params() helper and a 'for' loop to validate function signatures. added optional version() function in modules
| 
* 6bcdc21 2025-10-29 updated README.md [Jeff MacDonald]
| updated README.md
| 
* e57e852 2025-10-29 - updated [Jeff MacDonald]
| - updated
| 
* ebbe8d5 2025-10-29 - updated [Jeff MacDonald]
| - updated
| 
* 56f9170 2025-10-29 - updated [Jeff MacDonald]
| - updated
| 
* ebc1445 2025-10-29 updated README.md [Jeff MacDonald]
| updated README.md
| 
* 8af11e5 2025-10-29 removed README.md [Jeff MacDonald]
| removed README.md
| 
* bc3632f 2025-10-28 - bbsengine6/listbox.py:   * default of this version is to use a database cursor (fetchpage)   * added some debugging using the bottombar   * added a typehint on 'prompt' arg to Listbox.handle() [Jeff MacDonald]
| - bbsengine6/listbox.py:
|   * default of this version is to use a database cursor (fetchpage)
|   * added some debugging using the bottombar
|   * added a typehint on 'prompt' arg to Listbox.handle()
| 
* e06fc5b 2025-10-08 - bbsengine6/database.py: rewrite connect() [Jeff MacDonald]
| - bbsengine6/database.py: rewrite connect()
| 
* bc699a4 2025-10-08 - bbsengine6/sql/:   * grant changes   * fixed whitespace issues [Jeff MacDonald]
| - bbsengine6/sql/:
|   * grant changes
|   * fixed whitespace issues
| 
* 185be72 2025-10-07 - bbsengine6/util.py: copied logentry() from asimov [Jeff MacDonald]
| - bbsengine6/util.py: copied logentry() from asimov
| 
* a0863ca 2025-10-06 - bbsengine6/util.py: add **kwargs to getcurrentloginid() [Jeff MacDonald]
| - bbsengine6/util.py: add **kwargs to getcurrentloginid()
| 
* 22a9e3d 2025-05-30 - bbsengine6/console/checkclasses.py: updated call to database.importsql() (tag: v202505302019) [Jeff MacDonald]
| - bbsengine6/console/checkclasses.py: updated call to database.importsql()
| 
* b6fda4e 2025-05-28 - bbsengine6/util.py:   * added strip_ansi() to help with wide character support   * serialize_datetimes() - steps through a nested dict called 'data' and converts any datetimes it finds to isoformat (str)   * load_sql() - Loads an SQL resource file and returns its contents as a string   * get_safe_path() - safely joins and normalizes path components   * getcurrentloginid() - returns system login id using os.getlogin() (tag: v202505302017, tag: v202505301857, tag: v202505301855, tag: v202505281954) [Jeff MacDonald]
| - bbsengine6/util.py:
|   * added strip_ansi() to help with wide character support
|   * serialize_datetimes() - steps through a nested dict called 'data' and converts any datetimes it finds to isoformat (str)
|   * load_sql() - Loads an SQL resource file and returns its contents as a string
|   * get_safe_path() - safely joins and normalizes path components
|   * getcurrentloginid() - returns system login id using os.getlogin()
| 
* d6074f0 2025-05-28 - bbsengine6/module.py: be sure to pass kwargs to access() [Jeff MacDonald]
| - bbsengine6/module.py: be sure to pass kwargs to access()
| 
* 932ac86 2025-05-28 - bbsengine6/sql/: added manage_database_priv.sql and manage_schema_priv.sql [Jeff MacDonald]
| - bbsengine6/sql/: added manage_database_priv.sql and manage_schema_priv.sql
| 
* 30f3394 2025-05-28 - bbsengine6/Makefile: added 'sql' and 'console' to 'clean' target [Jeff MacDonald]
| - bbsengine6/Makefile: added 'sql' and 'console' to 'clean' target
| 
* 6be5fc9 2025-05-27 - bbsengine6/io/output.py: added strip_commands() for use by setbottombar() (tag: v202505281805, tag: v202505281759, tag: v202505281752, tag: v202505281732) [Jeff MacDonald]
| - bbsengine6/io/output.py: added strip_commands() for use by setbottombar()
| 
* 8b81d8c 2025-05-27 - bbsengine6/screen.py: setbottombar() rewrite [Jeff MacDonald]
| - bbsengine6/screen.py: setbottombar() rewrite
| 
* bd6b3d6 2025-05-27 - bbsengine6/io/output.py: attempting to fix spurious \n while typing fast in getchinputstring(); failed patch attempting to handle emojis (wide characters) [Jeff MacDonald]
| - bbsengine6/io/output.py: attempting to fix spurious \n while typing fast in getchinputstring(); failed patch attempting to handle emojis (wide characters)
| 
* 10c16d4 2025-05-27 - bbsengine6/io/input.py: changed display() to not repaint prompt+buffer unless it is different; tweaked some getch() timings [Jeff MacDonald]
| - bbsengine6/io/input.py: changed display() to not repaint prompt+buffer unless it is different; tweaked some getch() timings
| 
* f995831 2025-05-23 - bbsengine6/module.py: pass **kwargs to module's access(); check 'silent' kwarg before certain output in check() [Jeff MacDonald]
| - bbsengine6/module.py: pass **kwargs to module's access(); check 'silent' kwarg before certain output in check()
| 
* dd7cfa7 2025-05-15 - bbsengine6/io/input.py: commented out debugging in inputchoice() [Jeff MacDonald]
| - bbsengine6/io/input.py: commented out debugging in inputchoice()
| 
* 4766782 2025-05-14 - bbsengine6/io/input.py: fixed special handling of ^U in getch() which fixed a glitch in inputstring(); updated inputchoice() with a new kwarg 'rewriteprompt' which colorizes the prompt in the de facto way, plus puts parens around the default option; **kw -> **kwargs; [Jeff MacDonald]
| - bbsengine6/io/input.py: fixed special handling of ^U in getch() which fixed a glitch in inputstring(); updated inputchoice() with a new kwarg 'rewriteprompt' which colorizes the prompt in the de facto way, plus puts parens around the default option; **kw -> **kwargs;
| 
* 952a36f 2025-05-13 - bbsengin6/io/output.py: added letter prefixes in echo()'s 'level' for terminals without color [Jeff MacDonald]
| - bbsengin6/io/output.py: added letter prefixes in echo()'s 'level' for terminals without color
| 
* f96629f 2025-05-10 - bbsengine6/console/checkroles.py: fixed indentation mistake that only created one role; changed buildargs() to return None [Jeff MacDonald]
| - bbsengine6/console/checkroles.py: fixed indentation mistake that only created one role; changed buildargs() to return None
| 
* a1bc5a9 2025-04-20 - bbsengine6/sql/__init__.py: removed-- using MANIFEST.in instead (tag: v202504202158) [Jeff MacDonald]
| - bbsengine6/sql/__init__.py: removed-- using MANIFEST.in instead
| 
* 7a31dc1 2025-04-20 - bbsengine6/MANIFEST.in: added [Jeff MacDonald]
| - bbsengine6/MANIFEST.in: added
| 
* c981bca 2025-04-20 - bbsengine6/sql/: added __init__.py [Jeff MacDonald]
| - bbsengine6/sql/: added __init__.py
| 
* 131c5b4 2025-04-20 - bbsengine6/setup.py: commented out 'py_modules' [Jeff MacDonald]
| - bbsengine6/setup.py: commented out 'py_modules'
| 
* 716a73f 2025-04-20 - bbsengine6/setup.py: updated 'provides', 'packages', and 'classifiers' [Jeff MacDonald]
| - bbsengine6/setup.py: updated 'provides', 'packages', and 'classifiers'
| 
* 3069c34 2025-04-20 - moved 'sql' under bbsengine6 python package [Jeff MacDonald]
| - moved 'sql' under bbsengine6 python package
| 
* 34fc32d 2025-04-20 - bbsengine6/sql/upgrades.md: added [Jeff MacDonald]
| - bbsengine6/sql/upgrades.md: added
| 
* e016e2c 2025-04-20 - bbsengine6/io/input.py getch():   * rewrote code that handles ESC sequences (arrow keys, home, end, function keys, etc) which uses a while loop with a timeout instead of a for loop that reads up to five characters   * prevent busy wait by gradually increasing the time.sleep() at the bottom of the while loop starting at BASESLEEP increasing by 2% up to MAXSLEEP (phil)   * handle BSD (apple) non-blocking read failure gracefully [Jeff MacDonald]
| - bbsengine6/io/input.py getch():
|   * rewrote code that handles ESC sequences (arrow keys, home, end, function keys, etc) which uses a while loop with a timeout instead of a for loop that reads up to five characters
|   * prevent busy wait by gradually increasing the time.sleep() at the bottom of the while loop starting at BASESLEEP increasing by 2% up to MAXSLEEP (phil)
|   * handle BSD (apple) non-blocking read failure gracefully
| 
* 85ab95b 2025-04-20 - bbsengine6/sql/bbsengine6.sql:   * removed \sets for web, term, sysop   * added ltree, roles, tag, memberinet   * notify -> alert [Jeff MacDonald]
| - bbsengine6/sql/bbsengine6.sql:
|   * removed \sets for web, term, sysop
|   * added ltree, roles, tag, memberinet
|   * notify -> alert
| 
* 1229cfc 2025-04-20 - bbsengine6/sql/fortune.sql: engine.blurb -> engine.__blurb [Jeff MacDonald]
| - bbsengine6/sql/fortune.sql: engine.blurb -> engine.__blurb
| 
* a8ef5f1 2025-04-19 - bbsengine6/sql/sigview.sql: added [Jeff MacDonald]
| - bbsengine6/sql/sigview.sql: added
| 
* 7e312d8 2025-04-19 - bbsengine6/sql/map_member_flag.sql: added [Jeff MacDonald]
| - bbsengine6/sql/map_member_flag.sql: added
| 
* 44ad7fa 2025-04-19 - bbsengine6/sql/blurbview.sql: added index, left joins renamed to be clearer; untested [Jeff MacDonald]
| - bbsengine6/sql/blurbview.sql: added index, left joins renamed to be clearer; untested
| 
* d048657 2025-04-19 - bbsengine6/sql/map_group_member.sql: id -> moniker; added index [Jeff MacDonald]
| - bbsengine6/sql/map_group_member.sql: id -> moniker; added index
| 
* 519a4e7 2025-04-19 - bbsengine6/sql/role.sql: removed [Jeff MacDonald]
| - bbsengine6/sql/role.sql: removed
| 
* 7e57d03 2025-04-19 - bbsengine6/sql/map_sigop_sigpath.sql: added unique index [Jeff MacDonald]
| - bbsengine6/sql/map_sigop_sigpath.sql: added unique index
| 
* 3bff07d 2025-04-19 - bbsengine6/sql/blocklist.sql: add 'unique' to 'address'; id->moniker [Jeff MacDonald]
| - bbsengine6/sql/blocklist.sql: add 'unique' to 'address'; id->moniker
| 
* 3f5b0cb 2025-04-19 - bbsengine6/sql/memberinet.sql: text -> citext [Jeff MacDonald]
| - bbsengine6/sql/memberinet.sql: text -> citext
| 
* f4dc4ee 2025-04-19 - bbsengine6/sql/moderator.sql: text -> citext [Jeff MacDonald]
| - bbsengine6/sql/moderator.sql: text -> citext
| 
* 23bf540 2025-04-19 - bbsengine6/sql/moderator.sql: add an index (membermoniker, sigpath) id->moniker [Jeff MacDonald]
| - bbsengine6/sql/moderator.sql: add an index (membermoniker, sigpath) id->moniker
| 
* 1d6efd8 2025-04-19 - bbsengine6/sql/blurb.sql: :web -> web, etc; text -> citext [Jeff MacDonald]
| - bbsengine6/sql/blurb.sql: :web -> web, etc; text -> citext
| 
* bf8a9dc 2025-04-19 - bbsengine6/sql/extensions.sql: handled by bbsengine6.console [Jeff MacDonald]
| - bbsengine6/sql/extensions.sql: handled by bbsengine6.console
| 
* 7fba876 2025-04-19 - bbsengine6/sql/alert.sql: text -> citext, add a trigger to __alert [Jeff MacDonald]
| - bbsengine6/sql/alert.sql: text -> citext, add a trigger to __alert
| 
* 32cfd9c 2025-04-19 - bbsengine6/sql/checkflag.sql: if membermoniker is not null, return flag values. if membermoniker does not exist, return null [Jeff MacDonald]
| - bbsengine6/sql/checkflag.sql: if membermoniker is not null, return flag values. if membermoniker does not exist, return null
| 
* 86d96dc 2025-04-19 - bbsengine6/sql/memberview.sql: added local time to dateapproved, dateupdated, datecreated, lastlogin [Jeff MacDonald]
| - bbsengine6/sql/memberview.sql: added local time to dateapproved, dateupdated, datecreated, lastlogin
| 
* a72652e 2025-04-19 - bbsengine6/sql/flagdata.sql: commented out echo [Jeff MacDonald]
| - bbsengine6/sql/flagdata.sql: commented out echo
| 
* b60be75 2025-04-19 - bbsengine6/sql/flag.sql: text -> citext; commented out engine.map_blurb_flag; permissions [Jeff MacDonald]
| - bbsengine6/sql/flag.sql: text -> citext; commented out engine.map_blurb_flag; permissions
| 
* b40ca86 2025-04-19 - bbsengine6/sql/manage_secondary_role.sql: add -> grant, remove -> revoke, add execute permission to sysop [Jeff MacDonald]
| - bbsengine6/sql/manage_secondary_role.sql: add -> grant, remove -> revoke, add execute permission to sysop
| 
* 017a29b 2025-04-19 - bbsengine6/sql/manage_role_privs.sql: updated permissions [Jeff MacDonald]
| - bbsengine6/sql/manage_role_privs.sql: updated permissions
| 
* e223401 2025-04-19 - bbsengine6/sql/newuser.sql: no longer used [Jeff MacDonald]
| - bbsengine6/sql/newuser.sql: no longer used
| 
* 38b4451 2025-04-19 - bbsengine6/sql/notify.sql: deleted [Jeff MacDonald]
| - bbsengine6/sql/notify.sql: deleted
| 
* 0f1f3c2 2025-04-19 - bbsengine6/sql/roles.sql: commented out. this is done by firstboot [Jeff MacDonald]
| - bbsengine6/sql/roles.sql: commented out. this is done by firstboot
| 
* 0bf5adb 2025-04-19 - con -> bbsengine6/console [Jeff MacDonald]
| - con -> bbsengine6/console
| 
* 6b91536 2025-04-18 - bbsengine6/sql/: added createrol.sql createschema.sql get_role_privs.sql getflags.sql grants.sql ltree.sql [Jeff MacDonald]
| - bbsengine6/sql/: added createrol.sql createschema.sql get_role_privs.sql getflags.sql grants.sql ltree.sql
| 
* 17b501a 2025-04-18 - bbsengine6/sql/member.sql: memberid->membermoniker, added ui, tz, attrs, and refcode [Jeff MacDonald]
| - bbsengine6/sql/member.sql: memberid->membermoniker, added ui, tz, attrs, and refcode
| 
* 3ad16cd 2025-04-18 - bbsengine6/sql/actionlog.sql: renamed activitylog to actionlog [Jeff MacDonald]
| - bbsengine6/sql/actionlog.sql: renamed activitylog to actionlog
| 
* fa915f1 2025-04-18 - bbsengine6/sql/schema.sql: grant usage to web, term, sysop [Jeff MacDonald]
| - bbsengine6/sql/schema.sql: grant usage to web, term, sysop
| 
* de773fb 2025-04-18 - bbsengine6/sql/session.sql: added lastactivitylocal and expirylocal and memberid->membermoniker [Jeff MacDonald]
| - bbsengine6/sql/session.sql: added lastactivitylocal and expirylocal and memberid->membermoniker
| 
* c9a0183 2025-04-18 - bbsengine6/sql/refcode.sql: s/text/citext/ [Jeff MacDonald]
| - bbsengine6/sql/refcode.sql: s/text/citext/
| 
* f223f0c 2025-04-17 - bbsengine6/sql/buildsiguri.sql: rewrote from pl/pythonu to pl/pgsql [Jeff MacDonald]
| - bbsengine6/sql/buildsiguri.sql: rewrote from pl/pythonu to pl/pgsql
| 
* 54a5e6d 2025-04-17 - bbsengine6/sql/subscribe.sql: s/memberid/membermoniker/ [Jeff MacDonald]
| - bbsengine6/sql/subscribe.sql: s/memberid/membermoniker/
| 
* 8bf67e9 2025-04-17 - bbsengine6/sql/sig.sql: updatedby, approvedby, createdby are now citext instead of bigint [Jeff MacDonald]
| - bbsengine6/sql/sig.sql: updatedby, approvedby, createdby are now citext instead of bigint
| 
* 0633acc 2025-04-15 - bbsengine6/con/createdatabase.py: added [Jeff MacDonald]
| - bbsengine6/con/createdatabase.py: added
| 
* 5f753ac 2025-04-15 - bbsengine6/con/main.py:   * 3 stages: stage_zero, stage_one, and the rest of main [Jeff MacDonald]
| - bbsengine6/con/main.py:
|   * 3 stages: stage_zero, stage_one, and the rest of main
| 
* 9ac1204 2025-04-15 - bbsengine6/con/lib.py: added check*() functions [Jeff MacDonald]
| - bbsengine6/con/lib.py: added check*() functions
| 
* 1f34103 2025-04-15 - bbsengine6/con/__main__.py: use io.echo() instead of print() [Jeff MacDonald]
| - bbsengine6/con/__main__.py: use io.echo() instead of print()
| 
* f964b40 2025-04-15 - bbsengine6/con/member.py:   * kw -> kwargs   * pass kwargs to database functions   * setui() now accepts kwargs   * configurerole() works now   * add and edit of accounts works now [Jeff MacDonald]
| - bbsengine6/con/member.py:
|   * kw -> kwargs
|   * pass kwargs to database functions
|   * setui() now accepts kwargs
|   * configurerole() works now
|   * add and edit of accounts works now
| 
* 8426738 2025-04-15 - bbsengine6/session.py:   * add '**kwargs' to all functions   * session.start() now has a _work(), and the function can make a database connection if it was passed a pool (standard)   * added garbagecollect() [Jeff MacDonald]
| - bbsengine6/session.py:
|   * add '**kwargs' to all functions
|   * session.start() now has a _work(), and the function can make a database connection if it was passed a pool (standard)
|   * added garbagecollect()
| 
* bedf2db 2025-03-17 - bbsengine6/io/output.py:   * in echo()'s level handling, remove 'var:' ahead of var names   * renamed vars.py to echovars.py   * set_terminal_background_color() and reset_terminal_background_color() [Jeff MacDonald]
| - bbsengine6/io/output.py:
|   * in echo()'s level handling, remove 'var:' ahead of var names
|   * renamed vars.py to echovars.py
|   * set_terminal_background_color() and reset_terminal_background_color()
| 
* 8fb077c 2025-03-17 - bbsengine6/io/__init__.py: whitespace? [Jeff MacDonald]
| - bbsengine6/io/__init__.py: whitespace?
| 
* 9401567 2025-03-17 - bbsengine6/io/const.py:   - added 'attributes' table (bold, faint, italic, underline, strike, and blink)   - added a few emojis   - merged 'bgcolors' table into 'colors'   - flattened 'colors' table to be a simple dict   - renamed RGB token to RGBCOLOR, command itself is the same [Jeff MacDonald]
| - bbsengine6/io/const.py:
|   - added 'attributes' table (bold, faint, italic, underline, strike, and blink)
|   - added a few emojis
|   - merged 'bgcolors' table into 'colors'
|   - flattened 'colors' table to be a simple dict
|   - renamed RGB token to RGBCOLOR, command itself is the same
| 
* 924facb 2025-03-17 - bbsengine6/io/input.py: added comments to CTRLKEYSEQ, allow \n or \r (raw mode) to return KEY_ENTER [Jeff MacDonald]
| - bbsengine6/io/input.py: added comments to CTRLKEYSEQ, allow \n or \r (raw mode) to return KEY_ENTER
| 
* 9d3df11 2025-03-17 - bbsengine6/io/echovars.py: added 'level.crit' var [Jeff MacDonald]
| - bbsengine6/io/echovars.py: added 'level.crit' var
| 
* 530be1b 2025-03-17 - bbsengine6/con/check*.py: added [Jeff MacDonald]
| - bbsengine6/con/check*.py: added
| 
* 34f680a 2025-03-17 - con/session.py: **kw -> **kwargs, minor tweaks [Jeff MacDonald]
| - con/session.py: **kw -> **kwargs, minor tweaks
| 
* c51e24d 2025-03-16 - bbsengine6/module.py: added validate_function() to check annotations and return values [Jeff MacDonald]
| - bbsengine6/module.py: added validate_function() to check annotations and return values
| 
* fe5b417 2025-03-16 - bbsengine6/module.py: exception handling around calls to module functions; rename 'module' to 'modulename' [Jeff MacDonald]
| - bbsengine6/module.py: exception handling around calls to module functions; rename 'module' to 'modulename'
| 
* dd68c0d 2025-03-16 - ttyio/input.py: replaced getch() with an AI generated version [Jeff MacDonald]
| - ttyio/input.py: replaced getch() with an AI generated version
| 
* 054c40e 2025-02-19 - bbsengine6/handbook/module.md: added [Jeff MacDonald]
| - bbsengine6/handbook/module.md: added
| 
* 053c5c1 2025-02-19 - bbsengine6/handbook/: copied files from bbsengine5 [Jeff MacDonald]
| - bbsengine6/handbook/: copied files from bbsengine5
| 
* a904b9b 2024-12-03 - bbsengine6/con/checksuperuser.py: added. checks for corret db privs for the current loginid [Jeff MacDonald]
| - bbsengine6/con/checksuperuser.py: added. checks for corret db privs for the current loginid
| 
* c62278d 2024-12-01 - bbsengine6/con/checkextensions.py: added. checks for required extensions and installs them [Jeff MacDonald]
| - bbsengine6/con/checkextensions.py: added. checks for required extensions and installs them
| 
* bed5739 2024-11-26 - bbsengine6/util.py:   * upgraded to use context managed ('with') connections and cursors   * added getremoteaddr(), chop_last_element(), tobool(), ltree_to_path(), checksum()   * checkpassword() moved to member   * uses logging module for logentry() @ty ryan   * changed prototype for pluralize(), but no code changes (default values, type hints) [Jeff MacDonald]
| - bbsengine6/util.py:
|   * upgraded to use context managed ('with') connections and cursors
|   * added getremoteaddr(), chop_last_element(), tobool(), ltree_to_path(), checksum()
|   * checkpassword() moved to member
|   * uses logging module for logentry() @ty ryan
|   * changed prototype for pluralize(), but no code changes (default values, type hints)
| 
* 8654508 2024-11-25 - bbsengine6/screen.py: renamed setarea to setbottombar and converted to use f-strings [Jeff MacDonald]
| - bbsengine6/screen.py: renamed setarea to setbottombar and converted to use f-strings
| 
* 99e7b0f 2024-11-25 - bbsengine6/session.py: upgraded to use context managed connections and cursors (psycopg3) [Jeff MacDonald]
| - bbsengine6/session.py: upgraded to use context managed connections and cursors (psycopg3)
| 
* d7f4f97 2024-11-25 - bbsengine6/__init__.py: import init() from util [Jeff MacDonald]
| - bbsengine6/__init__.py: import init() from util
| 
* 770829c 2024-11-14 - bbsengine6/php/session.php:   * logentry -> \util\logentry   * encodejson -> \util\encodejson   * SYSTEMDSN -> \config\SYSTEMDSN [Jeff MacDonald]
| - bbsengine6/php/session.php:
|   * logentry -> \util\logentry
|   * encodejson -> \util\encodejson
|   * SYSTEMDSN -> \config\SYSTEMDSN
| 
* 7160384 2024-11-14 - bbsengine6/con/memberapproval.py: 'emailverified' and 'approved' flags moved to flags table [Jeff MacDonald]
| - bbsengine6/con/memberapproval.py: 'emailverified' and 'approved' flags moved to flags table
| 
* 923db3e 2024-11-14 - bbsengine6/con/lib.py: remove 'bbs' role [Jeff MacDonald]
| - bbsengine6/con/lib.py: remove 'bbs' role
| 
* b9b8259 2024-11-14 - bbsengine6/con/session.py: @project:9627 - upgrade session submodule database calls and ttyio [Jeff MacDonald]
| - bbsengine6/con/session.py: @project:9627 - upgrade session submodule database calls and ttyio
| 
* d7e975b 2024-11-14 - bbsengine6/con/member.py: if email address changed, clear EMAILVERIFIED flag [Jeff MacDonald]
| - bbsengine6/con/member.py: if email address changed, clear EMAILVERIFIED flag
| 
* 70b6918 2024-11-14 - bbsengine6/php/util.php: @project 9625 add util functions [Jeff MacDonald]
| - bbsengine6/php/util.php: @project 9625 add util functions
| 
* 216b475 2024-11-14 - bbsengine6/php/database.php: upgraded to pdo [Jeff MacDonald]
| - bbsengine6/php/database.php: upgraded to pdo
| 
* 07c4165 2024-11-14 - bbsengine6/sql/: 'grant' changes [Jeff MacDonald]
| - bbsengine6/sql/: 'grant' changes
| 
* fa2f0d4 2024-11-14 - bbsengine6/sql/flagdata.sql: cosmetic changes (MAGIC and ASIMOV) [Jeff MacDonald]
| - bbsengine6/sql/flagdata.sql: cosmetic changes (MAGIC and ASIMOV)
| 
* 1b3d86a 2024-11-01 - bbsengine6/sql/checkflag.sql: moniker and flag_name are now case insensitive; returns true, false, or null [Jeff MacDonald]
| - bbsengine6/sql/checkflag.sql: moniker and flag_name are now case insensitive; returns true, false, or null
| 
* 6314bbb 2024-11-01 - bbsengine6/sql/checkflag.sql: added [Jeff MacDonald]
| - bbsengine6/sql/checkflag.sql: added
| 
* b9c5248 2024-10-31 - bbsengine6/sql/manage_*.sql: @project:9609 add getpool(), cursor(), transaction(), createrol(), get_role_privs(), manage_secondary_role() [Jeff MacDonald]
| - bbsengine6/sql/manage_*.sql: @project:9609 add getpool(), cursor(), transaction(), createrol(), get_role_privs(), manage_secondary_role()
| 
* a9215c9 2024-10-31 - bbsengine6/sql/flagdata.sql: removed 'draft', 'frozen', and 'junk'; added 'approved' and 'emailverified' [Jeff MacDonald]
| - bbsengine6/sql/flagdata.sql: removed 'draft', 'frozen', and 'junk'; added 'approved' and 'emailverified'
| 
* 2ad410b 2024-10-27 - bbsengine6/con/member.py:   * update to bbsengine6 (ttyio -> bbsengine.io)   * added editflags()   * added showui(), editui(), setui()   * added handling of required member fields moniker, loginid, email   * added handling of refcode   * added handling of e-mail address   * added configurerole()   * allow editing of members (not fully tested) [Jeff MacDonald]
| - bbsengine6/con/member.py:
|   * update to bbsengine6 (ttyio -> bbsengine.io)
|   * added editflags()
|   * added showui(), editui(), setui()
|   * added handling of required member fields moniker, loginid, email
|   * added handling of refcode
|   * added handling of e-mail address
|   * added configurerole()
|   * allow editing of members (not fully tested)
| 
* 0cfcdc7 2024-10-27 - bbsengine6/con/member.py and bbsengine6/con/alert.py: added [Jeff MacDonald]
| - bbsengine6/con/member.py and bbsengine6/con/alert.py: added
| 
* a91cb39 2024-10-27 - bbsengine6/database.py:   * @project:9608 implement mogrifysql for psycopg3   * @project:9607 add parse_dsn and make_dsn which are not present in psycopg3   * @project:9609 add getpool(), cursor(), transaction(), createrol(), get_role_privs(), manage_secondary_role() [Jeff MacDonald]
| - bbsengine6/database.py:
|   * @project:9608 implement mogrifysql for psycopg3
|   * @project:9607 add parse_dsn and make_dsn which are not present in psycopg3
|   * @project:9609 add getpool(), cursor(), transaction(), createrol(), get_role_privs(), manage_secondary_role()
| 
* a9208a6 2024-10-27 - bbsengine6/Makefile: added 'io' to clean target [Jeff MacDonald]
| - bbsengine6/Makefile: added 'io' to clean target
| 
* 1e3cbc2 2024-10-27 - bbsengine6/con/main.py:   * renamed 'Quit' to 'Exit'   * added 'A' -- "Member Approval" option   * added call to session.start() and check it for errors and if so, return False   * from bbsengine6 import database [Jeff MacDonald]
| - bbsengine6/con/main.py:
|   * renamed 'Quit' to 'Exit'
|   * added 'A' -- "Member Approval" option
|   * added call to session.start() and check it for errors and if so, return False
|   * from bbsengine6 import database
| 
* e0dc94b 2024-10-27 - bbsengine6/con/lib.py:   * fixed up lib.runmodule()   * changed call to setarea() to setbottombar()   * added checkroles()   * changed buildargs() so it calls database.buildargs() [Jeff MacDonald]
| - bbsengine6/con/lib.py:
|   * fixed up lib.runmodule()
|   * changed call to setarea() to setbottombar()
|   * added checkroles()
|   * changed buildargs() so it calls database.buildargs()
| 
* b0ab120 2024-10-27 - bbsengine6/con/Makefile: added *.pyc to 'clean' target [Jeff MacDonald]
| - bbsengine6/con/Makefile: added *.pyc to 'clean' target
| 
* 06c9a42 2024-10-27 - bbsengine6/con/__init__.py: added __all__ which only helps with 'from con import *' [Jeff MacDonald]
| - bbsengine6/con/__init__.py: added __all__ which only helps with 'from con import *'
| 
* 2664912 2024-10-27 - bbsengine6/con/__main__.py: do not call session.start() [Jeff MacDonald]
| - bbsengine6/con/__main__.py: do not call session.start()
| 
* 30fa902 2024-10-26 - bbsengine6/member.py: removed ' as txn' from database.transaction() calls [Jeff MacDonald]
| - bbsengine6/member.py: removed ' as txn' from database.transaction() calls
| 
* 4d5d3a7 2024-10-26 - bbsengine6/member.py:   * @project:9606 mark some bbsengine.member functions as readonly transactions; add bbsengine.database.transaction()   * in member.getflag() use 'moniker' instead of 'membermoniker' [Jeff MacDonald]
| - bbsengine6/member.py:
|   * @project:9606 mark some bbsengine.member functions as readonly transactions; add bbsengine.database.transaction()
|   * in member.getflag() use 'moniker' instead of 'membermoniker'
| 
* ebcce38 2024-10-26 - bbsengine6/member.py:   * @project:9100 upgrade to psycopg3 (optional asyncio)   * @project:9606 mark some bbsengine6.member functions as readonly   * handle 'ui' field as list, store as comma-separated text [Jeff MacDonald]
| - bbsengine6/member.py:
|   * @project:9100 upgrade to psycopg3 (optional asyncio)
|   * @project:9606 mark some bbsengine6.member functions as readonly
|   * handle 'ui' field as list, store as comma-separated text
| 
* fcae98c 2024-10-14 - bbsengine6/database.py:   * @project 9587: add 'get_role_privs()' and 'manage_role_privs()'   * add 'manage_secondary_role()' [Jeff MacDonald]
| - bbsengine6/database.py:
|   * @project 9587: add 'get_role_privs()' and 'manage_role_privs()'
|   * add 'manage_secondary_role()'
| 
* 71fbe2b 2024-10-14 - bbsengine6: new screenshots of 'con' added [Jeff MacDonald]
| - bbsengine6: new screenshots of 'con' added
| 
* 82c73b8 2024-09-15 - bbsengine6/skin/tmpl/topbar-notifycount.tmpl renamed to topbar-alertcount [Jeff MacDonald]
| - bbsengine6/skin/tmpl/topbar-notifycount.tmpl renamed to topbar-alertcount
| 
* 06df6ab 2024-09-12 - bbsengine6/php/libmember.php: added [Jeff MacDonald]
| - bbsengine6/php/libmember.php: added
| 
* f3b26e2 2024-08-11 - bbsengine6/sql/map_sigop_sigpath.sql: memberid->membermoniker [Jeff MacDonald]
| - bbsengine6/sql/map_sigop_sigpath.sql: memberid->membermoniker
| 
* 67e2edc 2024-07-10 - bbsengine6/io/vars.py -> echovars.py [Jeff MacDonald]
| - bbsengine6/io/vars.py -> echovars.py
| 
* bafc5d7 2024-07-05 - bbsengine/io/terminal.py: updated width() such that MAXWIDTH is honored (clamp at 100, fe) (gitlab/main) [Jeff MacDonald]
| - bbsengine/io/terminal.py: updated width() such that MAXWIDTH is honored (clamp at 100, fe)
| 
* 0f8079d 2024-07-04 - bbsengine6/io/output.py:   * @project:9313 in logentry(), do not use hard-coded colors   * @project:9310 make many vars global (pos, wordwrap, indent) so they keep values between echo() calls   * @project:9305 io.echo() var references do not work   * commented out 'firstword' since it is unused   * on {{RESET}}, yield DECSTBM, SLASHALL, SPEED, INDENT, DECRC   * @project:9314 do not hard-code echo()'s level colors   * added tostr() [Jeff MacDonald]
| - bbsengine6/io/output.py:
|   * @project:9313 in logentry(), do not use hard-coded colors
|   * @project:9310 make many vars global (pos, wordwrap, indent) so they keep values between echo() calls
|   * @project:9305 io.echo() var references do not work
|   * commented out 'firstword' since it is unused
|   * on {{RESET}}, yield DECSTBM, SLASHALL, SPEED, INDENT, DECRC
|   * @project:9314 do not hard-code echo()'s level colors
|   * added tostr()
| 
* 94148f6 2024-07-04 - bbsengine6/util.py:   * @project:9307 fix hard-coded colors in heading()   * @project:9313 fix hard-coded colors in logentry()   * @project:9312 copy checkpassword() from bbsengine5   * databaseconnect -> database.connect() [Jeff MacDonald]
| - bbsengine6/util.py:
|   * @project:9307 fix hard-coded colors in heading()
|   * @project:9313 fix hard-coded colors in logentry()
|   * @project:9312 copy checkpassword() from bbsengine5
|   * databaseconnect -> database.connect()
| 
* f6f51f7 2024-07-04 - @project:9307: do not hard-code colors used by util.heading() [Jeff MacDonald]
| - @project:9307: do not hard-code colors used by util.heading()
| 
* 61b4474 2024-06-17 - bbsengine6/con/main.py: updated for bbsengine6 [Jeff MacDonald]
| - bbsengine6/con/main.py: updated for bbsengine6
| 
* 0deec98 2024-06-17 - bbsengine6/con/__main__.py: updated to bbsengine6 [Jeff MacDonald]
| - bbsengine6/con/__main__.py: updated to bbsengine6
| 
* 073e760 2024-06-17 - bbsengine6/Makefile: added [Jeff MacDonald]
| - bbsengine6/Makefile: added
| 
* 0aa9521 2024-06-17 - bbsengine6/skel/main.py: updated type hints [Jeff MacDonald]
| - bbsengine6/skel/main.py: updated type hints
| 
* d5e46a3 2024-06-17 - bbsengine6/skel/lib.py: minor tweaks (use PACKAGENAME, comment out database.buildargs() call) [Jeff MacDonald]
| - bbsengine6/skel/lib.py: minor tweaks (use PACKAGENAME, comment out database.buildargs() call)
| 
* 65368c8 2024-06-17 - bbsengine6/database.py:   * added postgres_to_python_list(), create(), createrol(), createschema()   * buildargdatabasegroup() -> buildargs()   * added --databaseschema   * changed update() to allow updating of the primarykey [Jeff MacDonald]
| - bbsengine6/database.py:
|   * added postgres_to_python_list(), create(), createrol(), createschema()
|   * buildargdatabasegroup() -> buildargs()
|   * added --databaseschema
|   * changed update() to allow updating of the primarykey
| 
* df8aef5 2024-05-16 - bbsengine6/module.py:   * added 'silent' kwarg to check() so the 'module not found' error can be     squelched.  I need this for projectflow, which checks for module     availability.   * tweak f-strings and debugging echo() calls   * runmodule()'s debug now defaults to False [Jeff MacDonald]
| - bbsengine6/module.py:
|   * added 'silent' kwarg to check() so the 'module not found' error can be
|     squelched.  I need this for projectflow, which checks for module
|     availability.
|   * tweak f-strings and debugging echo() calls
|   * runmodule()'s debug now defaults to False
| 
* 616b92a 2024-05-15 - bbsengine6/skel/main.py: add commented out call to lib.buildargs() [Jeff MacDonald]
| - bbsengine6/skel/main.py: add commented out call to lib.buildargs()
| 
* a8d6df5 2024-05-15 - bbsengine6/skel/__main__.py: call lib.buildargs() [Jeff MacDonald]
| - bbsengine6/skel/__main__.py: call lib.buildargs()
| 
* 32d97f3 2024-05-15 - bbsengine6/src/skel/__init__.py: updated main() to call 'main' module [Jeff MacDonald]
| - bbsengine6/src/skel/__init__.py: updated main() to call 'main' module
| 
* e8d7fce 2024-05-09 - bbsengine6/py/src/ss,tk: copied from bbsengine5 [Jeff MacDonald]
| - bbsengine6/py/src/ss,tk: copied from bbsengine5
| 
* 9d6ad62 2024-04-24 - bbsengine6/sql/blurb.sql: use 'moniker' (text) vs 'id' (bigint), update 'grant', and add 'flags' [Jeff MacDonald]
| - bbsengine6/sql/blurb.sql: use 'moniker' (text) vs 'id' (bigint), update 'grant', and add 'flags'
| 
* 0041f40 2024-04-17 - bbsengine6/screen.py: rewrote setarea() [Jeff MacDonald]
| - bbsengine6/screen.py: rewrote setarea()
| 
* 2581cfa 2024-04-17 - bbsengine6/py/src/skel/lib.py: added buildargs() [Jeff MacDonald]
| - bbsengine6/py/src/skel/lib.py: added buildargs()
| 
* 3b13e57 2024-04-17 - bbsengine6/py/src/skel/__main__.py: upgraded to bbsengine6 [Jeff MacDonald]
| - bbsengine6/py/src/skel/__main__.py: upgraded to bbsengine6
| 
* 4f95d26 2024-04-16 - bbsengine6/py/src/testemoji.py: step through emoji table [Jeff MacDonald]
| - bbsengine6/py/src/testemoji.py: step through emoji table
| 
* b97dd65 2024-04-15 - bbsengine6/py/src/testemoji.py: added [Jeff MacDonald]
| - bbsengine6/py/src/testemoji.py: added
| 
* ebbd2d3 2024-03-21 - bbsengine6/input.py:   * project#8720: fixed crash by wrapping call to getdate() in a try/except, and also modified input.date() to check if getdate() returned None.   * updated to import bbsengine6 modules individually   * fixed verifyValidDateExpression() prototype so it accepts a buffer as first arg   * added "today" as a date expression   * ttyio.echo() -> io.echo() [Jeff MacDonald]
| - bbsengine6/input.py:
|   * project#8720: fixed crash by wrapping call to getdate() in a try/except, and also modified input.date() to check if getdate() returned None.
|   * updated to import bbsengine6 modules individually
|   * fixed verifyValidDateExpression() prototype so it accepts a buffer as first arg
|   * added "today" as a date expression
|   * ttyio.echo() -> io.echo()
| 
* 34bb667 2024-03-17 - bbsengine6/py/src/skel/module.py: removed. [Jeff MacDonald]
| - bbsengine6/py/src/skel/module.py: removed.
| 
* 37273c9 2024-03-13 - bbsengine6/io/vars.py: added save() and restore() which is a stack like setarea() [Jeff MacDonald]
| - bbsengine6/io/vars.py: added save() and restore() which is a stack like setarea()
| 
* 7470bbd 2024-03-13 - bbsengine6/io/const.py: added 'shopping' emoji [Jeff MacDonald]
| - bbsengine6/io/const.py: added 'shopping' emoji
| 
* 3773620 2024-03-13 - bbsengine6/io/__init__.py: added init() [Jeff MacDonald]
| - bbsengine6/io/__init__.py: added init()
| 
* 564e1f7 2024-03-06 - bbsengine6/listbox.py: started on a feature to allow an item to be more than one line. [Jeff MacDonald]
| - bbsengine6/listbox.py: started on a feature to allow an item to be more than one line.
| 
* e437f40 2024-03-03 - bbsengine6/src/skel/: updated to modern standard [Jeff MacDonald]
| - bbsengine6/src/skel/: updated to modern standard
| 
* 40eff1c 2024-03-03 - bbsengine6/io/output.py: added handling for {{indent}} command [Jeff MacDonald]
| - bbsengine6/io/output.py: added handling for {{indent}} command
| 
* 887c586 2024-03-01 - bbsengine6/listbox.py:   * pass pagesize to Listbox constructor   * added handling of KEY_ENTER which returns a 'select' Op   * added handling of X, which returns an 'exit' Op   * if there are no items, return 'noitems' Op [Jeff MacDonald]
| - bbsengine6/listbox.py:
|   * pass pagesize to Listbox constructor
|   * added handling of KEY_ENTER which returns a 'select' Op
|   * added handling of X, which returns an 'exit' Op
|   * if there are no items, return 'noitems' Op
| 
* 27dc015 2024-03-01 - bbsengine6/module.py: reload module if needed added to check() [Jeff MacDonald]
| - bbsengine6/module.py: reload module if needed added to check()
| 
* bf9a475 2024-02-17 - bbsengine6/util.py: added getencryptedpassword(), updated pluralize() [Jeff MacDonald]
| - bbsengine6/util.py: added getencryptedpassword(), updated pluralize()
| 
* d691bf2 2024-02-17 - bbsengine6/member.py:   * ttyio -> io   * added 'tz' to member fields tuple   * updated f-strings   * added checksysop() -- checks for SYSOP flag. temp?   * fixed update(), by adding call to database.update() [Jeff MacDonald]
| - bbsengine6/member.py:
|   * ttyio -> io
|   * added 'tz' to member fields tuple
|   * updated f-strings
|   * added checksysop() -- checks for SYSOP flag. temp?
|   * fixed update(), by adding call to database.update()
| 
* 0ce4385 2024-02-17 - bbsengine6/__init__.py: commented out import statements which pull in *everything* by default [Jeff MacDonald]
| - bbsengine6/__init__.py: commented out import statements which pull in *everything* by default
| 
* ed9b289 2024-02-04 - bbsengine6/io/terminal.py: clamp getterminalwidth() to MAXWIDTH [Jeff MacDonald]
| - bbsengine6/io/terminal.py: clamp getterminalwidth() to MAXWIDTH
| 
* c49846c 2024-02-03 - bbsengine6/database.py:   * clean up some debugging echo()s   * fixed a crasher in classexists() [Jeff MacDonald]
| - bbsengine6/database.py:
|   * clean up some debugging echo()s
|   * fixed a crasher in classexists()
| 
* ee10642 2024-01-12 - bbsengine6/screen.py: copied updateprogress() from bbsengine5 [Jeff MacDonald]
| - bbsengine6/screen.py: copied updateprogress() from bbsengine5
| 
* c1fd2bd 2024-01-12 - bbsengine6/database.py: ttyio -> bbsengine.io [Jeff MacDonald]
| - bbsengine6/database.py: ttyio -> bbsengine.io
| 
* a044694 2024-01-12 - bbsengine6/util.py: added 'timedelta' (3 weeks, 6 days) and added 'determiner' for when there is only one item ('a' vs 'an') [Jeff MacDonald]
| - bbsengine6/util.py: added 'timedelta' (3 weeks, 6 days) and added 'determiner' for when there is only one item ('a' vs 'an')
| 
* 6d4b87a 2024-01-12 - bbsengine6/io/terminal.py: replace sys.stdout and sys.stdin with globals _streamout and _streamin [Jeff MacDonald]
| - bbsengine6/io/terminal.py: replace sys.stdout and sys.stdin with globals _streamout and _streamin
| 
* 1904fe0 2024-01-12 - bbsengine6/io/output.py: use new _streamout global instead of hard-coding sys.stdout [Jeff MacDonald]
| - bbsengine6/io/output.py: use new _streamout global instead of hard-coding sys.stdout
| 
* a6d43dd 2024-01-12 - bbsengine6/io/const.py: added 'desert' emoji [Jeff MacDonald]
| - bbsengine6/io/const.py: added 'desert' emoji
| 
* 78610bd 2024-01-12 - bbsengine6/io/__init__.py: added aliases for terminal.columns and terminal.lines to keep BC [Jeff MacDonald]
| - bbsengine6/io/__init__.py: added aliases for terminal.columns and terminal.lines to keep BC
| 
* c361565 2023-12-21 - bbsengine6/util.py: getdate.getdate() -> bbsengine6.input.getdate [Jeff MacDonald]
| - bbsengine6/util.py: getdate.getdate() -> bbsengine6.input.getdate
| 
* 9f110be 2023-12-21 - bbsengine6/input.py: changed comment [Jeff MacDonald]
| - bbsengine6/input.py: changed comment
| 
* 5181972 2023-12-21 - bbsengine6/listbox.py:   * cursorup on first item of page will go to previous page if it exists   * cursordown on last item of page will go to next page if it exists [Jeff MacDonald]
| - bbsengine6/listbox.py:
|   * cursorup on first item of page will go to previous page if it exists
|   * cursordown on last item of page will go to next page if it exists
| 
* 548fe9c 2023-12-14 - bbsengine6/listbox.py: added genericListboxItem class, untested [Jeff MacDonald]
| - bbsengine6/listbox.py: added genericListboxItem class, untested
| 
* d4b9754 2023-12-13 - bbsengine6/sig.py: ttyio -> bbsengine.io [Jeff MacDonald]
| - bbsengine6/sig.py: ttyio -> bbsengine.io
| 
* 21ca53e 2023-12-13 - bbsengine6/util.py: ttyio -> bbsengine.io [Jeff MacDonald]
| - bbsengine6/util.py: ttyio -> bbsengine.io
| 
* 1bf0862 2023-12-13 - bbsengine6/screen.py: ttyio -> bbsengine.io [Jeff MacDonald]
| - bbsengine6/screen.py: ttyio -> bbsengine.io
| 
* 9140511 2023-12-12 - bbsengine6/py/src/setup.py: changed license and packages [Jeff MacDonald]
| - bbsengine6/py/src/setup.py: changed license and packages
| 
* 02effbd 2023-12-12 - bbsengine6/io/Makefile: added [Jeff MacDonald]
| - bbsengine6/io/Makefile: added
| 
* eaca65a 2023-12-12 - bbsengine6/listbox.py:   * ttyio -> io   * handle KEY_PAGEUP and KEY_PAGEDOWN [Jeff MacDonald]
| - bbsengine6/listbox.py:
|   * ttyio -> io
|   * handle KEY_PAGEUP and KEY_PAGEDOWN
| 
* fd74e3b 2023-12-12 - testlistbox.py:   * moved Article2PresidentListboxItem from bbsengine6.listbox   * renamed setvariable() to setvar()   * added a query to get the total number of items   * renamed ttyio.echo to bbsengine6.io.echo   * changed title of listbox test [Jeff MacDonald]
| - testlistbox.py:
|   * moved Article2PresidentListboxItem from bbsengine6.listbox
|   * renamed setvariable() to setvar()
|   * added a query to get the total number of items
|   * renamed ttyio.echo to bbsengine6.io.echo
|   * changed title of listbox test
| 
* 85e0b2b 2023-12-06 - bbsengine6/__init__.py: added 'io' [Jeff MacDonald]
| - bbsengine6/__init__.py: added 'io'
| 
* 47bc967 2023-12-06 - bbsengine6/io/: copied from ttyio6 [Jeff MacDonald]
| - bbsengine6/io/: copied from ttyio6
| 
* ef4b76a 2023-12-05 - bbsengine6/www/: mass commit [Jeff MacDonald]
| - bbsengine6/www/: mass commit
| 
* c41a50a 2023-12-05 - bbsengine6/www/com/config-prod.php: added [Jeff MacDonald]
| - bbsengine6/www/com/config-prod.php: added
| 
* 462d3d1 2023-12-05 - bbsengine6/skin/: mass commit [Jeff MacDonald]
| - bbsengine6/skin/: mass commit
| 
* b5bb2f4 2023-12-05 - bbsengine6/www/php/Markdown*.php removed [Jeff MacDonald]
| - bbsengine6/www/php/Markdown*.php removed
| 
* e7ab3ea 2023-12-05 - bbsengine.org: copied www/Makefile [Jeff MacDonald]
| - bbsengine.org: copied www/Makefile
| 
* a2bcbb3 2023-12-03 - bbsengine6/input.py: fixed typo in getdate() [Jeff MacDonald]
| - bbsengine6/input.py: fixed typo in getdate()
| 
* 93eb0a2 2023-12-03 - bbsengine6/util.py,input.py: moved inputfilename to input.py [Jeff MacDonald]
| - bbsengine6/util.py,input.py: moved inputfilename to input.py
| 
* ea65c4e 2023-12-03 - bbsengine6/listbox.py: added displayitems() to Listbox [Jeff MacDonald]
| - bbsengine6/listbox.py: added displayitems() to Listbox
| 
* c9f1b63 2023-12-03 - bbsengine6/database.py: updated echo calls [Jeff MacDonald]
| - bbsengine6/database.py: updated echo calls
| 
* a9fa43c 2023-12-03 - bbsengine6/input.py: new module. merged getdate3 [Jeff MacDonald]
| - bbsengine6/input.py: new module. merged getdate3
| 
* b951d31 2023-12-03 - bbsengine6/menu.py: added some code that moves the cursor to the current item [Jeff MacDonald]
| - bbsengine6/menu.py: added some code that moves the cursor to the current item
| 
* 6269830 2023-11-30 - py/src/testmenu.py: renamed 'setvariable()' to 'setvar()' (both work currently); commented out call to screen.init() and screen.setarea() [Jeff MacDonald]
| - py/src/testmenu.py: renamed 'setvariable()' to 'setvar()' (both work currently); commented out call to screen.init() and screen.setarea()
| 
* dcd7b41 2023-11-29 - bbsengine6/: added 'listbox' and 'input' submodules [Jeff MacDonald]
| - bbsengine6/: added 'listbox' and 'input' submodules
| 
* 6585838 2023-11-26 - bbsengine6.listbox.ListboxItem:   * changed _init to accept 'width'   * added a help() method - bbsengine6.listbox.Listbox:   * clamp self.terminalwidth to 100   * .display() no longer has a terminalwidth arg   * handling of KEY_ENTER diverted to callback   * renamed 'mi' to 'item' [Jeff MacDonald]
| - bbsengine6.listbox.ListboxItem:
|   * changed _init to accept 'width'
|   * added a help() method
| - bbsengine6.listbox.Listbox:
|   * clamp self.terminalwidth to 100
|   * .display() no longer has a terminalwidth arg
|   * handling of KEY_ENTER diverted to callback
|   * renamed 'mi' to 'item'
| 
* ba01ed9 2023-11-26 - bbsengine6.menu:  * merged code in listbox that properly colors the current item  * calculate terminalwidth and clamp it at 100 [Jeff MacDonald]
| - bbsengine6.menu:
|  * merged code in listbox that properly colors the current item
|  * calculate terminalwidth and clamp it at 100
| 
* 8c7f82c 2023-11-25 - bbsengine6/menu.py: changed prototype for __getitem__() [Jeff MacDonald]
| - bbsengine6/menu.py: changed prototype for __getitem__()
| 
* fb8c558 2023-11-24 - bbsengine6/listbox.py: modified menu to behave like a single-page listbox including a callback function to handle keys [Jeff MacDonald]
| - bbsengine6/listbox.py: modified menu to behave like a single-page listbox including a callback function to handle keys
| 
* 18ba88f 2023-11-01 - bbsengine6/py/src/test*.py: added back [Jeff MacDonald]
| - bbsengine6/py/src/test*.py: added back
| 
* 74a3a67 2023-11-01 - bbsengine6/py/src/con/session.py: added main() [Jeff MacDonald]
| - bbsengine6/py/src/con/session.py: added main()
| 
* 980532f 2023-11-01 - bbsengine6/py/src/con/main.py: added 'S' option to list sessions [Jeff MacDonald]
| - bbsengine6/py/src/con/main.py: added 'S' option to list sessions
| 
* 6b6ec9c 2023-11-01 - bbsengine6/menu.py: bare minimum change to introduce 'pagesize' [Jeff MacDonald]
| - bbsengine6/menu.py: bare minimum change to introduce 'pagesize'
| 
* bff050f 2023-10-30 - bbsengine6/form.py: added FormItemCheckbox, FormItemRadioButton, and FormItemTextBox [Jeff MacDonald]
| - bbsengine6/form.py: added FormItemCheckbox, FormItemRadioButton, and FormItemTextBox
| 
* 96917bd 2023-10-30 - bbsengine6/database.py: in buildarggroup(), new kwarg 'suppress' [Jeff MacDonald]
| - bbsengine6/database.py: in buildarggroup(), new kwarg 'suppress'
| 
* e832a92 2023-10-30 - bbsengine/util.py: changed inputfilename() so that 'verify' is part of kw, and passed through to ttyio.inputstring() [Jeff MacDonald]
| - bbsengine/util.py: changed inputfilename() so that 'verify' is part of kw, and passed through to ttyio.inputstring()
| 
* 5fe1df1 2023-10-30 - bbsengine6/menu.py: removed 'default' kwarg from handle() [Jeff MacDonald]
| - bbsengine6/menu.py: removed 'default' kwarg from handle()
| 
* 51f5ceb 2023-10-30 - bbsengine6/module.py:   * check() now looks for 'main', 'buildargs', 'access', and 'init' in the module, and if any are missing returns False   * it also checks for proper argument names using the built-in 'inspect' module.   * buildargs() must always exist, and it is now allowed to return None [Jeff MacDonald]
| - bbsengine6/module.py:
|   * check() now looks for 'main', 'buildargs', 'access', and 'init' in the module, and if any are missing returns False
|   * it also checks for proper argument names using the built-in 'inspect' module.
|   * buildargs() must always exist, and it is now allowed to return None
| 
* 2e0e6c2 2023-10-30 - bbsengine6/session.py:   * wrap some echo statements in 'if args.debug' checks   * when there is more than one session, the message displayed is now of level 'warn'   * commented out an echo used for debugging [Jeff MacDonald]
| - bbsengine6/session.py:
|   * wrap some echo statements in 'if args.debug' checks
|   * when there is more than one session, the message displayed is now of level 'warn'
|   * commented out an echo used for debugging
| 
* c771b57 2023-10-30 - bbsengine6/menu.py: 'X' option no longer has a module; wrap calls to screen.setarea() in an 'if debug' check; add a {/all} to remove some artifacts [Jeff MacDonald]
| - bbsengine6/menu.py: 'X' option no longer has a module; wrap calls to screen.setarea() in an 'if debug' check; add a {/all} to remove some artifacts
| 
* 4fd7ae1 2023-10-30 - bbsengine6/php/engine.php:   * removed zoid6 specific choices from menu   * added a check to be sure $menu is not null before trying to sort it   * copied buildlabel() and normalizelabelpath() from bbsengine5 [Jeff MacDonald]
| - bbsengine6/php/engine.php:
|   * removed zoid6 specific choices from menu
|   * added a check to be sure $menu is not null before trying to sort it
|   * copied buildlabel() and normalizelabelpath() from bbsengine5
| 
* 77561ce 2023-10-30 - bbsengine6/php/session.php: tweeked debugging lines [Jeff MacDonald]
| - bbsengine6/php/session.php: tweeked debugging lines
| 
* d7e83a6 2023-10-30 - bbsengine6/php/database.php: added disconnect() [Jeff MacDonald]
| - bbsengine6/php/database.php: added disconnect()
| 
* b686bf2 2023-10-27 - bbsengine6/menu.py:   * removed extra {savecursor} call   * "X" is no longer handled by Menu() as special ("exit")   * added some screen.setarea() calls for debugging. these will eventually get wrapped into args.debug checks   * "enter" and "key" ops have been merged into "select" [Jeff MacDonald]
| - bbsengine6/menu.py:
|   * removed extra {savecursor} call
|   * "X" is no longer handled by Menu() as special ("exit")
|   * added some screen.setarea() calls for debugging. these will eventually get wrapped into args.debug checks
|   * "enter" and "key" ops have been merged into "select"
| 
* 703d7b3 2023-10-26 - bbsengine6/menu.py:   * finally got HOME, END, and wrapping working. tons of "off by one" problems [Jeff MacDonald]
| - bbsengine6/menu.py:
|   * finally got HOME, END, and wrapping working. tons of "off by one" problems
| 
* 061ae8e 2023-10-12 - bbsengine6/py/src/testmenu.py: added [Jeff MacDonald]
| - bbsengine6/py/src/testmenu.py: added
| 
* 87a61b0 2023-09-29 - bbsengine6/menu.py:   * moved form related items to form.py   * basically rewrote the Menu class   * Item is a new class   * Op is a NamedTuple [Jeff MacDonald]
| - bbsengine6/menu.py:
|   * moved form related items to form.py
|   * basically rewrote the Menu class
|   * Item is a new class
|   * Op is a NamedTuple
| 
* 1f23c1d 2023-09-29 - bbsengine6/util.py: added 'inputfilename()', commented out some unused code, and added some debugging [Jeff MacDonald]
| - bbsengine6/util.py: added 'inputfilename()', commented out some unused code, and added some debugging
| 
* 53869fd 2023-09-29 - bbsengine6/__init__.py: added import of new 'menu' module [Jeff MacDonald]
| - bbsengine6/__init__.py: added import of new 'menu' module
| 
* 28baaff 2023-09-25 - bbsengine6/util.py: copied inputfilename() from bbsengine5, added verify functions verifyFileExistsReadableWritable, verifyFileExistsReadable, and verifyDirExistsWritable [Jeff MacDonald]
| - bbsengine6/util.py: copied inputfilename() from bbsengine5, added verify functions verifyFileExistsReadableWritable, verifyFileExistsReadable, and verifyDirExistsWritable
| 
* 5b7ef68 2023-09-25 - bbsengine6/py/src/testinputfilename.py: short test script for util.inputfilename() [Jeff MacDonald]
| - bbsengine6/py/src/testinputfilename.py: short test script for util.inputfilename()
| 
* c446307 2023-09-24 - bbsengine6/py/src/testinputfilename.py: added [Jeff MacDonald]
| - bbsengine6/py/src/testinputfilename.py: added
| 
* 901b1af 2023-09-09 - bbsengine6/py/src/skel/: added skeleton code for a bbsengine6 module [Jeff MacDonald]
| - bbsengine6/py/src/skel/: added skeleton code for a bbsengine6 module
| 
* 848f2df 2023-09-04 - bbsengine6/session.py: minor change to debugging f-string; return new value from set() [Jeff MacDonald]
| - bbsengine6/session.py: minor change to debugging f-string; return new value from set()
| 
* f1bbfc8 2023-09-03 - bbsengine6/sig.py: added getchsigcomplete(); renamed old completer (compat with readlin) to gnusigcomplete() [Jeff MacDonald]
| - bbsengine6/sig.py: added getchsigcomplete(); renamed old completer (compat with readlin) to gnusigcomplete()
| 
* e5c1d3a 2023-09-01 - bbsengine6/sig.py: added builduri(), builddict(), buildrec(), and get() [Jeff MacDonald]
| - bbsengine6/sig.py: added builduri(), builddict(), buildrec(), and get()
| 
* 5cd85f2 2023-08-31 - bbsengine6/sql/getsubblurbs.sql: turns out I had already updated getsubnodes.sql to refer to blurbs but I never read the file. oops. [Jeff MacDonald]
| - bbsengine6/sql/getsubblurbs.sql: turns out I had already updated getsubnodes.sql to refer to blurbs but I never read the file. oops.
| 
* 3aa8366 2023-08-31 - bbsengine6/sql/getreplies.sql: renamed to getsubblurbs.sql [Jeff MacDonald]
| - bbsengine6/sql/getreplies.sql: renamed to getsubblurbs.sql
| 
* 9ed7c3a 2023-08-31 - bbsengine6/sql/getreplies.sql: copied from socrates [Jeff MacDonald]
| - bbsengine6/sql/getreplies.sql: copied from socrates
| 
* 0c73f1e 2023-08-29 - bbsengine6/blurb,database,form: no idea what the changes were-- diff is empty [Jeff MacDonald]
| - bbsengine6/blurb,database,form: no idea what the changes were-- diff is empty
| 
| Signed-off-by: Jeff MacDonald <jam@zoidtechnologies.com>
| 
* 270cb21 2023-08-29 - bbsengine6/editor.py:   * worked on .h (help)   * started on other dot commands [Jeff MacDonald]
| - bbsengine6/editor.py:
|   * worked on .h (help)
|   * started on other dot commands
| 
* eada6ce 2023-08-29 - bbsengine/module.py:   * added a lot more debugging   * use more f-strings [Jeff MacDonald]
| - bbsengine/module.py:
|   * added a lot more debugging
|   * use more f-strings
| 
* 8bf6c91 2023-08-29 - bbsengine6/menu.py: fixed a typo in class Menu (extra curly brace) [Jeff MacDonald]
| - bbsengine6/menu.py: fixed a typo in class Menu (extra curly brace)
| 
* 0cf78a3 2023-08-29 - bbsengine6/util.py: working on filedisplay(); in inputpassword(), accept a 'mask' kwarg and pass it to inputstring(); working on datestamp() so it shows timezone properly [Jeff MacDonald]
| - bbsengine6/util.py: working on filedisplay(); in inputpassword(), accept a 'mask' kwarg and pass it to inputstring(); working on datestamp() so it shows timezone properly
| 
* d083e96 2023-08-29 - bbsengine6/member.py: tweaked debugging echo() [Jeff MacDonald]
| - bbsengine6/member.py: tweaked debugging echo()
| 
* ac33ea4 2023-08-05 - bbsengine6/src/con/main.py: changed the prompt a little [Jeff MacDonald]
| - bbsengine6/src/con/main.py: changed the prompt a little
| 
* 16abacd 2023-08-05 - bbsengine6/src/con/__main__.py: added call to bbsengine.session.start() [Jeff MacDonald]
| - bbsengine6/src/con/__main__.py: added call to bbsengine.session.start()
| 
* fb7e46f 2023-08-05 - bbsengine6/util.py:   * renamed 'title()' to 'heading()' and tweaked the code a little   * added collapserange(), expandrange(), rangestr(), and printr() for handling ranges like 1-42 (projectflow?)   * copied filedisplay() from bbsengine5   * copied diceroll() from bbsengine5 [Jeff MacDonald]
| - bbsengine6/util.py:
|   * renamed 'title()' to 'heading()' and tweaked the code a little
|   * added collapserange(), expandrange(), rangestr(), and printr() for handling ranges like 1-42 (projectflow?)
|   * copied filedisplay() from bbsengine5
|   * copied diceroll() from bbsengine5
| 
* e2d9421 2023-08-04 - bbsengine6/module.py: args.debug -> debug; changed runsubmodule() into a passthru, needs to be evaluated [Jeff MacDonald]
| - bbsengine6/module.py: args.debug -> debug; changed runsubmodule() into a passthru, needs to be evaluated
| 
* df672dd 2023-08-04 - bbsengine6/screen.py: updated setarea() docs [Jeff MacDonald]
| - bbsengine6/screen.py: updated setarea() docs
| 
* d6b9d20 2023-08-04 - bbsengine6/src/testsession.py,testeditor.py: added [Jeff MacDonald]
| - bbsengine6/src/testsession.py,testeditor.py: added
| 
* 99c8ba9 2023-08-04 - bbsengine6.session   * added get(), set()   * fixed start()   * added garbagecollect()   * added buildsession() -> dict 'session'   * build(rec) -> dict 'session'   * garbagecollect() is only called in start() -- php has better knobs for the moment [Jeff MacDonald]
| - bbsengine6.session
|   * added get(), set()
|   * fixed start()
|   * added garbagecollect()
|   * added buildsession() -> dict 'session'
|   * build(rec) -> dict 'session'
|   * garbagecollect() is only called in start() -- php has better knobs for the moment
| 
* f81a68f 2023-08-02 - bbsengine6/editor.py: added an 'exit' command and handling of KEY_ENTER [Jeff MacDonald]
| - bbsengine6/editor.py: added an 'exit' command and handling of KEY_ENTER
| 
* 927e39e 2023-08-01 - bbsengine6/editor.py: added [Jeff MacDonald]
| - bbsengine6/editor.py: added
| 
* b299aa0 2023-07-17 - bbsengine6/con/: added 'email', 'member', and 'session' submodules [Jeff MacDonald]
| - bbsengine6/con/: added 'email', 'member', and 'session' submodules
| 
* 93af9fa 2023-06-27 - bbsengine6/screen.py: renamed ttyio.interpretecho() to ttyio.interpret() [Jeff MacDonald]
| - bbsengine6/screen.py: renamed ttyio.interpretecho() to ttyio.interpret()
| 
* dec1d40 2023-06-27 - bbsengine6/session.py: added write(), get(), updatelastactivity(), start(), build() and currentsessionid [Jeff MacDonald]
| - bbsengine6/session.py: added write(), get(), updatelastactivity(), start(), build() and currentsessionid
| 
* 6112f8c 2023-06-27 - bbsengine6/py/src/setup.py: changed bbsengine6 license to GPLv2 from GPLv3. [Jeff MacDonald]
| - bbsengine6/py/src/setup.py: changed bbsengine6 license to GPLv2 from GPLv3.
| 
* 30e6331 2023-06-27 - bbsengine6/con/lib.py: added setarea() and runsubmodule(). [Jeff MacDonald]
| - bbsengine6/con/lib.py: added setarea() and runsubmodule().
| 
* 89b6dd4 2023-06-27 - bbsengine6/con/main.py: added a menu that currently only accepts 'm' for member and calls the member submodule [Jeff MacDonald]
| - bbsengine6/con/main.py: added a menu that currently only accepts 'm' for member and calls the member submodule
| 
* 344e9dc 2023-06-27 - bbsengine6/con/__main__.py: added some boilerplate that calls the 'main' submodule [Jeff MacDonald]
| - bbsengine6/con/__main__.py: added some boilerplate that calls the 'main' submodule
| 
* 171e6f3 2023-06-08 - bbsengine6/*.py: modified but no diff output?! [Jeff MacDonald]
| - bbsengine6/*.py: modified but no diff output?!
| 
* 1dc0a37 2023-06-08 - bbsengine6/member.py:   * renamed builddict() to buildrec() -- builds a cleaned dictionary for use in the databse (filter epoch fields, etc)   * added build() which builds a member dictionary from a database record   * changed getcurrentid() so it uses os.getlogin(), which is cross platform vs pwd, which does not work on windowsks   * added getbymoniker()   * copied setflag(), getflag(), updateflag(), and checkflag() from bbsengine5   * added setpassword()   * added setattributes()   * copied verifyMemberNotFound and verifyMemberFound from bbsengine5   * added insert()   * commented out import of 'pwd' [Jeff MacDonald]
| - bbsengine6/member.py:
|   * renamed builddict() to buildrec() -- builds a cleaned dictionary for use in the databse (filter epoch fields, etc)
|   * added build() which builds a member dictionary from a database record
|   * changed getcurrentid() so it uses os.getlogin(), which is cross platform vs pwd, which does not work on windowsks
|   * added getbymoniker()
|   * copied setflag(), getflag(), updateflag(), and checkflag() from bbsengine5
|   * added setpassword()
|   * added setattributes()
|   * copied verifyMemberNotFound and verifyMemberFound from bbsengine5
|   * added insert()
|   * commented out import of 'pwd'
| 
* b2fe05e 2023-05-26 - bbsengine6/sql/member.sql: rename 'name' to 'moniker', added a 'not null' to 'email', and removed 'shell' [Jeff MacDonald]
| - bbsengine6/sql/member.sql: rename 'name' to 'moniker', added a 'not null' to 'email', and removed 'shell'
| 
* 7f2638c 2023-05-23 - bbsengine6/sql/: replaced references to 'apache' and 'www-data' with the psql var 'web' which is set by bbsengine6.sql [Jeff MacDonald]
| - bbsengine6/sql/: replaced references to 'apache' and 'www-data' with the psql var 'web' which is set by bbsengine6.sql
| 
* a7c75dd 2023-05-23 - bbsengine6/sql/node.sql: renamed to blurb.sql [Jeff MacDonald]
| - bbsengine6/sql/node.sql: renamed to blurb.sql
| 
* f7a63d4 2023-05-15 - bbsengine6/Makefile: added [Jeff MacDonald]
| - bbsengine6/Makefile: added
| 
* f823cec 2023-05-15 - bbsengine6.database: added resultiter from bbsengine5 [Jeff MacDonald]
| - bbsengine6.database: added resultiter from bbsengine5
| 
* 9bbe777 2023-05-14 - bbsengine6/py/src/Makefile: added [Jeff MacDonald]
| - bbsengine6/py/src/Makefile: added
| 
* 0d9ab44 2023-05-14 - bbsengine6/py/src/setup.py: updated [Jeff MacDonald]
| - bbsengine6/py/src/setup.py: updated
| 
* 2af0759 2023-05-14 - bbsengine6/py/src/bbsengine6/: added [Jeff MacDonald]
| - bbsengine6/py/src/bbsengine6/: added
| 
* 5ef86a1 2023-05-02 - bbsengined6/py/src/con/: added some code to __main__ [Jeff MacDonald]
| - bbsengined6/py/src/con/: added some code to __main__
| 
* a7ebd7e 2023-04-30 - bbsengine6/py/src/con/Makefile: added [Jeff MacDonald]
| - bbsengine6/py/src/con/Makefile: added
| 
* 3d86d8e 2023-04-30 - bbsengine6/py/src/setup.py: configured for bbsengine6 including 'con' [Jeff MacDonald]
| - bbsengine6/py/src/setup.py: configured for bbsengine6 including 'con'
| 
* cac3ca5 2023-04-30 - bbsengine6/py/src/Makefile: added [Jeff MacDonald]
| - bbsengine6/py/src/Makefile: added
| 
* 78f65b3 2023-04-30 - bbsengine6/py/src/setup.py: copied from bbsengine5 [Jeff MacDonald]
| - bbsengine6/py/src/setup.py: copied from bbsengine5
| 
* f5b080f 2023-04-30 - bbsengine6/py/src/con/: added [Jeff MacDonald]
| - bbsengine6/py/src/con/: added
| 
* 1c17a3d 2023-04-28 - bbsengine6/sql/mantra.sql: renamed to fortune.sql [Jeff MacDonald]
| - bbsengine6/sql/mantra.sql: renamed to fortune.sql
| 
* 581ad43 2023-04-21 - bbsengine6/sql/nodeview.sql -> blurbview.sql [Jeff MacDonald]
| - bbsengine6/sql/nodeview.sql -> blurbview.sql
| 
* 42f9fe0 2023-04-17 - bbsengine6/skin/tmpl/notify.tmpl: some quick edits [Jeff MacDonald]
| - bbsengine6/skin/tmpl/notify.tmpl: some quick edits
| 
* 755d00b 2023-04-15 - bbsengine6/www/: copied htaccess-prod, config-prod, htpasswd-prod, Makefiles, and bbsenginedotorg.sql from bbsengine5 [Jeff MacDonald]
| - bbsengine6/www/: copied htaccess-prod, config-prod, htpasswd-prod, Makefiles, and bbsenginedotorg.sql from bbsengine5
| 
* 6219037 2023-04-14 - bbsengine6/php/engine.php: renamed displaypage() arg from 'kw' to 'data' [Jeff MacDonald]
| - bbsengine6/php/engine.php: renamed displaypage() arg from 'kw' to 'data'
| 
* ceac73c 2023-04-14 - bbsengine6/php/database.php: use proper namespace for logentry() call [Jeff MacDonald]
| - bbsengine6/php/database.php: use proper namespace for logentry() call
| 
* 4ba09e0 2023-04-14 - bbsengine6/php/Input*.php: added [Jeff MacDonald]
| - bbsengine6/php/Input*.php: added
| 
* 229d15f 2023-04-14 - rewrote most of \bbsengine6\session - added insert() and update() - if a read fails, insert it as a new session - write() updated to use insert() - there is no update() yet - added a few calls to \bbsengine6\logentry() to track which of my functions are being called by php - changed validate() to return true only if the session has not expired [Jeff MacDonald]
| - rewrote most of \bbsengine6\session
| - added insert() and update()
| - if a read fails, insert it as a new session
| - write() updated to use insert()
| - there is no update() yet
| - added a few calls to \bbsengine6\logentry() to track which of my functions are being called by php
| - changed validate() to return true only if the session has not expired
| 
* dc0b9b4 2023-04-14 - copied php, skin, and smarty from bbsengine5 [Jeff MacDonald]
| - copied php, skin, and smarty from bbsengine5
| 
* 4e298d5 2023-04-13 - bbsengine6/js/query.smoothState.js: copied from zoidweb4 [Jeff MacDonald]
| - bbsengine6/js/query.smoothState.js: copied from zoidweb4
| 
* 53494e7 2023-04-13 - bbsengine6/www/js/bbsengine6.js: moved to 'js' so it can be installed to engine.zoid [Jeff MacDonald]
| - bbsengine6/www/js/bbsengine6.js: moved to 'js' so it can be installed to engine.zoid
| 
* fb6a305 2023-04-11 - bbsengine6/www/php/index.php: ported to bbsengine6, set some blurb data to null so the templates will work [Jeff MacDonald]
| - bbsengine6/www/php/index.php: ported to bbsengine6, set some blurb data to null so the templates will work
| 
* 98f911e 2023-04-09 - bbsengine6/js/: copied from bbsengine5/js/ [Jeff MacDonald]
| - bbsengine6/js/: copied from bbsengine5/js/
| 
* 0aff6d6 2023-04-06 - bbsengine6/sql/newuser.sql: removed 'finn' role [Jeff MacDonald]
| - bbsengine6/sql/newuser.sql: removed 'finn' role
| 
* 8479405 2023-04-06 - bbsengine6/sql/role.sql: removed 'finn' role [Jeff MacDonald]
| - bbsengine6/sql/role.sql: removed 'finn' role
| 
* b2ef94e 2023-04-05 - bbsengine6/sql/bbsengine5.sql: renamed to bbsengine6.sql [Jeff MacDonald]
| - bbsengine6/sql/bbsengine5.sql: renamed to bbsengine6.sql
| 
* 0d6b311 2023-04-05 - bbsengine6/sql/: copied from bbsengine5 [Jeff MacDonald]
| - bbsengine6/sql/: copied from bbsengine5
| 
* 639957f 2023-04-04 - bbsengine6/skin/: copied from bbsengine5/skin/ [Jeff MacDonald]
| - bbsengine6/skin/: copied from bbsengine5/skin/
| 
* 005f904 2023-04-03 - bbsengine6/php/: added modules session, database, and engine [Jeff MacDonald]
| - bbsengine6/php/: added modules session, database, and engine
| 
* 6460d91 2023-04-03 - bbsengine6/php/Makefile: added 'stage' target [Jeff MacDonald]
| - bbsengine6/php/Makefile: added 'stage' target
| 
* 0f6d8c2 2023-04-03 - bbsengine6/www/js/: copied from bbsengine5 [Jeff MacDonald]
| - bbsengine6/www/js/: copied from bbsengine5
| 
* 4c190bb 2023-04-02 - bbsengine6/: added Makefile and php/Makefile [Jeff MacDonald]
| - bbsengine6/: added Makefile and php/Makefile
| 
* e395fcd 2023-04-02 - bbsengine6/php/database.php: switched out MDB2 for PDO [Jeff MacDonald]
| - bbsengine6/php/database.php: switched out MDB2 for PDO
| 
* 382168a 2023-04-02 - bbsengine6/php/: added database, session, and engine [Jeff MacDonald]
| - bbsengine6/php/: added database, session, and engine
| 
* d09125c 2023-04-02 - bbsengine6/README.md: updated [Jeff MacDonald]
| - bbsengine6/README.md: updated
| 
* f843f5d 2022-08-24 bbsengine6/README.md: added. [Jeff MacDonald]
  bbsengine6/README.md: added.
