<?php

/*
 * @since 20230409
 */
$includepath = get_include_path().":/srv/www/zoid6/php/:/srv/www/bbsengine6/php/:/srv/www/smarty/";
if (set_include_path($includepath) === false)
{
    print("include path fail");
}

require_once("zoid6.php");

define("SITETITLE", "bbsengine6 official website");
define("SITEADMINEMAIL", "zoid zechnologies <bbsengine@projects.zoidtechnologies.com>");

define("STATICSKINURL", "https://bbsengine.com/skin/");
/**
 * define the base url for the site. THIS VALUE MUST BE TERMINATED WITH A "/"
 */
define("SITEURL", "https://bbsengine.com/");
define("SITENAME", "bbsenginedotcom");
define("SKINURL", SITEURL . "skin/");
define("SYSTEMDSN", \zoid6\SYSTEMDSN); // "pgsql:host=127.0.0.1;port=5432;dbname=zoid6");

define("VHOSTDIR", "/srv/www/vhosts/www.bbsengine.com/");
define("DOCUMENTROOT", VHOSTDIR . "html/");

define("ZOIDWEBDIR", "/srv/www/zoid6/");

define("SMARTYCOMPILEDTEMPLATESDIR", VHOSTDIR."templates_c");
define("SMARTYPLUGINSDIR", [ 0 => VHOSTDIR."smarty/"]);
define("SMARTYTEMPLATESDIR", [ 0 => DOCUMENTROOT."skin/tmpl/", 1 => ZOIDWEBDIR."skin/tmpl/", 2 => "/srv/www/bbsengine6/skin/tmpl/"]);

// @see http://php.net/strftime
define("DATEFORMAT", "%Y-%b-%d %I:%M %p %Z (%A)");

define("LOGENTRYPREFIX", "bbsenginedotcom");

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

define("CURRENTVERSION", "v6/");

define("APIDOCSDIR", DOCUMENTROOT . CURRENTVERSION . "apidocs/");
define("CHANGELOG", DOCUMENTROOT . CURRENTVERSION . "CHANGELOG.txt");
define("README", DOCUMENTROOT . CURRENTVERSION . "README.txt");
define("INSTALL", DOCUMENTROOT . CURRENTVERSION . "INSTALL.txt");
define("RELEASENOTES", DOCUMENTROOT . CURRENTVERSION . "RELEASENOTES.txt");

define("PROJECTURL", "//projects.zoidtechnologies.com/");

define("ENGINEURL", "/");

// @since 20180502 to squash a php notice
define("WWWURL", "//zoidtechnologies.com/");

// define("APIDOCSURI", "");
/**
 * @since 20190223
*/
define("HANDBOOKDIR", DOCUMENTROOT);

define("SESSIONCOOKIEDOMAIN", ".bbsengine.com");
define("SESSIONCOOKIEEXPIRE", 12*60*60);
define("SESSIONCOOKIEPATH", "/");
define("SESSIONNAME", "bbsenginedotcomsession");

// @since 20230409
define("CURRENTPROJECTNAME", "bbsengine6");


?>
