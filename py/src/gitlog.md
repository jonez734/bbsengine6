
## 2022-08-24
 * bbsengine6/README.md: added. (Jeff MacDonald)

## 2023-04-02
 * - bbsengine6/README.md: updated (Jeff MacDonald)
 * - bbsengine6/php/: added database, session, and engine (Jeff MacDonald)
 * - bbsengine6/php/database.php: switched out MDB2 for PDO (Jeff MacDonald)
 * - bbsengine6/: added Makefile and php/Makefile (Jeff MacDonald)

## 2023-04-03
 * - bbsengine6/www/js/: copied from bbsengine5 (Jeff MacDonald)
 * - bbsengine6/php/Makefile: added 'stage' target (Jeff MacDonald)
 * - bbsengine6/php/: added modules session, database, and engine (Jeff MacDonald)

## 2023-04-04
 * - bbsengine6/skin/: copied from bbsengine5/skin/ (Jeff MacDonald)

## 2023-04-05
 * - bbsengine6/sql/: copied from bbsengine5 (Jeff MacDonald)
 * - bbsengine6/sql/bbsengine5.sql: renamed to bbsengine6.sql (Jeff MacDonald)

## 2023-04-06
 * - bbsengine6/sql/role.sql: removed 'finn' role (Jeff MacDonald)
 * - bbsengine6/sql/newuser.sql: removed 'finn' role (Jeff MacDonald)

## 2023-04-09
 * - bbsengine6/js/: copied from bbsengine5/js/ (Jeff MacDonald)

## 2023-04-11
 * - bbsengine6/www/php/index.php: ported to bbsengine6, set some blurb data to null so the templates will work (Jeff MacDonald)

## 2023-04-13
 * - bbsengine6/www/js/bbsengine6.js: moved to 'js' so it can be installed to engine.zoid (Jeff MacDonald)
 * - bbsengine6/js/query.smoothState.js: copied from zoidweb4 (Jeff MacDonald)

## 2023-04-14
 * - copied php, skin, and smarty from bbsengine5 (Jeff MacDonald)
 * - rewrote most of bsengine6\session - added insert() and update() - if a read fails, insert it as a new session - write() updated to use insert() - there is no update() yet - added a few calls to bsengine6\logentry() to track which of my functions are being called by php - changed validate() to return true only if the session has not expired (Jeff MacDonald)
 * - bbsengine6/php/Input*.php: added (Jeff MacDonald)
 * - bbsengine6/php/database.php: use proper namespace for logentry() call (Jeff MacDonald)
 * - bbsengine6/php/engine.php: renamed displaypage() arg from 'kw' to 'data' (Jeff MacDonald)

## 2023-04-15
 * - bbsengine6/www/: copied htaccess-prod, config-prod, htpasswd-prod, Makefiles, and bbsenginedotorg.sql from bbsengine5 (Jeff MacDonald)

## 2023-04-17
 * - bbsengine6/skin/tmpl/notify.tmpl: some quick edits (Jeff MacDonald)

## 2023-04-21
 * - bbsengine6/sql/nodeview.sql -> blurbview.sql (Jeff MacDonald)

## 2023-04-28
 * - bbsengine6/sql/mantra.sql: renamed to fortune.sql (Jeff MacDonald)

## 2023-04-30
 * - bbsengine6/py/src/con/: added (Jeff MacDonald)
 * - bbsengine6/py/src/setup.py: copied from bbsengine5 (Jeff MacDonald)
 * - bbsengine6/py/src/Makefile: added (Jeff MacDonald)
 * - bbsengine6/py/src/setup.py: configured for bbsengine6 including 'con' (Jeff MacDonald)
 * - bbsengine6/py/src/con/Makefile: added (Jeff MacDonald)

## 2023-05-02
 * - bbsengined6/py/src/con/: added some code to __main__ (Jeff MacDonald)

## 2023-05-14
 * - bbsengine6/py/src/bbsengine6/: added (Jeff MacDonald)
 * - bbsengine6/py/src/setup.py: updated (Jeff MacDonald)
 * - bbsengine6/py/src/Makefile: added (Jeff MacDonald)

## 2023-05-15
 * - bbsengine6.database: added resultiter from bbsengine5 (Jeff MacDonald)
 * - bbsengine6/Makefile: added (Jeff MacDonald)

