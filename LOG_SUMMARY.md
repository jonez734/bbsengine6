<!--
GENERATED FILE — DO NOT EDIT BY HAND.

Produced by the `log` Makefile target (`make log`). This is the
date-grouped, subject-only view of the same history that LOG.md
and LOG_FULL.md show in full. Handy for skimming the project
timeline.
-->
## 2026-03-30
  f416127 Group LOG_SUMMARY by date with date headers (HEAD -> main) [J (eff)]
  523cda2 Add Makefile log target to generate LOG_FULL.md and LOG_SUMMARY.md (github/main) [J (eff)]
  474cbc3 security: remove hardcoded reCAPTCHA keys, use environment variables instead [J (eff)]
  e05b90a Update bbsengine6: Enable getdate-next dependency and fix Makefile to use PYTHON variable [J (eff)]
## 2026-03-29
  5abfd05 Fix remaining .spec references to .md in console.md related documentation section [J (eff)]
  2840f02 Update references from .spec to .md file extensions in handbook documentation [J (eff)]
  872b641 Rename handbook spec files from .spec to .md extension [J (eff)]
  c6a4432 bbsengine6: added .gitattributes (*.spec as markdown) [Jeff MacDonald]
  ddf14b5 Add comprehensive console module specification suite [J (eff)]
  d893afe Refactor console check modules for clean, robust code [J (eff)]
  c6b0963 Update database.spec - document that args parameter is optional in connect() [J (eff)]
  2d88cb3 Fix notify.count() error 110 regression - make args optional in database.connect() [J (eff)]
  8988863 Fix connection pool exhaustion in notify.count by using database.connect context manager [J (eff)]
  1fafd23 Fix 'connection is closed' error in member edit by moving commit inside with block [J (eff)]
  6fe2ea2 Fix enum type detection to prevent duplicate creation errors [J (eff)]
  bbf5f4e fix: propagate pool/args to inputchoice in member console menu [J (eff)]
  83232d8 fix: propagate pool/conn/args to notify.count() and log pool warning once [J (eff)]
## 2026-03-28
  f133db0 fix: add UNIQUE INDEX to map_member_flag table for UPSERT support [J (eff)]
  b6b4766 fix: refactor member updates to use atomic UPSERT and explicit cascade ordering [J (eff)]
  e9a216a docs: update specs for primary key change handling and transaction management [J (eff)]
  3965378 fix: handle moniker changes as special case with explicit transaction management [J (eff)]
  8cd6ad2 fix: disable notification checking in inputstring() tight input loop [J (eff)]
  4f28ea6 Fix: Remove double JSON conversion in member.buildrec() [J (eff)]
  b7aaf80 Rename timedelta_() to timedeltastr() for better readability [J (eff)]
  8b8b31b Implement empyre connection pooling pattern in notify.count() [J (eff)]
  5dc57c4 Fix dict/tuple row access in notify.py for psycopg3 cursor compatibility [J (eff)]
  3603350 docs: update NOTIFY_TESTING.md with automatic setup instructions [J (eff)]
  5b7b864 feat: add pytest conftest for automatic notify schema initialization and fix database connection [J (eff)]
  ec3baa3 fix: use sql.Identifier() for properly quoting schema-qualified table names in notify.py and session.py [J (eff)]
  c5b9770 Fix testsession.py test mocks to use timezone-aware datetimes [J (eff)]
  0a5de77 Fix timezone-aware datetime in test fixtures [J (eff)]
  2bf987a Fix timezone-aware datetime in notify.py [J (eff)]
  5883820 Fix timezone-aware datetime comparisons in session.py [J (eff)]
  cfffb8c refactor: rename currentsessionid functions with type annotations [J (eff)]
  f8486cd Security: add path validation to folder module [J (eff)]
  443716e security: improve session.py with thread safety and expiry validation [J (eff)]
  69f24f1 Fix: query base tables directly in get_notifications instead of views [J (eff)]
  324e471 Add checknotify console module and integrate with setup [J (eff)]
## 2026-03-27
  81058d4 fix: use echo_traceback in exception handlers [J (eff)]
  f6090a6 fix: add echo_traceback to notify.py exception handlers [J (eff)]
  02b34f4 refactor: rename get_notification_count() to notify.count() [J (eff)]
  b0fa7cd feat: integrate notifications into getch() with F2 key display and bell sound [J (eff)]
  35cbd51 Implement notification system (notify.py) with SQL schema and 37 tests [J (eff)]
  929636a Add notification system specification (notify.spec) [J (eff)]
  c09e9b9 Add threading-based async event system for keyboard input [J (eff)]
  09d139a Fix F841 unused variables and F401 unused imports [J (eff)]
  77aa1f9 Fix F821 undefined name errors [J (eff)]
  4af1549 Fix LSP errors: replace ttyio with bbsengine6.io, remove unused imports [J (eff)]
## 2026-03-25
  b5168d5 Add multi-character hotkey support to Listbox class [J (eff)]
## 2026-03-24
  2bed5f5 Fix listbox item display by disabling wordwrap in echo calls [J (eff)]
  d7e4607 Fix Article2PresidentListboxItem.display() signature to match ListboxItem contract [J (eff)]
## 2026-03-23
  dd7fccf Add robust type checking and error handling to expandrange() and collapserange() [J (eff)]
  e14f447 Add io.terminal.title() function, remove {settitle} echo command [J (eff)]
  6ef9c6e Bump version to 0.0.1.dev202603231010 [J (eff)]
  131790b demo_listbox_static_itemheight2: disable custom display function [J (eff)]
## 2026-03-22
  c49732f - bbsengine6.listbox: cleaned up some debugging [Jeff MacDonald]
  4e8b55c Comment out logentry() calls in listbox.py for cleaner output [J (eff)]
  a1a2713 Fix rendered_length() counting ACS control codes as visible characters [J (eff)]
  2375dda Format code with ruff [J (eff)]
  906fad8 Fix listbox item width rendering with ANSI-aware padding [J (eff)]
## 2026-03-21
  2e149a8 Pass parsed prgargs to module main function [J (eff)]
  c6f02ca Document buildargs() subparser parameter for CLI subcommands [J (eff)]
