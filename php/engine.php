<?php

namespace {

/**
 * @since 20160419
 * @since 20221116
 */
require_once("Log.php");

/**
 * pull in smarty class
 */
require_once("Smarty.class.php");
}

namespace bbsengine6 {

/**
 * @since 20180804
 * @param mixed field
 * @param string label
 * @param boolean default 
 * @return boolean
 */
function toboolean($value, $label="label", $default=false)
{
  if (is_null($value) === true)
  {
    return $default;
  }

  if (is_bool($value) === true)
  {
    return $value;
  }

  if ($value === "t" || $value == 1)
  {
    return true;
  }

  if ($value === "f" || $value == 0)
  {
    return false;
  }

//  logentry("toboolean.170: returning default of ".var_export($default, true)." for ".var_export($label, true));
  return $default;
}

/**
 * @since 20221116
 */
function displaypage($data=[])
{
  logentry("displaypage called");
  $pagetemplate = isset($data["pagetemplate"]) ? $data["pagetemplate"] : "page.tmpl";
//  $dsn = isset($data["systemdsn"]) ? $data["systemdsn"] : SYSTEMDSN;
  $data["pagetemplate"] = $pagetemplate;
  $data["pagefooter"]["fortune"] = null; // getrandomfortune();

  $choices = isset($data["choices"]) ? $data["choices"] : null;
  $data["choices"] = buildchoices($choices);
  logentry("bbsengine6.displaypage.100: data=".var_export($data, true));
//  logentry("kw.choices=".var_export($data["choices"], true)." pagetemplate=".var_export($pagetemplate, true), true);

  $tmpl = getsmarty();
  $tmpl->assign("data", $data);
  $tmpl->display($pagetemplate);
  return;
}

/**
 * display an error page template with message
 * 
 * @param string $message
 * @param integer $statuscode http error code (i.e. 500, 404)
 * @param string $title
 * @param string $template
 * @access public
 * @since 20120608
 * @since 20230214 added to bbsengine5/engine.php
 */
function displayerrorpage($message, $statuscode=418, $title="error", $template="errormessage.tmpl", $data=[])
{
  logentry("displayerrorpage.100: message=".var_export($message, true)." statuscode=".var_export($statuscode, true));
  
/*
  $tmpl = getsmarty();
  $tmpl->assign("message", $message);
  $tmpl->assign("statuscode", $statuscode);
  $tmpl->assign("title", $title);
*/
//  $page = getpage($title);

  header("HTTP/1.0 {$statuscode} {$title}", true, $statuscode);
//  $data = [];
  $data["statuscode"] = $statuscode;
  $data["message"] = $message;
  $data["title"] = $title;
  $data["pagetemplate"] = $template;
//  logentry("displayerrorpage.200: data=".var_export($data, True));
//  $options["pagedata"]["body"] = $tmpl->fetch($template);
//  $page = getpage("displayerrorpage");
  displaypage($data);
  return;
}

/**
 * @since 20221116
 */
function setcurrentsite($site)
{
  $_SESSION["currentsite"] = $site;
//  logentry("setcurrentsite.10: site=".var_export($site, true));
  return;
}

/**
 * @since 20221116
 */
function getcurrentsite()
{
  $site = isset($_SESSION["currentsite"]) ? $_SESSION["currentsite"] : null;
//  logentry("getcurrentsite.10: site=".var_export($site, true));
  return $site;
}

/**
 * set current page
 *
 * @param string $page
 * @since 20221116
 */
function setcurrentpage($page)
{
  $_SESSION["currentpage"] = $page;
  return;
}

/**
 * get current page
 *
 * @author zoidtechnologies.com
 * @since 20221116
 */
function getcurrentpage()
{
  $page = isset($_SESSION["currentpage"]) ? $_SESSION["currentpage"] : null;
  return $page;
}

/**
 * function to set the current "action" so that "view" can be hidden when in view mode, etc
 *
 * @since 20221116
 */
function setcurrentaction($action)
{
  $_SESSION["currentaction"] = $action;
}

/**
 * function to get the current "action" so that "view" can be hidden when in view mode, etc
 *
 * @since 20110803
 * @since 20221116
 */
function getcurrentaction()
{
  $op = isset($_SESSION["currentaction"]) ? $_SESSION["currentaction"] : null;
  return $op;
}

/**
 * function to clear the current action
 *
 * @since 20150309
 * @since 20221116
 */
function clearcurrentaction()
{
  setcurrentaction(NULL);
  return;
}

/**
 * set the 'returnto' session variable used by redirectpage()
 *
 * @param string $url
 * @param string $title
 * @return old value
 * @since 2022116
 *
 */
function setreturnto($url=null, $title=null)
{
  $old = getreturntourl();
  $url = ($url === null) ? $old : $url;
//  $parsedurl = parse_url($url);
//  $normalizedurl = http_build_url($parsedurl, $parsedurl);
  $returnto = ["url" => $url, "title" => $title];

  $_SESSION["returnto"] = $returnto;
    
//  logentry("setreturnto: url='{$url}'  title='{$title}'");

  return $old;
}
               
/**
 * get the 'returnto' session var which contains 'url' and 'title', falling back to SITEURL and SITETITLE from config
 *
 * @since 20150722
 * @since 20221116
 * @return array with two keys 'url' and 'title'
*/
function getreturnto()
{
 return isset($_SESSION["returnto"]) ? $_SESSION["returnto"] : array("url" => SITEURL, "title" => SITETITLE);
}
                 
/**
 * returns the returntourl as a string if it has been set, else uses SITEURL define
 *
 * @since 20221116
 *
 */
function getreturntourl()
{
  $url = isset($_SESSION["returnto"]["url"]) ? $_SESSION["returnto"]["url"] : SITEURL;
  
  if (isset($url) && !empty($url) && !is_null($url))
  {
    return $url;
  }
  else
  {
    return SITEURL;
  }
}
                   
/**
 * @since 20221116
 */
function getreturntotitle()
{
  return isset($_SESSION["returnto"]["title"]) ? $_SESSION["returnto"]["title"] : SITETITLE;
}

/**
 * return the "current member id" for the session
 *
 * @param string key optional key to use when accessing $_SESSION, defaults to "currentmemberid"
 * @since 20221116
 *
 * @return int
 */
function getcurrentmemberid()
{
  $res = isset($_SESSION["currentmemberid"]) ? intval($_SESSION["currentmemberid"]) : null;
  return $res;
}

/**
 * set the "current member id" for the session
 * 
 * @param integer
 * @return int previous value
 * @since 20221116
 */
function setcurrentmemberid($id)
{
  logentry("setcurrentmemberid.10: id=".var_export($id, true));

  $old = getcurrentmemberid();
  $_SESSION["currentmemberid"] = intval($id);
  return $old;
}

/**
 * permission checking function
 * 
 * permissions "PUBLIC" and "AUTHENTICATED" are built-in and checked for
 * specially before any database connection is made. other permissions are
 * in uppercase and must be listed in the flag table. if the member being
 * checked does not have a value set for a particular flag, the default
 * value will be returned.
 *
 * @param string $name 
 * @param integer $memberid
 * @return boolean
 * @since 20080324
 * @since 20221116
 */ 
function flag($name, $memberid=0)
{
  if ($memberid == 0)
  {
    $memberid = getcurrentmemberid();
  }
	
  $name = strtoupper($name);
    
  if ($name == "PUBLIC")
  {
    return true;
  }

  if ($memberid == 0 || is_null($memberid))
  {
    return false;
  }
	
  if ($name == "AUTHENTICATED")
  {
    return true;
  }
    
  $res = getflag($name, $memberid);
  if (PEAR::isError($res))
  {
    logentry("permission: ERROR: " . $res->toString());
    return PEAR::raiseError($res);
  }
  
  if (is_null($res))
  {
    return $res;
  }
  
  if ($res == true)
  {
    return true;
  }
  
  return false;
}

/**
 * returns flag value given the flag name and member id.
 *
 * @param string $flag flag name
 * @param integer $id member id
 * @return boolean
 * @since 20221116
 */
function getmemberflag($flag, $memberid, $dsn=SYSTEMDSN)
{
  $dbh = dbconnect($dsn);
  if (PEAR::isError($dbh))
  {
    return $dbh;
  }
  
  // @since 20130617
  // thanks to pingwin and teh1ghool on #php (oftc)

//  logentry("getflag.100: flag=".var_export($flag, true)." id=".var_export($id, true));

    $sql = <<<SQL
select 
  f.name, 
  coalesce(mmf.value, f.defaultvalue) as value 
from engine.flag as f
left outer join engine.map_member_flag as mmf on (f.name=mmf.name and mmf.memberid=?) 
where f.name=?;
SQL;

  $dat = [$memberid, $flag];
  $pdo = \bbsengine6\database\connect($dsn);
  $stmt = $pdo->prepare($sql);
  $stmt->execute($dat);

  $res = $dbh->getRow($sql, null, $dat, array("integer", "text"));
  if (PEAR::isError($res))
  {
    logentry("bbsengine3.getflag.0: " . $res->toString());
    return PEAR::raiseError($res);
  }

  $res = (isset($res["value"]) && $res["value"] == "t") ? true : false;
//  logentry("getflag.100: flag=".var_export($flag, true). " memberid=".var_export($memberid, true)." res=".var_export($res, true));
  return $res;
}

/**
 * return the set of flags and their values for a given memberid.
 * rewritten 2011-jun-23 so it actually works without smarty3 throwing notices about undefined vars
 *
 * @since 20081002
 * @param integer $memberid
 * @return array or PEAR_Error
 */
function getmemberflags($memberid, $dsn=SYSTEMDSN)
{
  $sql = <<<SQL
select 
  flag.name, 
  coalesce(map_member_flag.value, flag.defaultvalue) as value
from engine.flag 
left outer join engine.map_member_flag on flag.name = engine.map_member_flag.name and engine.map_member_flag.memberid=?
SQL;
  $dat = array($memberid);
  $pdo = \bbsengine6\database\connect($dsn);
  $stmt = $pdo->prepare($sql);
  $stmt->execute($dat);
  $res = $stmt->fetchAll();

  $flags = [];
  if ($memberid > 0)
  {
    $flags["AUTHENTICATED"] = true;
  }
  else
  {
    $flags["AUTHENTICATED"] = false;
  }

  foreach ($res as $rec)
  {
    $k = $rec["name"];
    $v = $rec["value"];

    if ($v == "t" || $v == "1")
    {
      $flags[$k] = true;
    }
    elseif ($v == "f" || $v == "0")
    {
      $flags[$k] = false;
    }
  }
  return $flags;
}

/**
 * permission checking function f.k.a flag()
 * 
 * permissions "PUBLIC" and "AUTHENTICATED" are built-in and checked for
 * specially before any database connection is made. other permissions are
 * in uppercase and must be listed in the flag table. if the member being
 * checked does not have a value set for a particular flag, the default
 * value will be returned.
 *
 * @param string $name 
 * @param integer $memberid
 * @return boolean
 * @since 20080324
 * @since 20221116
 */ 
function checkmemberflag($name, $memberid=0)
{
  if ($memberid == 0)
  {
    $memberid = getcurrentmemberid();
  }
	
  $name = strtoupper($name);
    
  if ($name == "PUBLIC")
  {
    return true;
  }

  if ($memberid == 0 || is_null($memberid))
  {
    return false;
  }
	
  if ($name == "AUTHENTICATED")
  {
    return true;
  }
    
  $res = getmemberflag($name, $memberid);
  if (PEAR::isError($res))
  {
    logentry("permission: ERROR: " . $res->toString());
    return PEAR::raiseError($res);
  }
  
  if (is_null($res))
  {
    return $res;
  }
  
  if ($res == true)
  {
    return true;
  }
  
  return false;
}

/**
 * put $message into a log at the given priority
 *
 * @since 20080105
 * @since 20221116
 * @param string
 * @param enum
 */
function logentry($message, $priority=PEAR_LOG_DEBUG)
{
  
  if (defined("LOGENTRYPREFIX") === false)
  {
    define("LOGENTRYPREFIX", "define-logentryprefix");
  }
  
  $logger = \Log::factory("syslog", "", LOGENTRYPREFIX, [], PEAR_LOG_DEBUG);
//  $logger->log("bbsengine5.logentry.100: _SERVER=".var_export($_SERVER, true), $priority);
  $ip = $_SERVER["REMOTE_ADDR"];
  
  $logger->log($message, $priority);
  return;
}

/** 
 * @since 20140512
 * @since 20221116
 */
function getfortune($fortuneid)
{
  $fortuneid = intval($fortuneid);
  
  $sql = "select * from engine.mantra where id=?";
  $dat = [$fortuneid];
  $pdo = \bbsengine6\database\connect(SYSTEMDSN);
  $stmt = $pdo->prepare($sql);
  $stmt->execute($dat);
  $res = $stmt->fetch();
  
  $mantra = [];
  $mantra["description"] = $res["description"];
  $mantra["author"] = $res["author"];
  $mantra["reference"] = $res["reference"];
  $mantra["dateposted"] = $res["dateposted"];
  $mantra["datepostedepoch"] = $res["datepostedepoch"];
  $mantra["postedbyid"] = $res["postedbyid"];
  $mantra["postedbyname"] = $res["postedbyname"];
  $mantra["lastmodified"] = $res["lastmodified"];
  $mantra["lastmodifiedepoch"] = $res["lastmodifiedepoch"];
  $mantra["lastmodifiedbyid"] = $res["lastmodifiedbyid"];
  $mantra["actions"] = buildfortuneactions(["fortuneid" => $fortuneid]);
  
  return $mantra;
}

/**
 * @since 20140512
 * @since 20221116
 */
function getrandomfortune($dsn=SYSTEMDSN)
{
  $sql = "select id from engine.mantra order by random() limit 1";
  $dat = [];

  $pdo = \bbsengine6\database\connect($dsn);
  $stmt = $pdo->prepare($sql);
  $stmt->execute($dat);
  $fortuneid = $stmt->fetch();
  return getfortune($fortuneid);
}

/**
 * @since 20160910
 * @since 20221116
 */
function buildfortuneactions($data)
{
  $id = intval($data["fortuneid"]);

  $currentaction = getcurrentaction();
  $currentpage = getcurrentpage();
  $currentsite = getcurrentsite();
//  $currentsection = getcurrentsection();

//  logentry("buildmantraactions.100: currentaction=".var_export($currentaction, true));
  
  $actions = [];
  if (accessfortune("detail") === true)
  {
    $actions[] = array("contenturl" => ENGINEURL."fortune-detail-{$id}?bare", "href" => ENGINEURL."fortune-detail-{$id}", "title" => "detail", "desc" => "show detail for fortune #{$id}", "class" => "fa fa-fw fa-angle-double-down");
  }
  if (accessfortune("edit") === true)
  {
    $actions[] = array("href" => ENGINEURL."fortune-edit-{$id}", "title" => "edit", "desc" => "edit fortune #{$id}", "class" => "fa fa-fw fa-edit");
  }
/*
  if ($currentaction !== "summary" && accessmantra("summary") === true)
  {
    $actions[] = array("href" => ENGINEURL."mantra-summary", "title" => "summary", "desc" => "paged listing of mantras");
  }
*/
  return $actions;
}

/**
 * given an operation, return a boolean or null if the operation is not handled
 * @param string op operation.. for example "summary" or "edit" or "delete"
 * @param dictionary data optional data needed to resolve access check
 * @param integer memberid member id to check or null to use result of getcurrentmemberid()
 * @return boolean|null true, false, or null if the operation is not handled
 * @since 20160910
 */
function accessfortune($op, $data=null, $memberid=null)
{
  switch ($op)
  {
    case "edit":
    {
      if (checkmemberflag("SYSOP", $memberid) === true)
      {
        $res = true;
        break;
      }
      $res = false;
      break;
    }
    case "detail":
    {
      $res = true;
      break;
    }
    case "add":
    {
      if (checkmemberflag("SYSOP", $memberid) === true)
      {
        $res = true;
        break;
      }
      $res = false;
      break;
    }
    case "summary":
    {
      $res = true;
      break;
    }
    default:
    {
      $res = null;
      break;
    }
  }
//  logentry("accessmantra.100: op=".var_export($op, true)." res=".var_export($res, true));
  return $res;
}

function getsmarty($options=null)
{
  $options = [];
  $options["pluginsdir"] = SMARTYPLUGINSDIR;
  $options["templatedir"] = SMARTYTEMPLATESDIR;
  $options["compiledir"] = SMARTYCOMPILEDTEMPLATESDIR;
  $options["compileid"] = LOGENTRYPREFIX;

  logentry("getsmarty.100: options=".var_export($options, true));

  $s = new \Smarty();

  $currentcart = [];
  $currentcart["items"] = [];
  $currentcart["itemcount"] = 0;
  
  $s->assign("currentcart", $currentcart); // getcurrentcart());

  if (is_array($options))
  {
    if (array_key_exists("templatedir", $options) === true)
    {
      $s->setTemplateDir($options["templatedir"]);
    }
    if (array_key_exists("pluginsdir", $options) === true)
    {
      $s->addPluginsDir($options["pluginsdir"]);
    }
    if (array_key_exists("compiledir", $options) === true)
    {
      $s->compile_dir = $options["compiledir"];
    }
    if (array_key_exists("compileid", $options) === true)
    {
      $s->compile_id = $options["compileid"];
    }
    if (array_key_exists("vars", $options) === true)
    {
      foreach ($options["vars"] as $k => $v)
      {
        $s->assign($k, $v);
      }
    }
  }
  
  $currentmemberid = getcurrentmemberid();
  
  if ($currentmemberid > 0)
  {
    $currentmember = getcurrentmember();
    if (PEAR::isError($currentmember))
    {
      logentry("getsmarty.10: " . $currentmember->toString());
      return PEAR::raiseError($currentmember);
    }
  }
  else
  {
    $currentmember = [];
    $currentmember["id"] = null;
  }

  $flags = getmemberflags($currentmemberid);

  $currentmember["flags"] = $flags;

  $s->assign("currentpage", getcurrentpage());
  $s->assign("currentmemberid", $currentmemberid);
  $s->assign("currentmember", $currentmember);
  $s->assign("currentaction", getcurrentaction());
  $s->assign("currentsite", getcurrentsite());
  $s->assign("currenturi", getcurrenturi());
  $s->assign("currentpath", getcurrentpath());
  $s->assign("currentsig", getcurrentsig());
//  $s->assign("sitevars", getsitevars());

  return $s;
}

/**
 * function that returns the current url (protocol, hostname, etc) even tho it is named ..uri()
 * 
 * @since 20110804
 * @since 20221116
 */
function getcurrenturi()
{
  $protocol = (isset($_SERVER["HTTPS"]) && $_SERVER["HTTPS"] !== "off") ? "https" : "http";
  $host = $_SERVER["HTTP_HOST"];
  $uri = $_SERVER["REQUEST_URI"];
  $buf = "{$protocol}://{$host}{$uri}";
  return $buf;
}

/**
 * @since 20151204
 * @since 20221116
 */
function getcurrentpath($uri=null)
{
  if ($uri === null)
  {
    $uri = getcurrenturi();
  }
  $path = parse_url($uri, PHP_URL_PATH);
  if (substr($path, -1) !== "/")
  {
    $path .= "/";
  }
  
  return $path;
}

/**
 * @since 20160427
 * @since 20221116
 */
function getcurrentsig()
{
  $currentsig = isset($_SESSION["currentsig"]) ? $_SESSION["currentsig"] : null;
  return $currentsig;
}

/**
 * @since 20160427
 * @since 20221116
 */
function setcurrentsig($sig=null)
{
  $_SESSION["currentsig"] = $sig;
  return;
}

/**
 * return a list of dictionaries with keys 'title' and 'uri' for each part of $path (ltree)
 *
 * @since 20151118
 * @since 20221117
 */
function buildbreadcrumbs($path)
{
  logentry("buildbreadcrumbs.100: ".var_export($path, true));

  $pdo = \bbsengine6\database\connect(SYSTEMDSN);
  $sql = "select * from engine.sig where path @> ? order by path asc";
  $dat = [$path];
  $stmt = $pdo->prepare($sql);
  $stmt->execute($dat);
  $res = $stmt->fetchAll();
  
  $crumbs = [];
  foreach ($res as $rec)
  {
    $crumbs[] = $rec;
  }

//  logentry("buildbreadcrumbs.200: crumbs=".var_export($crumbs, true));
  return $crumbs;
}

function buildsiguri($sigpath)
{
  if ($sigpath == null || $sigpath == "")
  {
    return "/";
  }
  
  $sigpath = str_replace($sigpath, "top.", "");
  $sigpath = str_replace($sigpath, ".", "/");
  $sigpath = str_replace($sigpath, "_", "-");
  return $sigpath;
}

/**
 * function which converts a postgres array (comma separated text) to a php array
 * https://prosuncsedu.wordpress.com/2009/10/13/postgres-array-to-php-array-or-vice-versa/
 *
 * @since 20190822 in bbsengine4
 * @since 20200223 in bbsengine5
 * @since 20221118
 *
 * @param $text postgres array in text format
 * @return array
 */
function postgres_to_php_array($text)
{
  logentry("postgres_to_php_array.100: text=".var_export($text, true));
  $text = trim($text, "{}");
  logentry("postgres_to_php_array.120: text=".var_export($text, true));
  $res = explode(",", $text);
  logentry("postgres_to_php_array.130: res=".var_export($res, true));
  return $res;
}

/**
 * copied from zoidweb2
 * 
 * @since 20180223
 * @since 20221120
 * @since 20221222 renamed
 */
function sortchoices($a, $b)
{
  $foo = isset($a["title"]) ? $a["title"] : null;
  $bar = isset($b["title"]) ? $b["title"] : null;

  if ($foo < $bar) return -1;
  if ($foo == $bar) return 0;
  if ($foo > $bar) return 1;
}

/**
 * copied from zoidweb2
 * 
 * @since 20131014
 * @since 20221120
 */
function buildchoices($menu=[])
{
//  $currentpage = getcurrentpage();
//  $menu = array();

  if (checkmemberflag("ADMIN"))
  {
      $menu[] = ["name" => "addflag", "title" => "add system flag", "url" => ENGINEURL."flag-add", "desc" => "add system flag to the database"];
      $menu[] = ["name" => "addmantra", "title" => "add mantra", "url" => ENGINEURL."mantra-add", "desc" => "add mantra"];
//      $menu[] = ["name" => "addsitenews", "title" => "add site news", "url" => TEOSURL."sitenews/add-post", "desc" => "add a post to the 'site news' sig to be displayed on the www site"];
//      $menu[] = array("name" => "addlink", "title" => "add link", "url" => VULCANURL . "add");
//      $menu[] = array("name" => "addfeed", "title" => "add feed", "url" => DEMETERURL . "add");
  }

//  $menu[] = ["name" => "about", "title" => "about", "url" => "/about", "desc" => "about this site"];
//  $menu[] = ["name" => "achilles", "title" => "achilles", "url" => ACHILLESURL, "desc" => ""];
/*
  $menu[] = ["name" => "teos", "title" => "teos", "url" => TEOSURL, "desc" => "catalog view"];
//  $menu[] = array("name" => "bbsengine", "title" => "BBSEngine", "url" => "http://bbsengine.org/", "desc" => "Simple But Elegant Web Application Framework");
  $menu[] = ["name" => "vulcan", "title" => "vulcan", "url" => VULCANURL, "desc" => "links database", "icon" => SKINURL . "art/new2.png"];
  $menu[] = ["name" => "www", "title" => "www site", "url" => WWWURL, "desc" => "main www site"];
  $menu[] = ["name" => "repo", "title" => "software repo", "url" => REPOURL, "desc" => "download software"];
//  $menu[] = array("name" => "aolbonics", "title" => "Urban Dictionary", "url" => AOLBONICSURL, "desc" => "Urban Dictionary");
  $menu[] = ["name" => "projects", "title" => "projects", "url" => "http://projects.zoidtechnologies.com/", "desc" => "Projects Site"];
  $menu[] = ["name" => "sophia", "title" => "sophia", "url" => SOPHIAURL, "desc" => "forum/blog"];
  
  $menu[] = ["name" => "psyche", "title" => "psyche", "url" => PSYCHEURL, "desc" => ""];
  $menu[] = ["name" => "agora", "title" => "agora", "url" => AGORAURL, "desc" => "a Worthy marketplace", "class" => "fas fa-fw fa-store"];
//  $menu[] = ["name" => "jamhacks", "title" => "jamhacks", "url" => WWWURL."jamhacks", "desc" => "combination resume, biography, and portfolio"];
  $menu[] = ["name" => "sitenewsarchive", "title" => "site news archive", "url" => WWWURL."sitenewsarchive/", "desc" => "site news older than a month or two"];
  if (flag("AUTHENTICATED"))
  {
    $menu[] = ["name" => "casino", "title" => "casino", "url" => CASINOURL, "desc" => "casino for entertainment purposes only"];
  }
  if (checkmemberflag("ADMIN"))
  {
    $menu[] = ["name" => "amznitem-add", "title" => "add amazon item", "url" => AGORAURL."amznitem-add"];
  }
  $menu[] = ["name" => "mantrasummary", "title" => "mantra summary", "url" => ENGINEURL."mantra-summary", "desc" => "mantra summary pages"];
*/
 if ($menu !== null)
 {
  uasort($menu, "\\bbsengine6\\sortchoices");
 }
//  logentry("menu=".var_export($menu, true));
  return $menu;
}


/**
 * return a list of dictionaries with keys 'title' and 'uri' for each part of $sigpath (ltree)
 *
 * @since 20151118
 * @since 20221124
 */
/*
function buildbreadcrumbs($sigpath, $skiptop=true, $hidepath=null)
{
//  logentry("bbsengine4.buildbreadcrumbs.100: sigpath=".var_export($sigpath, true)." skiptop=".var_export($skiptop, true));
  $pdo = databaseconnect(SYSTEMDSN4);
  $sql = "select title, path, uri from engine.sig where path @> ? order by path asc";
  $dat = [$sigpath];
  $stmt = $pdo->prepare($sql);
  $stmt->execute($dat);
  $res = $stmt->fetchAll();
  
  $crumbs = [];
  foreach ($res as $sig)
  {
    if ($skiptop === true && $sig["path"] === "top")
    {
      array_shift($res);
      continue;
    }
    if (is_string($hidepath) === true && $sig["path"] === $hidepath)
    {
      continue;
    }

    $crumbs[] = $sig;
  }

//  logentry("buildbreadcrumbs.200: crumbs=".var_export($crumbs, True));
  return $crumbs;
}
*/

/**
 * calls json_encode() with default parameters
 *
 * @since 20140730
 * @since 20230329 copied from bbsengine5.php
 */
function encodejson($data)
{
 // @see http://us3.php.net/manual/en/json.constants.php
 return json_encode($data); // , JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT | JSON_NUMERIC_CHECK); // JSON_UNESCAPED_UNICODE in 5.4+
}

/**
 * decodes given json data into a dictionary (associative array)
 * 
 * @since 20140730
 * @since 20230329 copied from bbsengine5.php
 */
function decodejson($data)
{
 if (is_string($data) === false)
 {
  logentry("decodejson.100: data=".var_export($data, true));
  return;
 }
 return json_decode($data, true);
}

/**
 * builds a valid ltree label from the given buffer
 * f.e.: m-a-s-h -> m_a_s_h
 * @since 20230704 copied from bbsengine5
 */
function buildlabel($buf)
{
  $buf = strtolower($buf);
  // replace anything that is not a-z0-9 with _
  $buf = preg_replace("@[^a-z0-9_]@","_", $buf);

  // replace 2 or more - with single _
  $buf = preg_replace("@[_-]{2,}@", "_", $buf);

  // trim '_' and '.' from both ends
  $buf = trim($buf, "_");
  $buf = trim($buf, ".");

  return $buf;
}

/**
 * @since 20230704 copied from bbsengine5
 * @return string
*/
function normalizelabelpath()
{
 $argc = func_num_args();
 $argv = func_get_args();

 $foo = [];

 foreach ($argv as $arg)
 {
  $labels = explode(".", $arg);
  foreach ($labels as $label)
  {
   $foo[] = buildlabel($label);
  }
 }
 $foo = array_filter($foo);
// logentry("normalizelabelpath.102: foo=".var_export($foo, true));
 if (count($foo) > 0 && $foo[0] !== "top")
 {
  array_unshift($foo, "top");
 }
 $res = implode(".", $foo);
 if ($res === "")
 {
  $res = "top";
 }
// logentry("normalizepath.100: res=".var_export($res, true));
 return $res;
}

} /* bbsengine6 namespace */
?>
