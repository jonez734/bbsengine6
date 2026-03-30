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

require_once("PEAR.php");

require_once("HTML/QuickForm2.php");
require_once("HTML/QuickForm2/Renderer.php");
//require_once("HTML/QuickForm2/Element/Captcha/TextCAPTCHA.php");
//require_once("HTML/QuickForm2/Element/Captcha/Image.php");
require_once("HTML/QuickForm2/Element/Captcha/ReCaptcha.php");

require_once("libmember.php");
require_once("util.php");

} /* root namespace */

namespace bbsengine6 {

/**
 * @since 20180804
 * @since 20240807 ported to bbsengine6
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

  if ($value === "t" || $value == 1 || $value == "true")
  {
    return true;
  }

  if ($value === "f" || $value == 0 || $value == "false")
  {
    return false;
  }

//  logentry("toboolean.170: returning default of ".var_export($default, true)." for ".var_export($label, true));
  return $default;
}

/**
 * @since 20221116
 */
function displaypage($data=[], $pagetemplate="page.tmpl")
{
//  util\logentry("displaypage called");
//  $pagetemplate = isset($data["pagetemplate"]) ? $data["pagetemplate"] : "page.tmpl";
//  $data["pagetemplate"] = $pagetemplate;

  $data["pagefooter"]["fortune"] = null; // getrandomfortune();

  $data["choices"] = isset($data["choices"]) ? $data["choices"] : null; // buildchoices($choices);
//  util\logentry("bbsengine6.displaypage.100: choices=".var_export($choices, true));

  $tmpl = getsmarty();
  $tmpl->assign("data", $data);
//  $tmpl->assign("currentpage", \bbsengine6\getcurrrentpage());
  $tmpl->display($pagetemplate);
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
/*
function flag($name, $memberid=0)
{
  if ($memberid == 0)
  {
    $memberid = member\lib\getcurrentid();
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
    
  $res = \bbsengine6\member\lib\getflag($name, $memberid);
  
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
*/
/**
 * returns flag value given the flag name and member id.
 *
 * @param string $flag flag name
 * @param integer $id member id
 * @return boolean
 * @since 20221116
 */
/*
function getmemberflag($flag, $memberid, $dsn=\config\SYSTEMDSN)
{
  //$dbh = \bbsengine6\database\connect($dsn);
  //if (\PEAR::isError($dbh))
  //{
  //  return $dbh;
  //}
  
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
  if (\PEAR::isError($res))
  {
    logentry("bbsengine3.getflag.0: " . $res->toString());
    return \PEAR::raiseError($res);
  }

  $res = (isset($res["value"]) && $res["value"] == "t") ? true : false;
//  logentry("getflag.100: flag=".var_export($flag, true). " memberid=".var_export($memberid, true)." res=".var_export($res, true));
  return $res;
}
*/

/** 
 * @since 20140512
 * @since 20221116
 */
function getfortune($fortuneid)
{
  $fortuneid = intval($fortuneid);
  
  $sql = "select * from engine.mantra where id=?";
  $dat = [$fortuneid];
  $pdo = \bbsengine6\database\connect(\config\SYSTEMDSN);
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
function getrandomfortune($dsn=\config\SYSTEMDSN)
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
  $options["pluginsdir"] = \SMARTYPLUGINSDIR;
  $options["templatedir"] = \SMARTYTEMPLATESDIR;
  $options["compiledir"] = \SMARTYCOMPILEDTEMPLATESDIR;
  $options["compileid"] = \LOGENTRYPREFIX;

  // logentry("getsmarty.100: options=".var_export($options, true));

  $s = new \Smarty();
  $s->setEscapeHtml(true);

/*
  $currentcart = [];
  $currentcart["items"] = [];
  $currentcart["itemcount"] = 0;
*/  
//  $s->assign("currentcart", $currentcart); // getcurrentcart());

  if (is_array($options))
  {
    if (array_key_exists("templatedir", $options) === true)
    {
      $s->setTemplateDir($options["templatedir"]);
    }
    if (array_key_exists("pluginsdir", $options) === true)
    {
      // \bbsengine6\logentry("pluginsdir=".var_export($options["pluginsdir"]));
      $s->addPluginsDir($options["pluginsdir"]);
    }
    if (array_key_exists("compiledir", $options) === true)
    {
      $s->setCompileDir($options["compiledir"]);
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
  
  $currentmoniker = member\lib\getcurrentmoniker();
  $currentmemberid = member\lib\getcurrentid();
  $currentmember = member\lib\getbymoniker($currentmoniker);
  
/*
  if ($currentmemberid > 0)
  {
    $currentmember = member\getcurrent();
  }
  else
  {
    $currentmember = [];
    $currentmember["id"] = null;
  }
*/
  $flags = member\lib\getflags($currentmemberid);
  $currentmember["flags"] = $flags;

//  \bbsengine6\logentry("engine.getsmarty.100: currentmember=".var_export($currentmember, true));
  $s->assign("currentpage", getcurrentpage());
  $s->assign("currentmemberid", $currentmemberid);
  $s->assign("currentmember", $currentmember);
  $s->assign("currentmoniker", $currentmoniker);
  $s->assign("currentaction", getcurrentaction());
  $s->assign("currentsite", getcurrentsite());
  $s->assign("currenturi", getcurrenturi());
  $s->assign("currentsig", getcurrentsig());
//  $s->assign("currentpath", getcurrentpath());
//  $s->assign("sitevars", getsitevars());
//  $s->register_modifier('var_export', 'var_export');
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
/*
  $protocol = (isset($_SERVER["HTTPS"]) && $_SERVER["HTTPS"] !== "off") ? "https" : "http";
  $host = $_SERVER["HTTP_HOST"];
  $uri = $_SERVER["REQUEST_URI"];
  $buf = "{$protocol}://{$host}{$uri}";
*/
// $protocol = $_SERVER['SERVER_PROTOCOL'];
// $requestscheme = $_SERVER["REQUEST_SCHEME"];
// $host = isset($_SERVER['HTTP_HOST']) ? $_SERVER["HTTP_HOST"] : $_SERVER["SERVER_NAME"];
// $uri = $_SERVER['REQUEST_URI'];

 $buf = $_SERVER["REQUEST_SCHEME"]."://".$_SERVER["SERVER_NAME"].$_SERVER["REQUEST_URI"];
 util\logentry("getcurrenturi.100: buf=".var_export($buf, true));
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
  util\logentry("buildbreadcrumbs.100: ".var_export($path, true));

  $pdo = \bbsengine6\database\connect(\config\SYSTEMDSN);
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
 * @since 20240812
 */
function buildsigpath($uri)
{
 if ($uri === null || $uri === "")
 {
  return "top";
 }
 $sigpath = str_replace($uri, "/", ".");
 $sigpath = str_replace($sigpath, "-", "_");
 $sigpath = "top.".$sigpath;
 return $sigpath;
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
function buildchoices($choices=[])
{
//  $currentpage = getcurrentpage();
//  $menu = array();

  if (member\lib\checkflag("SYSOP"))
  {
//      $menu[] = ["name" => "addflag", "title" => "add system flag", "url" => \config\ENGINEURL."flag-add", "desc" => "add system flag to the database"];
      $choices[] = ["name" => "addmantra", "title" => "add mantra", "url" => \config\ENGINEURL."mantra-add", "desc" => "add mantra"];
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
 if ($choices !== null and count($choices) > 0)
 {
  uasort($choices, "\\bbsengine6\\sortchoices");
 }
//  util\logentry("bbsengine6.engine.buildchoices.100: choices=".var_export($choices, true));
  return $choices;
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
 util\logentry("normalizepath.104: ".var_export($foo, true));
 $res = implode(".", $foo);
 if ($res === "")
 {
  $res = "top";
 }
// logentry("normalizepath.100: res=".var_export($res, true));
 return $res;
}

/**
 * Takes one or more path/filenames and joins them using DIRECTORY_SEPARATOR. then it strips a leading or trailing DIRECTORY_SEPARATOR, then it replaces "//" with "/"
 * Example: joinpath('/var','www/html/','/try.php'); // returns 'var/www/html/try.php'
 * original idea from http://www.bin-co.com/php//scripts/filesystem/join_path/
 * re-written to not use for loops (array_filter, join instead)
 * 
 * @since 20240619 copied from bbsengine5
 * @todo consider using preg_replace
 */
function joinpath()
{
    $arguments = func_get_args();
//    logentry("bbsengine5.joinpath.100: arguments=".var_export($arguments, true));
    $arguments = array_filter($arguments);

    $path = join(DIRECTORY_SEPARATOR, $arguments);
    if ($path === "")
    {
      return "";
    }

//    logentry("joinpath.140: before // removal: path=".var_export($path, true));
    $path = preg_replace("@[/]{2,}@", "/", $path);
//    $path = str_replace(DIRECTORY_SEPARATOR.DIRECTORY_SEPARATOR, DIRECTORY_SEPARATOR, $path);
//    logentry("joinpath.160: after // removal: path=".var_export($path, true));

//    logentry("bbsengine5.joinpath.120: path=".var_export($path, true));
    if ($path[0] === DIRECTORY_SEPARATOR)
    {
      $path = substr($path, 1);
    }

    if (substr($path, -1) === DIRECTORY_SEPARATOR)
    {
      $path = substr($path, 0, -1);
    }
//    logentry("joinpath.110: path=".var_export($path, true));
    return $path;
}

/**
 * @since 20240621 copied from bbsengine4 
 */
function normalizeuri($uri)
{
 $uri = preg_replace("@(/){2,}@", '$1', $uri);
 return $uri;
}

/**
 *
 * given one or more URIs (the function has a variable number of arguments),
 * compose a proper labelpath, calling normalizelabelpath() at the end.
 *
 * @since 20240621 copied from bbsengin4
 */
function buildlabelpath()
{
  $argv = func_get_args();
  $argc = func_num_args();

  $teospath = parse_url(\TEOSURL, PHP_URL_PATH);
  if ($teospath === null)
  {
      return \PEAR::raiseError("unable to parse url (code: buildlabelpath.100)");
  }
  $teospath = ltrim($teospath, "/");
//  logentry("buildlabelpath.120: teospath=".var_export($teospath, True));

  $foo = [];

  foreach ($argv as $arg)
  {
   $explode = explode("/", $arg);

   $uripath = parse_url($arg, PHP_URL_PATH);

   $count = 1;
   $res = str_replace($teospath, "", $uripath, $count);

   $fragments = explode("/", $res);
   foreach ($fragments as $fragment)
   {
    $foo[] = buildlabel($fragment);
   }
  }
  $foo = array_filter($foo);

  $path = implode(".", $foo);

  $path = normalizelabelpath($path);
  return $path;
}

function getsubsigs($labelpath)
{
  $sql = "select path from engine.sig where path ~ ?";
  $dat = ["{$labelpath}.*{1}",];

  $pdo = \bbsengine6\database\connect(\SYSTEMDSN);
  $stmt = $pdo->prepare($sql);
  $stmt->execute($dat);
  if ($stmt->rowCount() === 0)
  {
    \bbsengine6\util\logentry("engine.getsubsigs.100: no subsigs for ".var_export($labelpath, true));
  }
  $res = $stmt->fetchAll();

  $subsigs = [];
  foreach ($res as $rec)
  {
    $subsigs[] = getsig($rec["path"], false);
  }
  return $subsigs;
}
/**
 * @since 20240626 copied from bbsengine4
 *
 */
function getsig($labelpath, $subsigs=true)
{
  \bbsengine6\util\logentry("getsig.100: labelpath=".var_export($labelpath, true));
  $sql = "select * from engine.sig where path=:labelpath";
  $dat = ["labelpath" => $labelpath];

  $pdo = \bbsengine6\database\connect(\SYSTEMDSN);

  $stmt = $pdo->prepare($sql);
  $stmt->execute($dat);
  if ($stmt->rowCount() == 0)
  {
   return null;
  }
  $sig = $stmt->fetch();
  if ($sig["uri"] === null)
  {
   $sig["uri"] = util\ltreeToPath($sig["path"]); 
  }
  $sig["actions"] = buildsigactions($sig);

  $sig["icon"] = "fa fa-folder";

  $sig["sigs"] = null;
  if ($subsigs === true)
  {
    $sig["sigs"] = getsubsigs($labelpath);
  }
  return $sig;
}

/**
 * @since 20240626 copied from bbsengine4
 * @return boolean
 * @param string op delete, edit, add, view
 * @param dictionary sig dictionary containing a sig record
 * @param integer memberid memberid to check or null to use currentmemberid
 */
function accesssig($op, $sig=null, $memberid=null)
{
    if ($memberid === null)
    {
        $memberid = member\lib\getcurrentid();
    }

    //    logentry("accesssig.200: op=".var_export($op, True));
    switch ($op)
    {
        case "sig.delete":
        case "sig.edit":
        case "sig.add":
        {
            $adminflag = member\lib\checkflag("SYSOP");
            util\logentry("accesssig.210: adminflag=".var_export($adminflag, true));
            if ($adminflag === true)
            {
                util\logentry("accesssig.220: adminflag is true");
                $res = true;
                break;
            }
            else
            {
                util\logentry("accesssig.230: adminflag is false");
                $res = false;
                break;
            }
        }
        case "sig.view":
        {
            $res = true;
            break;
        }
        case "post.add":
//        case "addpost":
        {
            $res = true;
            break;
        }
        case "link.add":
        {
            $res = false;
            break;
        }
        default:
        {
            util\logentry("accesssig.100: unknown op ".var_export($op, true));
            $res = false;
            //$res = \PEAR::raiseError("unknown mode (code: accesssig.100)");
            break;
        }
    }
    util\logentry("accesssig.120: op=".var_export($op, true)." res=".var_export($res, true));
    return $res;
}

  /**
   * @since 20240626 copied from zoidweb4
   */
  function buildsigactions($sig)
  {
    $uri = isset($sig["uri"]) ? $sig["uri"] : null;
    $labelpath = isset($sig["path"]) ? $sig["path"] : null;
    
    $currentmemberid = member\lib\getcurrentid();

    $actions = [];
    if (accesssig("sig.edit", $sig) === true)
    {
      $actions[] = ["href" => \TEOSURL . $uri . "edit-sig", "title" => "edit sig", "class" => "fa fa-edit fa-fw"];
    }
    if (accesssig("link.add", $sig) === true)
    {
      $actions[] = ["href" => \TEOSURL . $uri . "add-link", "title" => "add link", "class" => "fa fa-plus fa-fw"];
    }
    if (accesssig("post.add", $sig) === true)
    {
      $actions[] = ["href" => \TEOSURL . $uri . "add-post", "title" => "add post", "class" => "fa fa-fw fa-plus"];
    }
    if (accesssig("sig.add", $sig) === true)
    {
      $actions[] = ["href" => \TEOSURL . $uri . "add-sig", "title" => "add sig", "class" => "fas fa-fw fa-folder-plus"];
    }
    if (accesssig("sig.detail", $sig) === true)
    {
      $actions[] = ["href" => \TEOSURL . $uri . "sig-detail", "title" => "detail", "class" => "fa fa-fw fa-angle-double-down"];
    }

    return $actions;
  }

/*
 * Smarty plugin
 * -------------------------------------------------------------
 * File:     modifier.var_export.php
 * Type:     modifier
 * Name:     var_export
 * Purpose:  export a given var
 * -------------------------------------------------------------
 */
function smarty_modifier_var_export($string)
{
    return var_export($string);
}

function getquickform($id, $method="post", $attributes="", $tracksubmit=true, $editor="standard")
{
  util\logentry("getquickform()");
  $form = new \HTML_QuickForm2($id, $method, $attributes, $tracksubmit);
  $form->setAttribute("enctype", "multipart/form-data");
  $form->addHidden("mode")->setValue("NEEDINFO");
  $form->addHidden("id")->setValue("NEEDINFO");
  $form->addHidden("memberid")->setValue("NEEDINFO");
  $csrfToken = \bbsengine6\util\csrfGetToken();
  $form->addHidden(\bbsengine6\util\CSRF_TOKEN_NAME)->setValue($csrfToken);
//  $form->addHidden("pageprotocol")->setValue("standard");
  $form->addRecursiveFilter("trim");
//  $form->addRecursiveFilter("strip_tags");

  return $form;
}

/**
 *
 * function which returns a configured Array renderer for use by quickform2
 *
 * @param $options array optional dictionary containing renderer options
 * @return QF2 Array renderer
 * @since 20140902
 */
function getquickformrenderer($options=null)
{
 $_options = array(
  "group_errors" => true, 
  "group_hiddens" => true, 
  "required_note" => "<span class='requiredstar'>*</span> denotes required fields."
 );
 
 if (is_array($options))
 {
  $_options = array_merge($_options, $options);
 }

 $renderer = \HTML_QuickForm2_Renderer::factory("array")->setOption($_options);
 return $renderer;
}

function buildcaptchafieldset($form, $sessionVar=null, $options=null)
{
//  $form->addElement("header", "captchafieldset", "Verification");

  util\logentry("buildcaptchafieldset.10: disabled");
  return;

  if ($sessionVar === null)
  {
    $sessionVar = basename(__FILE__, ".php");
  }

  util\logentry("buildcaptchafieldset.5: sessionVar=".var_export($sessionVar, true));
  
  $_options = [
    "width"        => 250,
    "height"       => 90,
    "callback"     => "/gencaptchaimage.php?var=".$sessionVar,
    "sessionVar"   => $sessionVar,
    "alt" => "testing",
    "imageOptions" => [
      "font_size" => 20,
      "font_path" => "/usr/share/fonts/truetype/",
      "font_file" => "cour.ttf",
      "min_font_size" => 10,
      "max_font_size" => 30,
      "lines_color" => "#FF0000",
      "background_color" => "#F0F0F0"]
    ];

  if ($options !== null)
  {
    $options = array_merge($_options, $options);
  }
  else
  {
    $options = $_options;
  }
  return;

  util\logentry("options=".var_export($options, true));
//  $form->addElement(new \HTML_QuickForm2_Element_Static, "<div class='g-recaptcha' data-sitekey=".\config\RECAPTCHASITEKEY."></div>");
  return;
  
  $captcha_question = &$form->addElement(new \HTML_QuickForm2_Element_Captcha_ReCaptcha(
      'captcha[recaptcha]',
      ['id' => 'captcha_recaptcha'],
      [
          'label' => 'ReCaptcha',

          "public-key" => getenv('RECAPTCHA_SITE_KEY') ?: RECAPTCHASITEKEY,
          "private-key" => getenv('RECAPTCHA_SECRET_KEY') ?: RECAPTCHASECRETKEY,
      ]
    )
);

/*
  $captcha_question = $form->addElement(new \HTML_QuickForm2_Element_Captcha_Image(
    'captcha[image]',
    ['id' => 'captcha_image'],
    ['label' => 'Image',
    // Captcha options
     'output' => 'png',
     'width'  => 300,
     'height' => 100,
     // Path where to store images
     'imageDir' => \config\CAPTCHAIMAGEDIR, // __DIR__ . '/tmp/',
     'imageDirUrl' => \config\CAPTCHAIMAGEURL, // 'tmp/',
     'imageOptions' => [
      'font_path'        => '/usr/share/fonts/truetype/dejavu/',
      'font_file'        => 'DejaVuSans.ttf',
      'text_color'       => '#000000',
      'background_color' => '#ffffff',
      'lines_color'      => '#000000',
    ]
   ]
  )
 );
//  $captcha_question = &$form->addElement("CAPTCHA_Image", "captcha_question",
//                                         "Type the letters you see", $options);
*/  
  if (\PEAR::isError($captcha_question))
  {
    util\logentry("buildcaptchafieldset.10: " . $captcha_question->toString());
    return \PEAR::raiseError("Form Error (code: buildcaptchafieldset.10)");
  }

  $captcha_answer = $form->addElement("text", "captcha", "Enter the answer");
  if (\PEAR::isError($captcha_answer))
  {
    util\logentry("buildcaptchafieldset.12: " . $captcha_answer->toString());
    return \PEAR::raiseError("Form Error (code: buildcaptchafieldset.12)");
  }

//  $form->addRule("captcha", "Enter the answer to the verification",
//                 "required");
//                 
//  $form->addRule("captcha", "You did not answer the verification correctly",
//                  "CAPTCHA", $captcha_question);

//  var_export($options);
//  exit;
}

function handleform($form, $callback)
{
  $issubmitted = $form->isSubmitted();
  $validate = $form->validate();

  util\logentry("handleform.100: issubmitted=".var_export($issubmitted, true)." validate=".var_export($validate, true));
  
  if ($issubmitted === true && !\bbsengine6\util\csrfCheckRequest())
  {
    util\logentry("handleform.105: CSRF validation failed");
    return \PEAR::raiseError("CSRF validation failed (code: handleform.105)");
  }

  if ($issubmitted === true)
  {
    $value = $form->getValue();
  }
  if ($issubmitted === true && $validate === true)
  {
    foreach ($form->getElements() as $element)
    {
      // @FIX: handle nested fieldsets
      util\logentry("handleform.200: inside foreach. class=".var_export(get_class($element), true));
      if ($element instanceof HTML_QuickForm2_Element_Captcha)
      {
        util\logentry("handleform.210: clearing captcha session");
        $element->clearCaptchaSession();
      }
    }

    util\logentry("handleform.110: form validated");
    
    $form->toggleFrozen(true);
// now done in getquickform()
//    $form->addRecursiveFilter("trim");
    $values = $form->getValue();
    util\logentry("handleform.120: values=".var_export($values, true));
    if (is_callable($callback) === true)
    {
      util\logentry("handleform.150: calling form callback with form values");
      $res = call_user_func($callback, $values);
    }
    else
    {
      util\logentry("handleform.140: callback is not callable!");
      $res = null;
    }
    if (\PEAR::isError($res))
    {
      util\logentry("handleform.130: " . $res->toString());
    }
    return $res;
  }

/*
  $renderer = getquickformrenderer(); 
  $form->render($renderer);
  $rendered = $renderer->toArray();

  $tmpl = getsmarty();
  $tmpl->assign("form", $rendered);

  $bodycontent = array();
  $bodycontent[] = fetchpageheader($pagetitle);
  $bodycontent[] = fetchtopbar();
  $bodycontent[] = fetchsidebar();
  $bodycontent[] = $tmpl->fetch($formtemplate);
  $bodycontent[] = fetchpagefooter();

  $page = getpage($pagetitle);
  $page->addScript(STATICJAVASCRIPTURL."form.js");
  $page->addStyleSheet(STATICSKINURL . "css/form.css");
  $page->addBodyContent($bodycontent);
  $res = displaypage($page);
*/
  return false;
}

  function displayform($renderer, $title, $data=[])
  {
    $pagetemplate = isset($data["pagetemplate"]) ? $data["pagetemplate"] : "form.tmpl";
    util\logentry("bbsengine6.displayform.125: pagetemplate=".var_export($pagetemplate, true));
    $data["title"] = $title;
    $data["form"] = $renderer->toArray();
    
    displaypage($data, $pagetemplate);
  }

  /**
   * @since 20240807 copied from bbsengine5
   */
  function buildnewpasswordfieldset($form)
  {
   $fieldset = $form->addElement("fieldset");
   $fieldset->setLabel("password");
   $newpassword = $fieldset->addElement("password", "password", array("style" => "width: 200px;"))->setLabel("password:");
   $newpassword->addRule("required", "'Password' is a required field.");
   $repeatpassword = $fieldset->addElement("password", "repeatpassword", array("style" => "width: 200px;"))->setLabel("repeat password:");
   $repeatpassword->addRule("required", "'PasswordRepeat' is a required field.");
  // $newPassword->addRule("nonempty")->and_($repPassword->createRule("nonempty"))->or_($repPassword->createRule("eq", "The passwords do not match", $newPassword));
   $repeatpassword->addRule("eq", "The passwords do not match.", $newpassword);
   return;
  }
  /**
   * @since 20240807 copied from bbsengine5
   */
  function buildchangepasswordfieldset($form, $data=array())
  {
  /*
    $group = $form->addGroup()->setLabel("group");
    $group->addPassword("password")->setLabel("Password");
    $group->addPassword("repeatpassword")->setLabel("Repeat Password");
  */
   $memberid = isset($data["memberid"]) ? intval($data["memberid"]) : null;
   util\logentry("buildpasswordfieldset.100: memberid=".var_export($memberid, true));
   
   $fieldset = $form->addElement("fieldset")->setLabel("Password");
   $oldPassword = $fieldset->addElement("password", "oldPassword", array("class" => "form-control"))->setLabel("Type your old password");

   $oldPassword->addRule("empty")->or_($oldPassword->createRule("callback", "wrong password", array("callback" => "checkpassword", "arguments" => array($memberid))));
   $newPassword = $fieldset->addElement("password", "newPassword", array("class" => "form-control"))->setLabel("Type your new password");
   $repPassword = $fieldset->addElement("password", "newPasswordRepeat", array("class" => "form-control"))->setLabel("Confirm your new password");

   // this behaves exactly as it reads: either "password" and "password
   // repeat" are both empty or they should be equal

   $newPassword->addRule("empty")->and_($repPassword->createRule("empty"))->or_($repPassword->createRule("eq", "The passwords do not match", $newPassword));

   // Either new password is not given, or old password is required
   $newPassword->addRule("empty")->or_($oldPassword->createRule("nonempty", "Supply old password if you want to change it"));

   //  $newPassword->addRule("minlength", 'The password is too short', 6, HTML_QuickForm2_Rule::ONBLUR_CLIENT_SERVER);

   // No sense changing the password to the same value
   $newPassword->addRule("nonempty")->and_($newPassword->createRule("neq", "New password is the same as the old one", $oldPassword));

    return;
  }

  function checkpostflag($flagname, $post)
  {
   if (isset($post["flags"]) && \array_key_exists($flagname, $post["flags"]) === true)
   {
    return $post["flags"][$flagname];
   }
   return null;
  }

  function accesspost($op, $post)
  {
   $sysop = \bbsengine6\member\lib\checkflag("SYSOP");
   $auth = \bbsengine6\member\lib\checkflag("AUTHENTICATED");
//   $flags = $post["flags"];
//   \bbsengine6\logentry("accesspost.100: op=".var_export($op, true)." post=".var_export($post, true));
   switch ($op)
   {
    case "add":
    {
     return true;

     if ($auth === true)
     {
      return true;
     }
    }
    case "view":
    {
     \bbsengine6\util\logentry("accesspost.120: view returning true");
     return true;
    }
    case "reply":
    {
     if ($auth === true && $post["flags"]["frozen"] == false)
     {
      return true;
     }
     return false;
    }
   }
   \bbsengine6\util\logentry("accesspost.140: op=".var_export($op, true));
   return true;
  }
  
  /**
   * @since 20240810 copied from zoidweb4
   */
  function buildsiglist($sigs)
  {
    if (is_array($sigs) === true)
    {
      util\logentry("bbsengine6.buildsiglist.120: sigs is an array");
      return $sigs;
    }
    $foo = preg_split("/[, ]/",$sigs);
    $foo = array_filter($foo);
    $foo = array_values($foo);
    util\logentry("bbsengine6.buildsiglist.100: foo=".var_export($foo, true));
    return $foo;
  }

/*
  function getpost($pdo, $postid)
  {
    $sql = "select * from socrates.post where id=:id";
    $dat = ["id" => $postid];

//    \bbsengine6\logentry("dat=".var_export($dat, true));

    $stmt = $pdo->prepare($sql);
    $stmt->execute($dat);
    $post = $stmt->fetch();
    $post["actions"] = buildpostactions($pdo, $post);
//    \bbsengine6\logentry("res=".var_export($res, true));
    return $post;
  }
*/
/*
 function buildpostactions($pdo, $post)
 {
   $id = intval($post["id"]);

   $currentaction = getcurrentaction();
   $currentpage = getcurrentpage();
   $currentsite = getcurrentsite();
 //  $currentsection = getcurrentsection();

 //  logentry("buildmantraactions.100: currentaction=".var_export($currentaction, true));

   $actions = [];
   if (accesspost($pdo, "edit") === true)
   {
     $actions[] = array("href" => \config\SOCRATESURL."post-edit-{$id}", "title" => "edit", "desc" => "edit post #{$id}"); //, "class" => "fa fa-fw fa-edit");
   }
   if (accesspost($pdo, "freeze") === true)
   {
     $actions[] = array("href" => \config\SOCRATESURL."post-freeze-{$id}", "title" => "freeze", "desc" => "freeze post #{$id}"); //, "class" => "fa fa-fw fa-edit");
   }
   if (accesspost($pdo, "thaw") === true)
   {
     $actions[] = array("href" => \config\SOCRATESURL."post-thaw-{$id}", "title" => "thaw", "desc" => "thaw post #{$id}");//, "class" => "fa fa-fw fa-edit");
   }
   if (accesspost($pdo, "reply") === true)
   {
     $actions[] = array("href" => \config\SOCRATESURL."post-reply-{$id}", "title" => "reply", "desc" => "reply to post #{$id}"); // , "class" => "fa fa-fw fa-edit");
   }
   if (accesspost($pdo, "markdraft") === true)
   {
     $actions[] = array("href" => \config\SOCRATESURL."post-markdraft-{$id}", "title" => "draft", "desc" => "mark #{$id} as draft"); //, "class" => "fa fa-fw fa-edit");
   }

   return $actions;
  }
*/
  // @since 20240921 human generated ("jam")
  function getparentsig($labelpath)
  {
    util\logentry("engine.parentsig.100: labelpath=".var_export($labelpath, true));
    $labelpath = util\chopLastElement($labelpath);
    util\logentry("engine.parentsig.120: chopped path=".var_export($labelpath, true));
    if ($labelpath == "")
    {
      util\logentry("engine.getparentsig.120: labelpath is null");
      return null;
    }
    $parentsig = getsig($labelpath, false);
    if ($parentsig === null)
    {
     util\logentry("engine.getparentsig.160: parentsig is null");
     return null;
    }
    $parentsig["icon"] = "fa fa-level-up";
    util\logentry("engine.getparentsig.140: parentsig=".var_export($parentsig, true));
    return $parentsig;
  }

} /* bbsengine6 namespace */
?>