## 2026-03-20
  e0bfe18 Add convert_for_jsonb() helper and execute() wrapper for safe JSONB encoding [J (eff)]
  fb531b7 Fix JSON serialization: recursively convert datetime in dicts/lists [J (eff)]
  1506a19 database: fix JSON serialization for type objects and Jsonb wrappers [J (eff)]
  869a944 Correct product name and version in all spec files [J (eff)]
  55a194b Strip bbsengine6- prefix from spec filenames, update product name to bbsengine6 v0.0.1.dev [J (eff)]
  89df3cb Move handbook/*.spec to handbook/specs/, update cross-references [J (eff)]
  89ed64a Update handbook specs to reflect current module.py architecture [J (eff)]
  e2639e6 specs: remove non-existent bbsengine6/modules/ path references [J (eff)]
  612c0fc util.py: add thread safety, fix bugs, and add spec [J (eff)]
  10abc8c Add member.spec to handbook [J (eff)]
  37368bd member.py: add thread safety, column allowlist, and standardize error handling [J (eff)]
## 2026-03-19
  9ac00ef Remove redundant conn.commit() calls - auto_commit handles this [J (eff)]
  d97e03a Fix INTRANS: add auto_commit=True to database.connect() [J (eff)]
  fad7bf3 Add database.with_connection utility for consistent connection handling [J (eff)]
  dc57dd9 Fix JSON serialization: handle type objects and datetime in database.update [J (eff)]
  95c112b Fix JSON serialization: handle datetime type objects in player.buildrec [J (eff)]
  6d7d143 Fix database.exists to commit after query [J (eff)]
  2a83d0e Fix duplicate pool.putconn call that caused error [J (eff)]
  0b20648 Add pool caching to fix 'connection to wrong pool' error [J (eff)]
  089a783 Revert pool caching, fix test to use mock [J (eff)]
  1846b28 Fix INTRANS: commit after getcurrentmoniker gets own connection [J (eff)]
  449ba8d Add traceback to debug second getcurrentmoniker call [J (eff)]
  7ae7065 Add debug logging to trace INTRANS [J (eff)]
  526a833 Fix: use pop() to remove conn from kwargs, restore after getcurrentmoniker [J (eff)]
  977ff9f Fix INTRANS: pass conn to getcurrentmoniker in getmembersession [J (eff)]
  1e9e313 Add debug logging to trace second connection in getcurrentmoniker [J (eff)]
  3154bfd Add debug logging to trace INTRANS issue [J (eff)]
  39330ba Add debug logging to trace INTRANS issue [J (eff)]
  513be8d Refactor session module: consistent conn/pool handling pattern [J (eff)]
  91d32c1 Fix INTRANS rollback: ensure conn passed to inner functions and commits [J (eff)]
  65b1c8e Add comprehensive tests for session module [J (eff)]
  dcac5bb Fix INTRANS rollback: add conn.commit() when existing session found [J (eff)]
  526da84 Fix INTRANS connection rollback in session management [J (eff)]
  3ee8820 Fix database.update() to wrap dict/list values in Jsonb for jsonb columns [J (eff)]
## 2026-03-18
  91f14f3 database: add commit param to insert(), default commit=True for update() and insert() [J (eff)]
  d10115c Update database.spec: document connect() uses getconn/putconn, raises if pool is None, shows correct usage pattern [J (eff)]
  9ba6307 Use pool kwarg passed to connect() instead of calling getpool(). Raise if pool is None. [J (eff)]
  b8a5853 Fix connect() to use getconn/putconn — was returning pool.connection() directly which is a GeneratorContextManager, not a Connection. Restore context manager pattern with proper connection lifecycle. [J (eff)]
  e19803a Add exception handling to connect() for robust error reporting [J (eff)]
  8cb3a0b Rollback connect() to non-generator, add robust pool cleanup in tests [J (eff)]
  05f51c0 Add SQL injection tests for database functions [J (eff)]
  5d523c3 Add database.py tests with Unix socket and TCP support [J (eff)]
  da18e56 Use f-strings for sql.SQL composition in database.py [J (eff)]
  bb33566 database.py: fix connection leaks, closures, and error handling [J (eff)]
## 2026-03-16
  320d35f - bbsengine6/io/screen.py: commented out debuging echo() calls [Jeff MacDonald]
## 2026-03-15
  2f9df9d Fix missing quote in listbox.item.highlighted skin key [J (eff)]
  dda7c02 Convert dict and list values to Jsonb in insert [J (eff)]
  98129a5 Add debug logging for right() callable in setbottombar [J (eff)]
  f433622 Improve error messages in module check for main function [J (eff)]
  300c2a3 Bump version to 0.0.1.dev202603142153 [J (eff)]
  c9280ea Add getdate module for parsing date expressions [J (eff)]
  dfe5b80 Add listbox skin variables and type validation to echo [J (eff)]
## 2026-03-12
  a02343c Add demo_article2_givenyear - list presidents by year in 4 mutually exclusive groups [J (eff)]
  dc671cd Update version; add inputchar alias for inputchoice in io module [J (eff)]
  f4fbcef session: Fix _work() call signature in start(); remove dead code [J (eff)]
  5e4fabb Refactor setpassword to use connection pattern; fix getcurrentmoniker call in setflag [J (eff)]
  b452b56 Remove extra blank line in database.py [J (eff)]
## 2026-03-11
  df402ed Add init() function to listbox for color variable setup [J (eff)]
## 2026-03-10
  0443e1d Update version config and pyproject.toml [J (eff)]
  9dfb7cd bbsengine6/io: export getch from getch module [J (eff)]
  4d87a3c Add noqa for Jsonb import - used externally via database.Jsonb() [J (eff)]
  01a30de Fix schema-qualified table names in database.update() and database.insert() [J (eff)]
  3446dc6 Export inputstring/inputinteger/inputboolean/inputchoice from io module [J (eff)]
## 2026-03-08
  4f9947d Export setvar/getvar/register_emoji/register_emojis from io module [J (eff)]
## 2026-03-07
  23be3c6 Add inputdate.py module using getdate-next package [J (eff)]
## 2026-03-04
  2633446 Sync io with asimov.io: add deprecation headers, update imports/signatures [J (eff)]
## 2026-02-27
  33a46c9 Fix listbox item padding and demo prompts [J (eff)]
  aadad0e Fix listbox item padding to use space instead of dot [J (eff)]
  aefa822 Fix listbox title centering regression [J (eff)]
## 2026-02-26
  6ada53d Update listbox width calculations, fix title centering, update demo specs [jam]
  fc2819a Fix listbox title centering alignment [jam]
  9647e79 Fix listbox width calculations for borders and title [jam]
## 2026-02-25
  1d10eee Update spec: add bottom bar, helper functions, None value handling [Jeff MacDonald]
  11b81cf Add compose_person_name() helper function [Jeff MacDonald]
  4bb13cc Update demo_listbox_masterdetail: add args param, skip None values, fix attractions listbox, return to categories [Jeff MacDonald]
  c2c2624 Update spec with echovars documentation [Jeff MacDonald]
  aadfe0a Update listbox with echovars and fix attraction queries [Jeff MacDonald]
  e771a81 Update demo_listbox_masterdetail: add listboxes for detail views [Jeff MacDonald]
  4e9529c Add demo_listbox_masterdetail: master-detail view for US Presidents [Jeff MacDonald]
  1346b55 feat: add new PHP modules, Python utilities, templates, and tests [Jeff MacDonald]
  9ab5dbd docs: add LOG.md and NOTES.md [Jeff MacDonald]
  f6b5db4 chore: add .gitignore patterns for build artifacts and caches [Jeff MacDonald]
  4d82c36 misc: various updates across php, python, and skin modules [Jeff MacDonald]
## 2026-02-24
  7d71b3f feat(getch): add timeout=None to block indefinitely; add height comparison to demo [Jeff MacDonald]
  954a4f3 docs: add spec files for demo_listbox_*.py demos [Jeff MacDonald]
  3500a13 fix: swap reset and restorecursor in finally block [Jeff MacDonald]
  3ca2f14 fix: add database and schema existence checks, use database.buildargs() [Jeff MacDonald]
  6501b8b fix: add robust error handling for database pool and connections [Jeff MacDonald]
  4acc154 fix: use database.getpool() to create connection pool in demo [Jeff MacDonald]
  724199a fix: syntax error in ListboxCursor - positional args must be keyword args [Jeff MacDonald]
  630ecf3 feat: add ListboxCursor subclass for database cursor lazy-loading [Jeff MacDonald]
  f4383fc listbox: add _highlight_item(), ListboxResult('redraw'), and fix lint [Jeff MacDonald]
  9ab873a test: add unit tests for {cha} cursor horizontal absolute command [Jeff MacDonald]
  feaa8a8 Make listbox prompt a required positional argument and standardize demo formatting [Jeff MacDonald]
  c7cfe4b fix: key_pageup rings bell when on first item of first page [Jeff MacDonald]
  297caf1 fix: key_pageup/pagedown jump to first/last item instead of bell [Jeff MacDonald]
  a739073 feat: add itemheight support to listbox with multi-line items [Jeff MacDonald]
  fac3796 refactor: rename BORDER_HLINE_WIDTH to BORDER_CORNER_WIDTH [Jeff MacDonald]
  00f7a79 refactor: rename BORDER_LINE_WIDTH to BORDER_HLINE_WIDTH for clarity [Jeff MacDonald]
  9a8a087 refactor: replace border width magic numbers with BORDER_WIDTH_LEFT and BORDER_WIDTH_RIGHT [Jeff MacDonald]
  cf94a56 refactor: replace magic number 4 with CONTENT_PADDING constant in listbox [Jeff MacDonald]
## 2026-02-23
  a7e5c67 docs: add integration tests and finalize features [Jeff MacDonald]
  e21af08 feat: add shell completion with argcomplete [Jeff MacDonald]
  e03cd98 feat: implement dynamic module discovery with caching [Jeff MacDonald]
  b329043 feat: add module-specific argument support [Jeff MacDonald]
  ed1c9a6 feat: comprehensive help handling with argparse subcommands [Jeff MacDonald]
  282723c Add comprehensive BBSEngine v6.0 master specification [Jeff MacDonald]
  1f6e179 Remove backup files (tag: v202602231857) [Jeff MacDonald]
  706a1f9 Update handbook and js files [Jeff MacDonald]
  25991bd Rename listbox_next to listbox [Jeff MacDonald]
  81cbf68 Rename listbox_next to listbox [Jeff MacDonald]
  a5f907c Move spec files to handbook/specs/ [Jeff MacDonald]
  c030ab1 Update spec with docstring requirement note [Jeff MacDonald]
  46af116 Add docstrings to key handler methods [Jeff MacDonald]
  b5ba922 Add docstrings to database.py functions [Jeff MacDonald]
  f645ffa Update spec: commit() now properly calls conn.commit() [Jeff MacDonald]
  4882cb9 Fix commit() to properly call conn.commit() [Jeff MacDonald]
  32e10cf Fix remaining issues: update() return type, commit() dead code, make_dsn() attribute check, parse_dsn() error handling, buildargs() mutable default, cursor() annotations. Move spec to handbook/specs/ [Jeff MacDonald]
  e15b306 Standardize error handling - return False on pool/conn errors, consistent return types [Jeff MacDonald]
  96b3e44 Fix SQL injection in update(), insert(), createrol() - use sql.Identifier() [Jeff MacDonald]
  f3c87de Lint database.py, add type annotations, add database.spec [Jeff MacDonald]
  f3518d4 Refactor key handlers into dict with private methods [Jeff MacDonald]
  98bb3cf Add custom key handler demo to listbox_next [Jeff MacDonald]
  3a51c07 Add custom_keys parameter for handling custom key callbacks; add data field to ListboxResult [Jeff MacDonald]
  640486b Fix KEY_HOME and KEY_END cursor positioning; use f-strings for all echo() calls [Jeff MacDonald]
  2dc2af2 Use {cursorup} for KEY_UP after redraw, simplify {cud} to no args (tag: v202602231454) [Jeff MacDonald]
  d655d52 Add onkey() return True/False for handled/not handled; add cursor movement {cud:1} after redrawing items [Jeff MacDonald]
  b51924f Add _terminal_state_stack_enabled flag for VT-compliant save/restore cursor behavior [Jeff MacDonald]
  4985c3d Fix cursor positioning and _display_item defaults [Jeff MacDonald]
  e052dd1 Update spec: highlight uses end='', document cursor handling [Jeff MacDonald]
  130fe23 Fix left border to use ' {vline} ' with adjusted contentwidth [Jeff MacDonald]
  eb4ca59 Set normalcolor and cic in demo for highlighting [Jeff MacDonald]
  f0474f8 Highlight current item after displaying box [Jeff MacDonald]
  9bf79d7 Remove extra echo() call that was adding blank lines [Jeff MacDonald]
  f96a5a6 Revert to contentwidth-3 for content area [Jeff MacDonald]
  3de8a3d Fix content area width: contentwidth-1 [Jeff MacDonald]
  80d03e6 Title box is 4 lines, middle border connects to content [Jeff MacDonald]
  bb02eee Fix title box bottom to use corners instead of tees [Jeff MacDonald]
  d1f9ee2 Fix middle border: rtee on left, ltee on right [Jeff MacDonald]
  c21049e Fix contentwidth-2 for inner content alignment [Jeff MacDonald]
  8511968 Fix hline width: contentwidth - 2 instead of +4 [Jeff MacDonald]
  b6a836f Update spec: leading space instead of trailing in border definitions [Jeff MacDonald]
  51d9556 Change trailing space to leading space in border functions [Jeff MacDonald]
  632f630 Update spec: add hline to constructor, fix contentwidth-3 [Jeff MacDonald]
  ea1220d Fix contentwidth in _display_item, move hline to constructor [Jeff MacDonald]
  77dd655 Add _display_top_border, update spec with border functions [Jeff MacDonald]
  a9d9cc1 Rename _display_content_top to _display_middle_border [Jeff MacDonald]
  3729551 Rename _display_content_bottom to _display_bottom_border [Jeff MacDonald]
  2e91deb Update spec Height Calculation with f-string border definitions [Jeff MacDonald]
  e5b8a44 Fix echo calls - remove end='' for display, keep for bell [Jeff MacDonald]
  633c0d5 Add demo_listbox_next_static demo [Jeff MacDonald]
  3284138 Implement listbox_next module from spec [Jeff MacDonald]
  9a88713 Add onkey method to Listbox class, move all key handling into it [Jeff MacDonald]
## 2026-02-22
  451327e Reorder ListboxResult with status first, item defaults to None [Jeff MacDonald]
  67b9985 Add ListboxResult NamedTuple for structured return values [Jeff MacDonald]
  750db5d Use echo_command syntax for savecursor/restorecursor [Jeff MacDonald]
  a4847ab Add savecursor after prompt, restorecursor on item selection [Jeff MacDonald]
  0df1aea Rename cic dict to itemcolors [Jeff MacDonald]
  e44bbcd Add io.setvar() calls for cic echovar [Jeff MacDonald]
  153d1e5 Document cic as a dict for item color states [Jeff MacDonald]
  b16c94a Use 'enabled' instead of 'non-disabled' throughout [Jeff MacDonald]
  f390d2c Use 'enabled' instead of 'non-disabled' in KEY_END [Jeff MacDonald]
  de5d8ec Add cic echovar for current item color [Jeff MacDonald]
  8ec7bec Add listbox_next widget specification [Jeff MacDonald]
  bfe1b3f listbox: add compose() method and multi-line support [Jeff MacDonald]
## 2026-02-21
  1b1f3ac Sync spec with asimov.io: add register_emojis section and unicode codepoints [Jeff MacDonald]
  5091cb6 Sync emoji comments with asimov.io format [Jeff MacDonald]
  04be0de Add register_emojis, move empyre emojis to project [Jeff MacDonald]
  5f30f93 Mark emoji table as sample in echo_commands.spec [Jeff MacDonald]
  9106663 Implement literal braces {{ and }} in bbsengine6.io.echo [Jeff MacDonald]
## 2026-02-19
  74f0d02 io: add type annotations to input functions (tag: v202602211051) [Jeff MacDonald]
  1fdcc6e io: sync spec files from asimov [Jeff MacDonald]
  92eb250 build: disable gitlab push in release target [Jeff MacDonald]
  a51e7bc io: update inputstring and core modules from asimov (tag: v202602192015) [Jeff MacDonald]
  5c6f934 bbsengine6/io: refactored getch, added getstr, updated common/echo/inputstring/util [Jeff MacDonald]
## 2026-02-13
  c8a78f3 - bbsengine6/io/screen.py: fixed a bug in init() regarding the 'args' argument and a default value [Jeff MacDonald]
## 2026-01-08
  7643a65 - bbsengine6/sql: renamed sigview to folderview [Jeff MacDonald]
## 2025-12-24
  cb1de2c - bbsengine6: renamed sig.sql to folder.sql [Jeff MacDonald]
  e7625ff - bbsengine6: added php/bootstrap.php [Jeff MacDonald]
## 2025-12-14
  5b33036 - bbsengine6/io/screen.py: copied from asimov/io/ [Jeff MacDonald]
  6183f21 - bbsengine6/io/echo.py:   * fixed cuu, cud, cuf, cub ('repeat' was being handled wrong)   * added start of literalopen/close handling. does not work yet.   * added 'settitle' echo command   * changed tokenize() to accept **kwargs   * changed terminal_state to a single instance instead of a list   * decsc and decrc update internal vars   * added 'level' as kwarg to echo(). calls common.logentry(). sets up a prefix which uses echo vars level.info, level.debug, etc   * added rendered_length() which is used by inputstring() for displaying the prompt and positioning the cursor correctly. [Jeff MacDonald]
  038290d - bbsengine6/io/inputstring.py:   * added/removed/updated comments   * if trying to move left when curpos is 0, ring the bell.   * if trying to move right when curpos is at the end of buffer, ring the bell   * yank has been written but not tested   * if verify() fails, call refresh_input_view()   * updated handle_tab_manager()   * added oldvalue as 2nd positional arg of inputstring() [Jeff MacDonald]
  51d718e - bbsengine6/io/terminal.py:   * added size(), columns(), and lines()   * height and width are now aliases   * commented out title() (it is now an echo command, and commenting this out fixed a circular ref with .echo)   * removed savecursor() [Jeff MacDonald]
  7530775 - bbsengine6/io/inputinteger.py: cast oldvalue to str [Jeff MacDonald]
  0f57894 - bbsengine6/io/getch.py: added **kwargs for future use [Jeff MacDonald]
  3681511 - bbsengine6/io/const.py: added OSC (terminal title, amongst other functions), MAX_TERMINAL_WIDTH, and FALLBACK_TERMINAL_WIDTH [Jeff MacDonald]
  bca3395 - bbsengine6/io/common.py: moved terminal_size(), terminal_columns(), and terminal_lines() into io/screen.py [Jeff MacDonald]
  e1c7baf - bbsengine6/io/__init__.py: split the input functions and their support into separate files [Jeff MacDonald]
## 2025-12-07
  f7a4808 - bbsengine6/io/inputboolean.py: import echo() [Jeff MacDonald]
  50d87e0 - bbsengine6/io/inputchoice.py: import echo() and getch() [Jeff MacDonald]
  d4f8c26 - bbsengine6/io/__init__.py: import of getch() and commented out import of 'input' [Jeff MacDonald]
  8bff9ca - bbsengine6/io/getch.py: removed an extra blank line [Jeff MacDonald]
  8f9e437 - bbsengine6/io/: sync with asimov/io/ [Jeff MacDonald]
## 2025-12-05
  8003e3f - bbsengine6/common.py: fixed logentry() to behave better if a logging level is not in the table: use logging.NOTSET [Jeff MacDonald]
## 2025-12-03
  a80f101 - bbsengine6/io/echo.py:   * fixed a 'repeat bug' in cuu, cuf   * updated _handle_decstbm so it is properly 1-based   * fixed the 'reset top and bottom margins' feature   * fixed _handle_bel() typo (BEL vs BELL)   * fixed reset:all by clearing token.args   * {decstbm:1,1} can be shortened to {decstbm} (reset margins) [Jeff MacDonald]
  5f34923 - bbsengine6/io/: split up each function in input.py into their own files, updated __init__ to match. [Jeff MacDonald]
  2e4468d - bbsengine6/io/inputstring.py: fixed up whitespace issues [Jeff MacDonald]
## 2025-12-02
  03220e6 - bbsengine6/session.py: if no conn, check for a pool [Jeff MacDonald]
  f8078c2 - bbsengine6/io/keymap.py: copied from asimov/io/ [Jeff MacDonald]
  2a6e5a1 - bbsengine6/io/input.py: updated 'curdisplay' to use cha instead of cursorhpos [Jeff MacDonald]
  63d91d3 - bbsengine6/io/__init__.py: updated to use asimov's inputstring and echo [Jeff MacDonald]
  fa2e190 - bbsengine6/io/echo.py: changed 'bottombarcolor' and commented out a few print() calls [Jeff MacDonald]
  9cf05cc - added inputstring and util from asimov/io/ [Jeff MacDonald]
  55e71ce - bbsengine6/io/getch.py: copied from asimov/io/ [Jeff MacDonald]
## 2025-11-30
  4a7f721 no changes? [Jeff MacDonald]
  3cf5ff5 - copied asimov.io.common to bbsengine6 [Jeff MacDonald]
  831ef22 - bbsengine6/smarty/: added function.teos, modifier.markdown, and modifier.wpprop [Jeff MacDonald]
## 2025-11-29
  0810b17 - copied some bits of asimov.io into bbsengine6 (echo) [Jeff MacDonald]
  1196619 - bbsengine6/module.py: reworked by adding _check_params() helper and a 'for' loop to validate function signatures. added optional version() function in modules [Jeff MacDonald]
## 2025-10-29
  6bcdc21 updated README.md [Jeff MacDonald]
  e57e852 - updated [Jeff MacDonald]
  ebbe8d5 - updated [Jeff MacDonald]
  56f9170 - updated [Jeff MacDonald]
  ebc1445 updated README.md [Jeff MacDonald]
  8af11e5 removed README.md [Jeff MacDonald]
## 2025-10-28
  bc3632f - bbsengine6/listbox.py:   * default of this version is to use a database cursor (fetchpage)   * added some debugging using the bottombar   * added a typehint on 'prompt' arg to Listbox.handle() [Jeff MacDonald]
## 2025-10-08
  e06fc5b - bbsengine6/database.py: rewrite connect() [Jeff MacDonald]
  bc699a4 - bbsengine6/sql/:   * grant changes   * fixed whitespace issues [Jeff MacDonald]
## 2025-10-07
  185be72 - bbsengine6/util.py: copied logentry() from asimov [Jeff MacDonald]
## 2025-10-06
  a0863ca - bbsengine6/util.py: add **kwargs to getcurrentloginid() [Jeff MacDonald]
## 2025-05-30
  22a9e3d - bbsengine6/console/checkclasses.py: updated call to database.importsql() (tag: v202505302019) [Jeff MacDonald]
## 2025-05-28
  b6fda4e - bbsengine6/util.py:   * added strip_ansi() to help with wide character support   * serialize_datetimes() - steps through a nested dict called 'data' and converts any datetimes it finds to isoformat (str)   * load_sql() - Loads an SQL resource file and returns its contents as a string   * get_safe_path() - safely joins and normalizes path components   * getcurrentloginid() - returns system login id using os.getlogin() (tag: v202505302017, tag: v202505301857, tag: v202505301855, tag: v202505281954) [Jeff MacDonald]
  d6074f0 - bbsengine6/module.py: be sure to pass kwargs to access() [Jeff MacDonald]
  932ac86 - bbsengine6/sql/: added manage_database_priv.sql and manage_schema_priv.sql [Jeff MacDonald]
  30f3394 - bbsengine6/Makefile: added 'sql' and 'console' to 'clean' target [Jeff MacDonald]
## 2025-05-27
  6be5fc9 - bbsengine6/io/output.py: added strip_commands() for use by setbottombar() (tag: v202505281805, tag: v202505281759, tag: v202505281752, tag: v202505281732) [Jeff MacDonald]
  8b81d8c - bbsengine6/screen.py: setbottombar() rewrite [Jeff MacDonald]
  bd6b3d6 - bbsengine6/io/output.py: attempting to fix spurious \n while typing fast in getchinputstring(); failed patch attempting to handle emojis (wide characters) [Jeff MacDonald]
  10c16d4 - bbsengine6/io/input.py: changed display() to not repaint prompt+buffer unless it is different; tweaked some getch() timings [Jeff MacDonald]
## 2025-05-23
  f995831 - bbsengine6/module.py: pass **kwargs to module's access(); check 'silent' kwarg before certain output in check() [Jeff MacDonald]
## 2025-05-15
  dd7cfa7 - bbsengine6/io/input.py: commented out debugging in inputchoice() [Jeff MacDonald]
## 2025-05-14
  4766782 - bbsengine6/io/input.py: fixed special handling of ^U in getch() which fixed a glitch in inputstring(); updated inputchoice() with a new kwarg 'rewriteprompt' which colorizes the prompt in the de facto way, plus puts parens around the default option; **kw -> **kwargs; [Jeff MacDonald]
## 2025-05-13
  952a36f - bbsengin6/io/output.py: added letter prefixes in echo()'s 'level' for terminals without color [Jeff MacDonald]
## 2025-05-10
  f96629f - bbsengine6/console/checkroles.py: fixed indentation mistake that only created one role; changed buildargs() to return None [Jeff MacDonald]
## 2025-04-20
  a1bc5a9 - bbsengine6/sql/__init__.py: removed-- using MANIFEST.in instead (tag: v202504202158) [Jeff MacDonald]
  7a31dc1 - bbsengine6/MANIFEST.in: added [Jeff MacDonald]
  c981bca - bbsengine6/sql/: added __init__.py [Jeff MacDonald]
  131c5b4 - bbsengine6/setup.py: commented out 'py_modules' [Jeff MacDonald]
  716a73f - bbsengine6/setup.py: updated 'provides', 'packages', and 'classifiers' [Jeff MacDonald]
  3069c34 - moved 'sql' under bbsengine6 python package [Jeff MacDonald]
  34fc32d - bbsengine6/sql/upgrades.md: added [Jeff MacDonald]
  e016e2c - bbsengine6/io/input.py getch():   * rewrote code that handles ESC sequences (arrow keys, home, end, function keys, etc) which uses a while loop with a timeout instead of a for loop that reads up to five characters   * prevent busy wait by gradually increasing the time.sleep() at the bottom of the while loop starting at BASESLEEP increasing by 2% up to MAXSLEEP (phil)   * handle BSD (apple) non-blocking read failure gracefully [Jeff MacDonald]
  85ab95b - bbsengine6/sql/bbsengine6.sql:   * removed \sets for web, term, sysop   * added ltree, roles, tag, memberinet   * notify -> alert [Jeff MacDonald]
  1229cfc - bbsengine6/sql/fortune.sql: engine.blurb -> engine.__blurb [Jeff MacDonald]
## 2025-04-19
  a8ef5f1 - bbsengine6/sql/sigview.sql: added [Jeff MacDonald]
  7e312d8 - bbsengine6/sql/map_member_flag.sql: added [Jeff MacDonald]
  44ad7fa - bbsengine6/sql/blurbview.sql: added index, left joins renamed to be clearer; untested [Jeff MacDonald]
  d048657 - bbsengine6/sql/map_group_member.sql: id -> moniker; added index [Jeff MacDonald]
  519a4e7 - bbsengine6/sql/role.sql: removed [Jeff MacDonald]
  7e57d03 - bbsengine6/sql/map_sigop_sigpath.sql: added unique index [Jeff MacDonald]
  3bff07d - bbsengine6/sql/blocklist.sql: add 'unique' to 'address'; id->moniker [Jeff MacDonald]
  3f5b0cb - bbsengine6/sql/memberinet.sql: text -> citext [Jeff MacDonald]
  f4dc4ee - bbsengine6/sql/moderator.sql: text -> citext [Jeff MacDonald]
  23bf540 - bbsengine6/sql/moderator.sql: add an index (membermoniker, sigpath) id->moniker [Jeff MacDonald]
  1d6efd8 - bbsengine6/sql/blurb.sql: :web -> web, etc; text -> citext [Jeff MacDonald]
  bf8a9dc - bbsengine6/sql/extensions.sql: handled by bbsengine6.console [Jeff MacDonald]
  7fba876 - bbsengine6/sql/alert.sql: text -> citext, add a trigger to __alert [Jeff MacDonald]
  32cfd9c - bbsengine6/sql/checkflag.sql: if membermoniker is not null, return flag values. if membermoniker does not exist, return null [Jeff MacDonald]
  86d96dc - bbsengine6/sql/memberview.sql: added local time to dateapproved, dateupdated, datecreated, lastlogin [Jeff MacDonald]
  a72652e - bbsengine6/sql/flagdata.sql: commented out echo [Jeff MacDonald]
  b60be75 - bbsengine6/sql/flag.sql: text -> citext; commented out engine.map_blurb_flag; permissions [Jeff MacDonald]
  b40ca86 - bbsengine6/sql/manage_secondary_role.sql: add -> grant, remove -> revoke, add execute permission to sysop [Jeff MacDonald]
  017a29b - bbsengine6/sql/manage_role_privs.sql: updated permissions [Jeff MacDonald]
  e223401 - bbsengine6/sql/newuser.sql: no longer used [Jeff MacDonald]
  38b4451 - bbsengine6/sql/notify.sql: deleted [Jeff MacDonald]
  0f1f3c2 - bbsengine6/sql/roles.sql: commented out. this is done by firstboot [Jeff MacDonald]
  0bf5adb - con -> bbsengine6/console [Jeff MacDonald]
## 2025-04-18
  6b91536 - bbsengine6/sql/: added createrol.sql createschema.sql get_role_privs.sql getflags.sql grants.sql ltree.sql [Jeff MacDonald]
  17b501a - bbsengine6/sql/member.sql: memberid->membermoniker, added ui, tz, attrs, and refcode [Jeff MacDonald]
  3ad16cd - bbsengine6/sql/actionlog.sql: renamed activitylog to actionlog [Jeff MacDonald]
  fa915f1 - bbsengine6/sql/schema.sql: grant usage to web, term, sysop [Jeff MacDonald]
  de773fb - bbsengine6/sql/session.sql: added lastactivitylocal and expirylocal and memberid->membermoniker [Jeff MacDonald]
  c9a0183 - bbsengine6/sql/refcode.sql: s/text/citext/ [Jeff MacDonald]
## 2025-04-17
  f223f0c - bbsengine6/sql/buildsiguri.sql: rewrote from pl/pythonu to pl/pgsql [Jeff MacDonald]
  54a5e6d - bbsengine6/sql/subscribe.sql: s/memberid/membermoniker/ [Jeff MacDonald]
  8bf67e9 - bbsengine6/sql/sig.sql: updatedby, approvedby, createdby are now citext instead of bigint [Jeff MacDonald]
## 2025-04-15
  0633acc - bbsengine6/con/createdatabase.py: added [Jeff MacDonald]
  5f753ac - bbsengine6/con/main.py:   * 3 stages: stage_zero, stage_one, and the rest of main [Jeff MacDonald]
  9ac1204 - bbsengine6/con/lib.py: added check*() functions [Jeff MacDonald]
  1f34103 - bbsengine6/con/__main__.py: use io.echo() instead of print() [Jeff MacDonald]
  f964b40 - bbsengine6/con/member.py:   * kw -> kwargs   * pass kwargs to database functions   * setui() now accepts kwargs   * configurerole() works now   * add and edit of accounts works now [Jeff MacDonald]
  8426738 - bbsengine6/session.py:   * add '**kwargs' to all functions   * session.start() now has a _work(), and the function can make a database connection if it was passed a pool (standard)   * added garbagecollect() [Jeff MacDonald]
## 2025-03-17
  bedf2db - bbsengine6/io/output.py:   * in echo()'s level handling, remove 'var:' ahead of var names   * renamed vars.py to echovars.py   * set_terminal_background_color() and reset_terminal_background_color() [Jeff MacDonald]
  8fb077c - bbsengine6/io/__init__.py: whitespace? [Jeff MacDonald]
  9401567 - bbsengine6/io/const.py:   - added 'attributes' table (bold, faint, italic, underline, strike, and blink)   - added a few emojis   - merged 'bgcolors' table into 'colors'   - flattened 'colors' table to be a simple dict   - renamed RGB token to RGBCOLOR, command itself is the same [Jeff MacDonald]
  924facb - bbsengine6/io/input.py: added comments to CTRLKEYSEQ, allow \n or \r (raw mode) to return KEY_ENTER [Jeff MacDonald]
  9d3df11 - bbsengine6/io/echovars.py: added 'level.crit' var [Jeff MacDonald]
  530be1b - bbsengine6/con/check*.py: added [Jeff MacDonald]
  34f680a - con/session.py: **kw -> **kwargs, minor tweaks [Jeff MacDonald]
## 2025-03-16
  c51e24d - bbsengine6/module.py: added validate_function() to check annotations and return values [Jeff MacDonald]
  fe5b417 - bbsengine6/module.py: exception handling around calls to module functions; rename 'module' to 'modulename' [Jeff MacDonald]
  dd68c0d - ttyio/input.py: replaced getch() with an AI generated version [Jeff MacDonald]
## 2025-02-19
  054c40e - bbsengine6/handbook/module.md: added [Jeff MacDonald]
  053c5c1 - bbsengine6/handbook/: copied files from bbsengine5 [Jeff MacDonald]
## 2024-12-03
  a904b9b - bbsengine6/con/checksuperuser.py: added. checks for corret db privs for the current loginid [Jeff MacDonald]
## 2024-12-01
  c62278d - bbsengine6/con/checkextensions.py: added. checks for required extensions and installs them [Jeff MacDonald]
## 2024-11-26
  bed5739 - bbsengine6/util.py:   * upgraded to use context managed ('with') connections and cursors   * added getremoteaddr(), chop_last_element(), tobool(), ltree_to_path(), checksum()   * checkpassword() moved to member   * uses logging module for logentry() @ty ryan   * changed prototype for pluralize(), but no code changes (default values, type hints) [Jeff MacDonald]
## 2024-11-25
  8654508 - bbsengine6/screen.py: renamed setarea to setbottombar and converted to use f-strings [Jeff MacDonald]
  99e7b0f - bbsengine6/session.py: upgraded to use context managed connections and cursors (psycopg3) [Jeff MacDonald]
  d7f4f97 - bbsengine6/__init__.py: import init() from util [Jeff MacDonald]
## 2024-11-14
  770829c - bbsengine6/php/session.php:   * logentry -> \util\logentry   * encodejson -> \util\encodejson   * SYSTEMDSN -> \config\SYSTEMDSN [Jeff MacDonald]
  7160384 - bbsengine6/con/memberapproval.py: 'emailverified' and 'approved' flags moved to flags table [Jeff MacDonald]
  923db3e - bbsengine6/con/lib.py: remove 'bbs' role [Jeff MacDonald]
  b9b8259 - bbsengine6/con/session.py: @project:9627 - upgrade session submodule database calls and ttyio [Jeff MacDonald]
  d7e975b - bbsengine6/con/member.py: if email address changed, clear EMAILVERIFIED flag [Jeff MacDonald]
  70b6918 - bbsengine6/php/util.php: @project 9625 add util functions [Jeff MacDonald]
  216b475 - bbsengine6/php/database.php: upgraded to pdo [Jeff MacDonald]
  07c4165 - bbsengine6/sql/: 'grant' changes [Jeff MacDonald]
  fa2f0d4 - bbsengine6/sql/flagdata.sql: cosmetic changes (MAGIC and ASIMOV) [Jeff MacDonald]
## 2024-11-01
  1b3d86a - bbsengine6/sql/checkflag.sql: moniker and flag_name are now case insensitive; returns true, false, or null [Jeff MacDonald]
  6314bbb - bbsengine6/sql/checkflag.sql: added [Jeff MacDonald]
## 2024-10-31
  b9c5248 - bbsengine6/sql/manage_*.sql: @project:9609 add getpool(), cursor(), transaction(), createrol(), get_role_privs(), manage_secondary_role() [Jeff MacDonald]
  a9215c9 - bbsengine6/sql/flagdata.sql: removed 'draft', 'frozen', and 'junk'; added 'approved' and 'emailverified' [Jeff MacDonald]
## 2024-10-27
  2ad410b - bbsengine6/con/member.py:   * update to bbsengine6 (ttyio -> bbsengine.io)   * added editflags()   * added showui(), editui(), setui()   * added handling of required member fields moniker, loginid, email   * added handling of refcode   * added handling of e-mail address   * added configurerole()   * allow editing of members (not fully tested) [Jeff MacDonald]
  0cfcdc7 - bbsengine6/con/member.py and bbsengine6/con/alert.py: added [Jeff MacDonald]
  a91cb39 - bbsengine6/database.py:   * @project:9608 implement mogrifysql for psycopg3   * @project:9607 add parse_dsn and make_dsn which are not present in psycopg3   * @project:9609 add getpool(), cursor(), transaction(), createrol(), get_role_privs(), manage_secondary_role() [Jeff MacDonald]
  a9208a6 - bbsengine6/Makefile: added 'io' to clean target [Jeff MacDonald]
  1e3cbc2 - bbsengine6/con/main.py:   * renamed 'Quit' to 'Exit'   * added 'A' -- "Member Approval" option   * added call to session.start() and check it for errors and if so, return False   * from bbsengine6 import database [Jeff MacDonald]
  e0dc94b - bbsengine6/con/lib.py:   * fixed up lib.runmodule()   * changed call to setarea() to setbottombar()   * added checkroles()   * changed buildargs() so it calls database.buildargs() [Jeff MacDonald]
  b0ab120 - bbsengine6/con/Makefile: added *.pyc to 'clean' target [Jeff MacDonald]
  06c9a42 - bbsengine6/con/__init__.py: added __all__ which only helps with 'from con import *' [Jeff MacDonald]
  2664912 - bbsengine6/con/__main__.py: do not call session.start() [Jeff MacDonald]
## 2024-10-26
  30fa902 - bbsengine6/member.py: removed ' as txn' from database.transaction() calls [Jeff MacDonald]
  4d5d3a7 - bbsengine6/member.py:   * @project:9606 mark some bbsengine.member functions as readonly transactions; add bbsengine.database.transaction()   * in member.getflag() use 'moniker' instead of 'membermoniker' [Jeff MacDonald]
  ebcce38 - bbsengine6/member.py:   * @project:9100 upgrade to psycopg3 (optional asyncio)   * @project:9606 mark some bbsengine6.member functions as readonly   * handle 'ui' field as list, store as comma-separated text [Jeff MacDonald]
## 2024-10-14
  fcae98c - bbsengine6/database.py:   * @project 9587: add 'get_role_privs()' and 'manage_role_privs()'   * add 'manage_secondary_role()' [Jeff MacDonald]
  71fbe2b - bbsengine6: new screenshots of 'con' added [Jeff MacDonald]
## 2024-09-15
  82c73b8 - bbsengine6/skin/tmpl/topbar-notifycount.tmpl renamed to topbar-alertcount [Jeff MacDonald]
## 2024-09-12
  06df6ab - bbsengine6/php/libmember.php: added [Jeff MacDonald]
## 2024-08-11
  f3b26e2 - bbsengine6/sql/map_sigop_sigpath.sql: memberid->membermoniker [Jeff MacDonald]
## 2024-07-10
  67e2edc - bbsengine6/io/vars.py -> echovars.py [Jeff MacDonald]
## 2024-07-05
  bafc5d7 - bbsengine/io/terminal.py: updated width() such that MAXWIDTH is honored (clamp at 100, fe) (gitlab/main) [Jeff MacDonald]
## 2024-07-04
  0f8079d - bbsengine6/io/output.py:   * @project:9313 in logentry(), do not use hard-coded colors   * @project:9310 make many vars global (pos, wordwrap, indent) so they keep values between echo() calls   * @project:9305 io.echo() var references do not work   * commented out 'firstword' since it is unused   * on {{RESET}}, yield DECSTBM, SLASHALL, SPEED, INDENT, DECRC   * @project:9314 do not hard-code echo()'s level colors   * added tostr() [Jeff MacDonald]
  94148f6 - bbsengine6/util.py:   * @project:9307 fix hard-coded colors in heading()   * @project:9313 fix hard-coded colors in logentry()   * @project:9312 copy checkpassword() from bbsengine5   * databaseconnect -> database.connect() [Jeff MacDonald]
  f6f51f7 - @project:9307: do not hard-code colors used by util.heading() [Jeff MacDonald]
## 2024-06-17
  61b4474 - bbsengine6/con/main.py: updated for bbsengine6 [Jeff MacDonald]
  0deec98 - bbsengine6/con/__main__.py: updated to bbsengine6 [Jeff MacDonald]
  073e760 - bbsengine6/Makefile: added [Jeff MacDonald]
  0aa9521 - bbsengine6/skel/main.py: updated type hints [Jeff MacDonald]
  d5e46a3 - bbsengine6/skel/lib.py: minor tweaks (use PACKAGENAME, comment out database.buildargs() call) [Jeff MacDonald]
  65368c8 - bbsengine6/database.py:   * added postgres_to_python_list(), create(), createrol(), createschema()   * buildargdatabasegroup() -> buildargs()   * added --databaseschema   * changed update() to allow updating of the primarykey [Jeff MacDonald]
## 2024-05-16
  df8aef5 - bbsengine6/module.py:   * added 'silent' kwarg to check() so the 'module not found' error can be     squelched.  I need this for projectflow, which checks for module     availability.   * tweak f-strings and debugging echo() calls   * runmodule()'s debug now defaults to False [Jeff MacDonald]
## 2024-05-15
  616b92a - bbsengine6/skel/main.py: add commented out call to lib.buildargs() [Jeff MacDonald]
  a8d6df5 - bbsengine6/skel/__main__.py: call lib.buildargs() [Jeff MacDonald]
  32d97f3 - bbsengine6/src/skel/__init__.py: updated main() to call 'main' module [Jeff MacDonald]
## 2024-05-09
  e8d7fce - bbsengine6/py/src/ss,tk: copied from bbsengine5 [Jeff MacDonald]
## 2024-04-24
  9d6ad62 - bbsengine6/sql/blurb.sql: use 'moniker' (text) vs 'id' (bigint), update 'grant', and add 'flags' [Jeff MacDonald]
## 2024-04-17
  0041f40 - bbsengine6/screen.py: rewrote setarea() [Jeff MacDonald]
  2581cfa - bbsengine6/py/src/skel/lib.py: added buildargs() [Jeff MacDonald]
  3b13e57 - bbsengine6/py/src/skel/__main__.py: upgraded to bbsengine6 [Jeff MacDonald]
## 2024-04-16
  4f95d26 - bbsengine6/py/src/testemoji.py: step through emoji table [Jeff MacDonald]
## 2024-04-15
  b97dd65 - bbsengine6/py/src/testemoji.py: added [Jeff MacDonald]
## 2024-03-21
  ebbd2d3 - bbsengine6/input.py:   * project#8720: fixed crash by wrapping call to getdate() in a try/except, and also modified input.date() to check if getdate() returned None.   * updated to import bbsengine6 modules individually   * fixed verifyValidDateExpression() prototype so it accepts a buffer as first arg   * added "today" as a date expression   * ttyio.echo() -> io.echo() [Jeff MacDonald]
## 2024-03-17
  34bb667 - bbsengine6/py/src/skel/module.py: removed. [Jeff MacDonald]
## 2024-03-13
  37273c9 - bbsengine6/io/vars.py: added save() and restore() which is a stack like setarea() [Jeff MacDonald]
  7470bbd - bbsengine6/io/const.py: added 'shopping' emoji [Jeff MacDonald]
  3773620 - bbsengine6/io/__init__.py: added init() [Jeff MacDonald]
## 2024-03-06
  564e1f7 - bbsengine6/listbox.py: started on a feature to allow an item to be more than one line. [Jeff MacDonald]
## 2024-03-03
  e437f40 - bbsengine6/src/skel/: updated to modern standard [Jeff MacDonald]
  40eff1c - bbsengine6/io/output.py: added handling for {{indent}} command [Jeff MacDonald]
## 2024-03-01
  887c586 - bbsengine6/listbox.py:   * pass pagesize to Listbox constructor   * added handling of KEY_ENTER which returns a 'select' Op   * added handling of X, which returns an 'exit' Op   * if there are no items, return 'noitems' Op [Jeff MacDonald]
  27dc015 - bbsengine6/module.py: reload module if needed added to check() [Jeff MacDonald]
## 2024-02-17
  bf9a475 - bbsengine6/util.py: added getencryptedpassword(), updated pluralize() [Jeff MacDonald]
  d691bf2 - bbsengine6/member.py:   * ttyio -> io   * added 'tz' to member fields tuple   * updated f-strings   * added checksysop() -- checks for SYSOP flag. temp?   * fixed update(), by adding call to database.update() [Jeff MacDonald]
  0ce4385 - bbsengine6/__init__.py: commented out import statements which pull in *everything* by default [Jeff MacDonald]
## 2024-02-04
  ed9b289 - bbsengine6/io/terminal.py: clamp getterminalwidth() to MAXWIDTH [Jeff MacDonald]
## 2024-02-03
  c49846c - bbsengine6/database.py:   * clean up some debugging echo()s   * fixed a crasher in classexists() [Jeff MacDonald]
## 2024-01-12
  ee10642 - bbsengine6/screen.py: copied updateprogress() from bbsengine5 [Jeff MacDonald]
  c1fd2bd - bbsengine6/database.py: ttyio -> bbsengine.io [Jeff MacDonald]
  a044694 - bbsengine6/util.py: added 'timedelta' (3 weeks, 6 days) and added 'determiner' for when there is only one item ('a' vs 'an') [Jeff MacDonald]
  6d4b87a - bbsengine6/io/terminal.py: replace sys.stdout and sys.stdin with globals _streamout and _streamin [Jeff MacDonald]
  1904fe0 - bbsengine6/io/output.py: use new _streamout global instead of hard-coding sys.stdout [Jeff MacDonald]
  a6d43dd - bbsengine6/io/const.py: added 'desert' emoji [Jeff MacDonald]
  78610bd - bbsengine6/io/__init__.py: added aliases for terminal.columns and terminal.lines to keep BC [Jeff MacDonald]
## 2023-12-21
  c361565 - bbsengine6/util.py: getdate.getdate() -> bbsengine6.input.getdate [Jeff MacDonald]
  9f110be - bbsengine6/input.py: changed comment [Jeff MacDonald]
  5181972 - bbsengine6/listbox.py:   * cursorup on first item of page will go to previous page if it exists   * cursordown on last item of page will go to next page if it exists [Jeff MacDonald]
## 2023-12-14
  548fe9c - bbsengine6/listbox.py: added genericListboxItem class, untested [Jeff MacDonald]
## 2023-12-13
  d4b9754 - bbsengine6/sig.py: ttyio -> bbsengine.io [Jeff MacDonald]
  21ca53e - bbsengine6/util.py: ttyio -> bbsengine.io [Jeff MacDonald]
  1bf0862 - bbsengine6/screen.py: ttyio -> bbsengine.io [Jeff MacDonald]
## 2023-12-12
  9140511 - bbsengine6/py/src/setup.py: changed license and packages [Jeff MacDonald]
  02effbd - bbsengine6/io/Makefile: added [Jeff MacDonald]
  eaca65a - bbsengine6/listbox.py:   * ttyio -> io   * handle KEY_PAGEUP and KEY_PAGEDOWN [Jeff MacDonald]
  fd74e3b - testlistbox.py:   * moved Article2PresidentListboxItem from bbsengine6.listbox   * renamed setvariable() to setvar()   * added a query to get the total number of items   * renamed ttyio.echo to bbsengine6.io.echo   * changed title of listbox test [Jeff MacDonald]
## 2023-12-06
  85e0b2b - bbsengine6/__init__.py: added 'io' [Jeff MacDonald]
  47bc967 - bbsengine6/io/: copied from ttyio6 [Jeff MacDonald]
## 2023-12-05
  ef4b76a - bbsengine6/www/: mass commit [Jeff MacDonald]
  c41a50a - bbsengine6/www/com/config-prod.php: added [Jeff MacDonald]
  462d3d1 - bbsengine6/skin/: mass commit [Jeff MacDonald]
  b5bb2f4 - bbsengine6/www/php/Markdown*.php removed [Jeff MacDonald]
  e7ab3ea - bbsengine.org: copied www/Makefile [Jeff MacDonald]
## 2023-12-03
  a2bcbb3 - bbsengine6/input.py: fixed typo in getdate() [Jeff MacDonald]
  93eb0a2 - bbsengine6/util.py,input.py: moved inputfilename to input.py [Jeff MacDonald]
  ea65c4e - bbsengine6/listbox.py: added displayitems() to Listbox [Jeff MacDonald]
  c9f1b63 - bbsengine6/database.py: updated echo calls [Jeff MacDonald]
  a9fa43c - bbsengine6/input.py: new module. merged getdate3 [Jeff MacDonald]
  b951d31 - bbsengine6/menu.py: added some code that moves the cursor to the current item [Jeff MacDonald]
## 2023-11-30
  6269830 - py/src/testmenu.py: renamed 'setvariable()' to 'setvar()' (both work currently); commented out call to screen.init() and screen.setarea() [Jeff MacDonald]
## 2023-11-29
  dcd7b41 - bbsengine6/: added 'listbox' and 'input' submodules [Jeff MacDonald]
## 2023-11-26
  6585838 - bbsengine6.listbox.ListboxItem:   * changed _init to accept 'width'   * added a help() method - bbsengine6.listbox.Listbox:   * clamp self.terminalwidth to 100   * .display() no longer has a terminalwidth arg   * handling of KEY_ENTER diverted to callback   * renamed 'mi' to 'item' [Jeff MacDonald]
  ba01ed9 - bbsengine6.menu:  * merged code in listbox that properly colors the current item  * calculate terminalwidth and clamp it at 100 [Jeff MacDonald]
## 2023-11-25
  8c7f82c - bbsengine6/menu.py: changed prototype for __getitem__() [Jeff MacDonald]
## 2023-11-24
  fb8c558 - bbsengine6/listbox.py: modified menu to behave like a single-page listbox including a callback function to handle keys [Jeff MacDonald]
## 2023-11-01
  18ba88f - bbsengine6/py/src/test*.py: added back [Jeff MacDonald]
  74a3a67 - bbsengine6/py/src/con/session.py: added main() [Jeff MacDonald]
  980532f - bbsengine6/py/src/con/main.py: added 'S' option to list sessions [Jeff MacDonald]
  6b6ec9c - bbsengine6/menu.py: bare minimum change to introduce 'pagesize' [Jeff MacDonald]
## 2023-10-30
  bff050f - bbsengine6/form.py: added FormItemCheckbox, FormItemRadioButton, and FormItemTextBox [Jeff MacDonald]
  96917bd - bbsengine6/database.py: in buildarggroup(), new kwarg 'suppress' [Jeff MacDonald]
  e832a92 - bbsengine/util.py: changed inputfilename() so that 'verify' is part of kw, and passed through to ttyio.inputstring() [Jeff MacDonald]
  5fe1df1 - bbsengine6/menu.py: removed 'default' kwarg from handle() [Jeff MacDonald]
  51f5ceb - bbsengine6/module.py:   * check() now looks for 'main', 'buildargs', 'access', and 'init' in the module, and if any are missing returns False   * it also checks for proper argument names using the built-in 'inspect' module.   * buildargs() must always exist, and it is now allowed to return None [Jeff MacDonald]
  2e0e6c2 - bbsengine6/session.py:   * wrap some echo statements in 'if args.debug' checks   * when there is more than one session, the message displayed is now of level 'warn'   * commented out an echo used for debugging [Jeff MacDonald]
  c771b57 - bbsengine6/menu.py: 'X' option no longer has a module; wrap calls to screen.setarea() in an 'if debug' check; add a {/all} to remove some artifacts [Jeff MacDonald]
  4fd7ae1 - bbsengine6/php/engine.php:   * removed zoid6 specific choices from menu   * added a check to be sure $menu is not null before trying to sort it   * copied buildlabel() and normalizelabelpath() from bbsengine5 [Jeff MacDonald]
  77561ce - bbsengine6/php/session.php: tweeked debugging lines [Jeff MacDonald]
  d7e83a6 - bbsengine6/php/database.php: added disconnect() [Jeff MacDonald]
## 2023-10-27
  b686bf2 - bbsengine6/menu.py:   * removed extra {savecursor} call   * "X" is no longer handled by Menu() as special ("exit")   * added some screen.setarea() calls for debugging. these will eventually get wrapped into args.debug checks   * "enter" and "key" ops have been merged into "select" [Jeff MacDonald]
## 2023-10-26
  703d7b3 - bbsengine6/menu.py:   * finally got HOME, END, and wrapping working. tons of "off by one" problems [Jeff MacDonald]
## 2023-10-12
  061ae8e - bbsengine6/py/src/testmenu.py: added [Jeff MacDonald]
## 2023-09-29
  87a61b0 - bbsengine6/menu.py:   * moved form related items to form.py   * basically rewrote the Menu class   * Item is a new class   * Op is a NamedTuple [Jeff MacDonald]
  1f23c1d - bbsengine6/util.py: added 'inputfilename()', commented out some unused code, and added some debugging [Jeff MacDonald]
  53869fd - bbsengine6/__init__.py: added import of new 'menu' module [Jeff MacDonald]
## 2023-09-25
  28baaff - bbsengine6/util.py: copied inputfilename() from bbsengine5, added verify functions verifyFileExistsReadableWritable, verifyFileExistsReadable, and verifyDirExistsWritable [Jeff MacDonald]
  5b7ef68 - bbsengine6/py/src/testinputfilename.py: short test script for util.inputfilename() [Jeff MacDonald]
## 2023-09-24
  c446307 - bbsengine6/py/src/testinputfilename.py: added [Jeff MacDonald]
## 2023-09-09
  901b1af - bbsengine6/py/src/skel/: added skeleton code for a bbsengine6 module [Jeff MacDonald]
## 2023-09-04
  848f2df - bbsengine6/session.py: minor change to debugging f-string; return new value from set() [Jeff MacDonald]
## 2023-09-03
  f1bbfc8 - bbsengine6/sig.py: added getchsigcomplete(); renamed old completer (compat with readlin) to gnusigcomplete() [Jeff MacDonald]
## 2023-09-01
  e5c1d3a - bbsengine6/sig.py: added builduri(), builddict(), buildrec(), and get() [Jeff MacDonald]
## 2023-08-31
  5cd85f2 - bbsengine6/sql/getsubblurbs.sql: turns out I had already updated getsubnodes.sql to refer to blurbs but I never read the file. oops. [Jeff MacDonald]
  3aa8366 - bbsengine6/sql/getreplies.sql: renamed to getsubblurbs.sql [Jeff MacDonald]
  9ed7c3a - bbsengine6/sql/getreplies.sql: copied from socrates [Jeff MacDonald]
## 2023-08-29
  0c73f1e - bbsengine6/blurb,database,form: no idea what the changes were-- diff is empty [Jeff MacDonald]
  270cb21 - bbsengine6/editor.py:   * worked on .h (help)   * started on other dot commands [Jeff MacDonald]
  eada6ce - bbsengine/module.py:   * added a lot more debugging   * use more f-strings [Jeff MacDonald]
  8bf6c91 - bbsengine6/menu.py: fixed a typo in class Menu (extra curly brace) [Jeff MacDonald]
  0cf78a3 - bbsengine6/util.py: working on filedisplay(); in inputpassword(), accept a 'mask' kwarg and pass it to inputstring(); working on datestamp() so it shows timezone properly [Jeff MacDonald]
  d083e96 - bbsengine6/member.py: tweaked debugging echo() [Jeff MacDonald]
## 2023-08-05
  ac33ea4 - bbsengine6/src/con/main.py: changed the prompt a little [Jeff MacDonald]
  16abacd - bbsengine6/src/con/__main__.py: added call to bbsengine.session.start() [Jeff MacDonald]
  fb7e46f - bbsengine6/util.py:   * renamed 'title()' to 'heading()' and tweaked the code a little   * added collapserange(), expandrange(), rangestr(), and printr() for handling ranges like 1-42 (projectflow?)   * copied filedisplay() from bbsengine5   * copied diceroll() from bbsengine5 [Jeff MacDonald]
## 2023-08-04
  e2d9421 - bbsengine6/module.py: args.debug -> debug; changed runsubmodule() into a passthru, needs to be evaluated [Jeff MacDonald]
  df672dd - bbsengine6/screen.py: updated setarea() docs [Jeff MacDonald]
  d6b9d20 - bbsengine6/src/testsession.py,testeditor.py: added [Jeff MacDonald]
  99c8ba9 - bbsengine6.session   * added get(), set()   * fixed start()   * added garbagecollect()   * added buildsession() -> dict 'session'   * build(rec) -> dict 'session'   * garbagecollect() is only called in start() -- php has better knobs for the moment [Jeff MacDonald]
## 2023-08-02
  f81a68f - bbsengine6/editor.py: added an 'exit' command and handling of KEY_ENTER [Jeff MacDonald]
## 2023-08-01
  927e39e - bbsengine6/editor.py: added [Jeff MacDonald]
## 2023-07-17
  b299aa0 - bbsengine6/con/: added 'email', 'member', and 'session' submodules [Jeff MacDonald]
## 2023-06-27
  93af9fa - bbsengine6/screen.py: renamed ttyio.interpretecho() to ttyio.interpret() [Jeff MacDonald]
  dec1d40 - bbsengine6/session.py: added write(), get(), updatelastactivity(), start(), build() and currentsessionid [Jeff MacDonald]
  6112f8c - bbsengine6/py/src/setup.py: changed bbsengine6 license to GPLv2 from GPLv3. [Jeff MacDonald]
  30e6331 - bbsengine6/con/lib.py: added setarea() and runsubmodule(). [Jeff MacDonald]
  89b6dd4 - bbsengine6/con/main.py: added a menu that currently only accepts 'm' for member and calls the member submodule [Jeff MacDonald]
  344e9dc - bbsengine6/con/__main__.py: added some boilerplate that calls the 'main' submodule [Jeff MacDonald]
## 2023-06-08
  171e6f3 - bbsengine6/*.py: modified but no diff output?! [Jeff MacDonald]
  1dc0a37 - bbsengine6/member.py:   * renamed builddict() to buildrec() -- builds a cleaned dictionary for use in the databse (filter epoch fields, etc)   * added build() which builds a member dictionary from a database record   * changed getcurrentid() so it uses os.getlogin(), which is cross platform vs pwd, which does not work on windowsks   * added getbymoniker()   * copied setflag(), getflag(), updateflag(), and checkflag() from bbsengine5   * added setpassword()   * added setattributes()   * copied verifyMemberNotFound and verifyMemberFound from bbsengine5   * added insert()   * commented out import of 'pwd' [Jeff MacDonald]
## 2023-05-26
  b2fe05e - bbsengine6/sql/member.sql: rename 'name' to 'moniker', added a 'not null' to 'email', and removed 'shell' [Jeff MacDonald]
## 2023-05-23
  7f2638c - bbsengine6/sql/: replaced references to 'apache' and 'www-data' with the psql var 'web' which is set by bbsengine6.sql [Jeff MacDonald]
  a7c75dd - bbsengine6/sql/node.sql: renamed to blurb.sql [Jeff MacDonald]
## 2023-05-15
  f7a63d4 - bbsengine6/Makefile: added [Jeff MacDonald]
  f823cec - bbsengine6.database: added resultiter from bbsengine5 [Jeff MacDonald]
## 2023-05-14
  9bbe777 - bbsengine6/py/src/Makefile: added [Jeff MacDonald]
  0d9ab44 - bbsengine6/py/src/setup.py: updated [Jeff MacDonald]
  2af0759 - bbsengine6/py/src/bbsengine6/: added [Jeff MacDonald]
## 2023-05-02
  5ef86a1 - bbsengined6/py/src/con/: added some code to __main__ [Jeff MacDonald]
## 2023-04-30
  a7ebd7e - bbsengine6/py/src/con/Makefile: added [Jeff MacDonald]
  3d86d8e - bbsengine6/py/src/setup.py: configured for bbsengine6 including 'con' [Jeff MacDonald]
  cac3ca5 - bbsengine6/py/src/Makefile: added [Jeff MacDonald]
  78f65b3 - bbsengine6/py/src/setup.py: copied from bbsengine5 [Jeff MacDonald]
  f5b080f - bbsengine6/py/src/con/: added [Jeff MacDonald]
## 2023-04-28
  1c17a3d - bbsengine6/sql/mantra.sql: renamed to fortune.sql [Jeff MacDonald]
## 2023-04-21
  581ad43 - bbsengine6/sql/nodeview.sql -> blurbview.sql [Jeff MacDonald]
## 2023-04-17
  42f9fe0 - bbsengine6/skin/tmpl/notify.tmpl: some quick edits [Jeff MacDonald]
## 2023-04-15
  755d00b - bbsengine6/www/: copied htaccess-prod, config-prod, htpasswd-prod, Makefiles, and bbsenginedotorg.sql from bbsengine5 [Jeff MacDonald]
## 2023-04-14
  6219037 - bbsengine6/php/engine.php: renamed displaypage() arg from 'kw' to 'data' [Jeff MacDonald]
  ceac73c - bbsengine6/php/database.php: use proper namespace for logentry() call [Jeff MacDonald]
  4ba09e0 - bbsengine6/php/Input*.php: added [Jeff MacDonald]
  229d15f - rewrote most of \bbsengine6\session - added insert() and update() - if a read fails, insert it as a new session - write() updated to use insert() - there is no update() yet - added a few calls to \bbsengine6\logentry() to track which of my functions are being called by php - changed validate() to return true only if the session has not expired [Jeff MacDonald]
  dc0b9b4 - copied php, skin, and smarty from bbsengine5 [Jeff MacDonald]
## 2023-04-13
  4e298d5 - bbsengine6/js/query.smoothState.js: copied from zoidweb4 [Jeff MacDonald]
  53494e7 - bbsengine6/www/js/bbsengine6.js: moved to 'js' so it can be installed to engine.zoid [Jeff MacDonald]
## 2023-04-11
  fb6a305 - bbsengine6/www/php/index.php: ported to bbsengine6, set some blurb data to null so the templates will work [Jeff MacDonald]
## 2023-04-09
  98f911e - bbsengine6/js/: copied from bbsengine5/js/ [Jeff MacDonald]
## 2023-04-06
  0aff6d6 - bbsengine6/sql/newuser.sql: removed 'finn' role [Jeff MacDonald]
  8479405 - bbsengine6/sql/role.sql: removed 'finn' role [Jeff MacDonald]
## 2023-04-05
  b2ef94e - bbsengine6/sql/bbsengine5.sql: renamed to bbsengine6.sql [Jeff MacDonald]
  0d6b311 - bbsengine6/sql/: copied from bbsengine5 [Jeff MacDonald]
## 2023-04-04
  639957f - bbsengine6/skin/: copied from bbsengine5/skin/ [Jeff MacDonald]
## 2023-04-03
  005f904 - bbsengine6/php/: added modules session, database, and engine [Jeff MacDonald]
  6460d91 - bbsengine6/php/Makefile: added 'stage' target [Jeff MacDonald]
  0f6d8c2 - bbsengine6/www/js/: copied from bbsengine5 [Jeff MacDonald]
## 2023-04-02
  4c190bb - bbsengine6/: added Makefile and php/Makefile [Jeff MacDonald]
  e395fcd - bbsengine6/php/database.php: switched out MDB2 for PDO [Jeff MacDonald]
  382168a - bbsengine6/php/: added database, session, and engine [Jeff MacDonald]
  d09125c - bbsengine6/README.md: updated [Jeff MacDonald]
## 2022-08-24
  f843f5d bbsengine6/README.md: added. [Jeff MacDonald]
