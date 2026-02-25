<?php

/*
 * @since 20230409
 */
$includepath = get_include_path().":/srv/www/zoid6/php/:/srv/www/bbsengine6/php/:/srv/www/smarty/";
if (set_include_path($includepath) === false)
{
    print("include path fail");
}

//require_once("zoid6.php");

define("SITETITLE", "bbsengine6 official website");
define("SITEADMINEMAIL", "zoid zechnologies <bbsengine@projects.zoidtechnologies.com>");

define("STATICSKINURL", "https://bbsengine.org/skin/");
/**
 * define the base url for the site. THIS VALUE MUST BE TERMINATED WITH A "/"
 */
define("SITEURL", "https://bbsengine.org/");
define("SITENAME", "bbsenginedotorg");
define("SKINURL", SITEURL . "skin/");
define("config\SYSTEMDSN", "pgsql:host=127.0.0.1;port=5432;dbname=zoid6");

define("config\VHOSTDIR", "/srv/www/vhosts/www.bbsengine.org/");
define("config\DOCUMENTROOT", \config\VHOSTDIR . "html/");

//define("ZOIDWEBDIR", "/srv/www/zoid6/");

define("config\SMARTYCOMPILEDTEMPLATESDIR", \config\VHOSTDIR."templates_c");
define("config\SMARTYPLUGINSDIR", [ 0 => \config\VHOSTDIR."smarty/"]);
//define("SMARTYTEMPLATESDIR", [ 0 => DOCUMENTROOT."skin/tmpl/", 1 => ZOIDWEBDIR."skin/tmpl/", 2 => "/srv/www/bbsengine6/skin/tmpl/"]);
define("config\SMARTYTEMPLATESDIR", [ 0 => \config\DOCUMENTROOT."skin/tmpl/", 1 => "/srv/www/bbsengine6/skin/tmpl/"]);

// @see http://php.net/strftime
define("DATEFORMAT", "%Y-%b-%d %I:%M %p %Z (%A)");

define("config\LOGENTRYPREFIX", "bbsenginedotorg");

define("RELEASESDIR", "/srv/repo/");

/**
 * @since 20110817
 */
define("ARCHIVEURL", "/archive/");

/**
 * @since 20140511
 */
define("REPOURL", "https://repo.zoidtechnologies.com/");

date_default_timezone_set("America/New_York");

define("CURRENTVERSION", "6");

define("config\HANDBOOKDIR", \config\DOCUMENTROOT."handbook/");
define("config\HANDBOOKURI", "/handbook/");

define("config\CURRENTHANDBOOKURI", \config\HANDBOOKURI."current/");

define("config\APIDOCSDIR", \config\HANDBOOKDIR . CURRENTVERSION . "/api/");
define("config\APIDOCSURI", \config\HANDBOOKURI . CURRENTVERSION . "/api/");

define("config\CHANGELOG", \config\HANDBOOKURI . "CHANGELOG.txt");
define("config\README", \config\HANDBOOKURI . "README.txt");
define("config\INSTALL", \config\HANDBOOKURI . "INSTALL.txt");
define("config\RELEASENOTES", \config\HANDBOOKURI . "RELEASENOTES.txt");

define("PROJECTURL", "https://projects.zoidtechnologies.com/");

define("ENGINEURL", "/engine/");

// @since 20180502 to squash a php notice
define("WWWURL", "//zoidtechnologies.com/");

// define("APIDOCSURI", "");
/**
 * @since 20190223
*/

define("config\SESSIONCOOKIEDOMAIN", ".bbsengine.org");
define("config\SESSIONCOOKIEEXPIRE", 12*60*60);
define("config\SESSIONCOOKIEPATH", "/");
define("config\SESSIONNAME", "bbsenginedotorgsession");

// @since 20230409
define("CURRENTPROJECTNAME", "bbsengine6");


?>
