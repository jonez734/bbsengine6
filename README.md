bbsengine6
==========

dependencies
------------

- postgresql
- bbsengine6
- python3
- php8.1
- apache2
- PEAR package: html_quickform2

changes
-------

- biggest changes are a move to php8.1 from php7 and from PEAR::MDB2 to PDO
- reorganized files
    * bbsengine.org is now stored in bbsengine6/www/org/
    * module files (database, session, etc) get installed to /srv/www/bbsengine6/php/
    * skin templates are installed outside the DOCROOT-- be sure config-prod.php is accurate
    * new top-level 'handbook' dir, with a stripped down Makefile
- custom session handler
    * rewritten
    * stores as json for cross-platform
    * namespace \bbsengine6\session
