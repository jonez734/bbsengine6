<?php

/*
 * @since 20230409
 */

$bbsengine_root = getenv('BBSENGINE_ROOT') ?: '/srv/www/bbsengine6';
$zoid_root = getenv('ZOID_ROOT') ?: '/srv/www/zoid6';
$smarty_root = getenv('SMARTY_ROOT') ?: '/srv/www/smarty';
$vhost_dir = getenv('VHOST_DIR') ?: '/srv/www/vhosts/www.bbsengine.org';
$repo_dir = getenv('REPO_DIR') ?: '/srv/repo';

$includepath = get_include_path().":{$zoid_root}/php/:{$bbsengine_root}/php/:{$smarty_root}/php/";
if (set_include_path($includepath) === false)
{
    error_log("include path fail");
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

define("config\VHOSTDIR", $vhost_dir . "/");
define("config\DOCUMENTROOT", \config\VHOSTDIR . "html/");

//define("ZOIDWEBDIR", $zoid_root);

define("config\SMARTYCOMPILEDTEMPLATESDIR", \config\VHOSTDIR."templates_c");
define("config\SMARTYPLUGINSDIR", [ 0 => \config\VHOSTDIR."smarty/"]);
//define("SMARTYTEMPLATESDIR", [ 0 => DOCUMENTROOT."skin/tmpl/", 1 => ZOIDWEBDIR."skin/tmpl/", 2 => $bbsengine_root."/skin/tmpl/"]);
define("config\SMARTYTEMPLATESDIR", [ 0 => \config\DOCUMENTROOT."skin/tmpl/", 1 => $bbsengine_root."/skin/tmpl/"]);

// @see http://php.net/strftime
define("DATEFORMAT", "%Y-%b-%d %I:%M %p %Z (%A)");

define("config\LOGENTRYPREFIX", "bbsenginedotorg");

define("RELEASESDIR", $repo_dir . "/");

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
define("\HANDBOOKDIR", \config\HANDBOOKDIR);

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

define("RECAPTCHASITEKEY", getenv('RECAPTCHA_SITE_KEY') ?: '');
define("RECAPTCHASECRETKEY", getenv('RECAPTCHA_SECRET_KEY') ?: '');

?>