## 2023-05-23
 * - bbsengine6/sql/node.sql: renamed to blurb.sql (Jeff MacDonald)
 * - bbsengine6/sql/: replaced references to 'apache' and 'www-data' with the psql var 'web' which is set by bbsengine6.sql (Jeff MacDonald)

## 2023-05-26
 * - bbsengine6/sql/member.sql: rename 'name' to 'moniker', added a 'not null' to 'email', and removed 'shell' (Jeff MacDonald)

## 2023-06-08
 * - bbsengine6/member.py:   * renamed builddict() to buildrec() -- builds a cleaned dictionary for use in the databse (filter epoch fields, etc)   * added build() which builds a member dictionary from a database record   * changed getcurrentid() so it uses os.getlogin(), which is cross platform vs pwd, which does not work on windowsks   * added getbymoniker()   * copied setflag(), getflag(), updateflag(), and checkflag() from bbsengine5   * added setpassword()   * added setattributes()   * copied verifyMemberNotFound and verifyMemberFound from bbsengine5   * added insert()   * commented out import of 'pwd' (Jeff MacDonald)
 * - bbsengine6/*.py: modified but no diff output?! (Jeff MacDonald)

## 2023-06-27
 * - bbsengine6/con/__main__.py: added some boilerplate that calls the 'main' submodule (Jeff MacDonald)
 * - bbsengine6/con/main.py: added a menu that currently only accepts 'm' for member and calls the member submodule (Jeff MacDonald)
 * - bbsengine6/con/lib.py: added setarea() and runsubmodule(). (Jeff MacDonald)
 * - bbsengine6/py/src/setup.py: changed bbsengine6 license to GPLv2 from GPLv3. (Jeff MacDonald)
 * - bbsengine6/session.py: added write(), get(), updatelastactivity(), start(), build() and currentsessionid (Jeff MacDonald)
 * - bbsengine6/screen.py: renamed ttyio.interpretecho() to ttyio.interpret() (Jeff MacDonald)

## 2023-07-17
 * - bbsengine6/con/: added 'email', 'member', and 'session' submodules (Jeff MacDonald)

## 2023-08-01
 * - bbsengine6/editor.py: added (Jeff MacDonald)

## 2023-08-02
 * - bbsengine6/editor.py: added an 'exit' command and handling of KEY_ENTER (Jeff MacDonald)

## 2023-08-04
 * - bbsengine6.session   * added get(), set()   * fixed start()   * added garbagecollect()   * added buildsession() -> dict 'session'   * build(rec) -> dict 'session'   * garbagecollect() is only called in start() -- php has better knobs for the moment (Jeff MacDonald)
 * - bbsengine6/src/testsession.py,testeditor.py: added (Jeff MacDonald)
 * - bbsengine6/screen.py: updated setarea() docs (Jeff MacDonald)
 * - bbsengine6/module.py: args.debug -> debug; changed runsubmodule() into a passthru, needs to be evaluated (Jeff MacDonald)

## 2023-08-05
 * - bbsengine6/util.py:   * renamed 'title()' to 'heading()' and tweaked the code a little   * added collapserange(), expandrange(), rangestr(), and printr() for handling ranges like 1-42 (projectflow?)   * copied filedisplay() from bbsengine5   * copied diceroll() from bbsengine5 (Jeff MacDonald)
 * - bbsengine6/src/con/__main__.py: added call to bbsengine.session.start() (Jeff MacDonald)
 * - bbsengine6/src/con/main.py: changed the prompt a little (Jeff MacDonald)

## 2023-08-29
 * - bbsengine6/member.py: tweaked debugging echo() (Jeff MacDonald)
 * - bbsengine6/util.py: working on filedisplay(); in inputpassword(), accept a 'mask' kwarg and pass it to inputstring(); working on datestamp() so it shows timezone properly (Jeff MacDonald)
 * - bbsengine6/menu.py: fixed a typo in class Menu (extra curly brace) (Jeff MacDonald)
 * - bbsengine/module.py:   * added a lot more debugging   * use more f-strings (Jeff MacDonald)
 * - bbsengine6/editor.py:   * worked on .h (help)   * started on other dot commands (Jeff MacDonald)
 * - bbsengine6/blurb,database,form: no idea what the changes were-- diff is empty (Jeff MacDonald)

## 2023-08-31
 * - bbsengine6/sql/getreplies.sql: copied from socrates (Jeff MacDonald)
 * - bbsengine6/sql/getreplies.sql: renamed to getsubblurbs.sql (Jeff MacDonald)
 * - bbsengine6/sql/getsubblurbs.sql: turns out I had already updated getsubnodes.sql to refer to blurbs but I never read the file. oops. (Jeff MacDonald)

## 2023-09-01
 * - bbsengine6/sig.py: added builduri(), builddict(), buildrec(), and get() (Jeff MacDonald)

## 2023-09-03
 * - bbsengine6/sig.py: added getchsigcomplete(); renamed old completer (compat with readlin) to gnusigcomplete() (Jeff MacDonald)

## 2023-09-04
 * - bbsengine6/session.py: minor change to debugging f-string; return new value from set() (Jeff MacDonald)

## 2023-09-09
 * - bbsengine6/py/src/skel/: added skeleton code for a bbsengine6 module (Jeff MacDonald)

## 2023-09-24
 * - bbsengine6/py/src/testinputfilename.py: added (Jeff MacDonald)

## 2023-09-25
 * - bbsengine6/py/src/testinputfilename.py: short test script for util.inputfilename() (Jeff MacDonald)
 * - bbsengine6/util.py: copied inputfilename() from bbsengine5, added verify functions verifyFileExistsReadableWritable, verifyFileExistsReadable, and verifyDirExistsWritable (Jeff MacDonald)

## 2023-09-29
 * - bbsengine6/__init__.py: added import of new 'menu' module (Jeff MacDonald)
 * - bbsengine6/util.py: added 'inputfilename()', commented out some unused code, and added some debugging (Jeff MacDonald)
 * - bbsengine6/menu.py:   * moved form related items to form.py   * basically rewrote the Menu class   * Item is a new class   * Op is a NamedTuple (Jeff MacDonald)

## 2023-10-12
 * - bbsengine6/py/src/testmenu.py: added (Jeff MacDonald)

## 2023-10-26
 * - bbsengine6/menu.py:   * finally got HOME, END, and wrapping working. tons of "off by one" problems (Jeff MacDonald)

## 2023-10-27
 * - bbsengine6/menu.py:   * removed extra {savecursor} call   * "X" is no longer handled by Menu() as special ("exit")   * added some screen.setarea() calls for debugging. these will eventually get wrapped into args.debug checks   * "enter" and "key" ops have been merged into "select" (Jeff MacDonald)

## 2023-10-30
 * - bbsengine6/php/database.php: added disconnect() (Jeff MacDonald)
 * - bbsengine6/php/session.php: tweeked debugging lines (Jeff MacDonald)
 * - bbsengine6/php/engine.php:   * removed zoid6 specific choices from menu   * added a check to be sure $menu is not null before trying to sort it   * copied buildlabel() and normalizelabelpath() from bbsengine5 (Jeff MacDonald)
 * - bbsengine6/menu.py: 'X' option no longer has a module; wrap calls to screen.setarea() in an 'if debug' check; add a {/all} to remove some artifacts (Jeff MacDonald)
 * - bbsengine6/session.py:   * wrap some echo statements in 'if args.debug' checks   * when there is more than one session, the message displayed is now of level 'warn'   * commented out an echo used for debugging (Jeff MacDonald)
 * - bbsengine6/module.py:   * check() now looks for 'main', 'buildargs', 'access', and 'init' in the module, and if any are missing returns False   * it also checks for proper argument names using the built-in 'inspect' module.   * buildargs() must always exist, and it is now allowed to return None (Jeff MacDonald)
 * - bbsengine6/menu.py: removed 'default' kwarg from handle() (Jeff MacDonald)
 * - bbsengine/util.py: changed inputfilename() so that 'verify' is part of kw, and passed through to ttyio.inputstring() (Jeff MacDonald)
 * - bbsengine6/database.py: in buildarggroup(), new kwarg 'suppress' (Jeff MacDonald)
 * - bbsengine6/form.py: added FormItemCheckbox, FormItemRadioButton, and FormItemTextBox (Jeff MacDonald)
