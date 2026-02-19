
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
