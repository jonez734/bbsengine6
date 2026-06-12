<?php

require_once("/srv/www/bbsengine6/php/bootstrap.php");

require_once("/srv/www/vhosts/zoidtechnologies.com/html/teos/config.php");
require_once("/srv/www/vhosts/zoidtechnologies.com/html/teos/zoid6.php");
require_once("/srv/www/bbsengine6/php/engine.php");
require_once("/srv/www/vhosts/zoidtechnologies.com/html/teos/session.php");
require_once("/srv/www/vhosts/zoidtechnologies.com/html/teos/libmember.php");
require_once("/srv/www/vhosts/zoidtechnologies.com/html/teos/util.php");
require_once("PEAR.php");
require_once("Pager.php");
require_once("/srv/www/vhosts/zoidtechnologies.com/html/teos/libvulcan.php");
require_once("/srv/www/bbsengine6/php/page.php");
require_once("/srv/www/bbsengine6/php/blurb.php");
require_once("/home/opencode/data/work/bbsengine5/www/php/Markdown.inc.php");

class folder
{
  var $pdo = null;

  /**
   * @since 20151017
   */
  function getsigcount($labelpath)
  {
    $sql = "select count(id) from engine.sig where path ~ ?";
    $dat = ["{$labelpath}.*{1}"];
    $pdo = \bbsengine6\database\connect(\SYSTEMDSN);
    $stmt = $pdo->prepare($sql);
    $stmt->execute($dat);
    $res = $stmt->fetchColumn();
    // $res = $dbh->getOne($sql, array("integer"), $dat, array("text"));
    return intval($res);
  }

  function getlinkcount($labelpath)
  {
    $sql = "select count(linkid) from vulcan.map_link_sig where siglabelpath ~ ?";
    $dat = ["{$labelpath}.*{1}"];

    $pdo = \bbsengine6\database\connect(\SYSTEMDSN);
    $stmt = $pdo->prepare($sql);
    $stmt->execute($dat);
    $res = $stmt->fetchColumn();
    return intval($res);
  }

  function getpostcount($labelpath)
  {
    $sql = "select count(postid) from sophia.map_post_sig where siglabelpath ~ ?";
    $dat = ["{$labelpath}.*{1}"];

    $pdo = \bbsengine6\database\connect(\SYSTEMDSN);
    $stmt = $pdo->prepare($sql);
    $stmt->execute($dat);
    $res = $stmt->fetchColumn();
    return intval($res);
  }

  function detail()
  {
    $uri = isset($_REQUEST["uri"]) ? $_REQUEST["uri"] : null;
    logentry("teos.301: uri=".var_export($uri, true));
    $labelpath = \bbsengine6\buildlabelpath("teos", $uri);
    logentry("teos.303: labelpath=".var_export($labelpath, true));
    $sig = \bbsengine6\getsig($labelpath);
    if (\PEAR::isError($sig))
    {
      logentry("teos.300: ".var_export($sig->toString()));
      \bbsengine6\page\error("invalid uri (code: teos.300)");
      return;
    }
    if ($sig === null)
    {
      logentry("teos.302: getsigfrompath(".var_export($labelpath, true).") returned null");
      \bbsengine6\page\error("invalid uri (code: teos.302)");
      return;
    }
    $sig["totallinks"] = $this->getlinkcount($labelpath);
    $sig["totalposts"] = $this->getpostcount($labelpath);
    $sig["totalsigs"] = $this->getsigcount($labelpath);
    $sig["sigs"] = \bbsengine6\getsubsigs($labelpath);
    $bare = isset($_REQUEST["bare"]) ? true : False;
    if ($bare === true)
    {
      header('content-type: application/json; charset=utf-8');
      $tmpl = \bbsengine6\getsmarty();
      $tmpl->assign("sig", $sig);
      $data = $tmpl->fetch("sig-detail.tmpl");
      $encode = \bbsengine6\util\encodejson($data);
      $callback = isset($_REQUEST["callback"]) ? $_REQUEST["callback"] : null;
      print "{$callback} ({$encode});";
      return;
    }

    print "not working yet";
    return;
  }

/*
  function edit()
  {
    $currentmemberid = \bbsengine6\member\getcurrentid();
    
    $uri = isset($_REQUEST["uri"]) ? $_REQUEST["uri"] : null;
    
    \bbsengine6\setreturnto(TEOSURL.$uri);

    $labelpath = \bbsengine6\buildlabelpath("teos", $uri);
    $parentlabelpath = \bbsengine6\buildparentlabelpath($labelpath); // buildlabelpath(dirname($uri));
    $name = \basename($uri);

    logentry("sig.209: uri=".var_export($uri, true). " labelpath=".var_export($labelpath, true));

    $sig = getsig($labelpath);
    if (\PEAR::isError($sig))
    {
      logentry("sig.210: " . $sig->toString());
      return \PEAR::raiseError("Database Error (code: sig.210)");
    }
    
    if ($sig === null)
    {
      logentry("sig.220: labelpath ".var_export($labelpath, true)." not found");
      return \PEAR::raiseError("Input Error (code: sig.220)");
    }

    $sig["uri"] = $uri;
    
    if (accesssig("edit", $sig) === False)
    {
      displaypermissiondenied("You do not have permission to edit this sig.");
      return;
    }
    
    $sigid = getsigidfromlabelpath($labelpath);
    $form = getquickform("sig-edit");
    
    $parentpath = buildparentlabelpath($labelpath);

    $defaults = array();
    $defaults["parentlabelpath"] = $parentlabelpath; // $sig["path"];
    $defaults["title"] = $sig["title"];
    $defaults["name"] = $name; // sig["name"];
    $defaults["intro"] = $sig["intro"];

    $form->addDataSource(new HTML_QuickForm2_DataSource_Array($defaults));

    $constants = array();
    $constants["mode"] = "edit";
    $constants["uri"] = $uri;
    $constants["id"] = $sigid;

    $form->addDataSource(new HTML_QuickForm2_DataSource_Array($constants));

    buildsigfieldset($form);
    $form->addElement("submit", "blah", array("value" => "update"));

    $res = handleform($form, array($this, "update"), "edit sig");
    if (\PEAR::isError($res))
    {
      logentry("sig.230: " . $res->toString());
      return \PEAR::raiseError("error handling form (code: sig.230");
    }
    if ($res === true)
    {
      return;
    }
    
    $renderer = getquickformrenderer();
    $form->render($renderer);
  
    $res = displayform($renderer, "edit sig");
    if (\PEAR::isError($res))
    {
      logentry("sig.232: " . $res->toString());
      return \PEAR::raiseError("error displaying form (code: sig.232)");
    }
    return;
  }
  
  function update($values)
  {
    $path = $values["parentlabelpath"];
    $name = $values["name"];
    $id = intval($values["id"]);

    $uri = $values["uri"];
    $pageprotocol = isset($values["pageprotocol"]) ? $values["pageprotocol"] : "standard";

    $labelpath = normalizelabelpath($path, $name);

    $sig = array();
    $sig["title"] = $values["title"];
    $sig["intro"] = $values["intro"];
    $sig["name"] = $name;
    $sig["path"] =  $labelpath; // path + name
    $sig["lastmodified"] = "now()";
    $sig["lastmodifiedbyid"] = getcurrentmemberid();

    $res = $this->dbh->beginTransaction();
    $res = $this->dbh->autoExecute("engine.__folder", $sig, MDB2_AUTOQUERY_UPDATE, "id=".$this->dbh->quote($id, "integer"));
    if (\PEAR::isError($res))
    {
      logentry("sig.300: " . $res->toString());
      $this->dbh->rollback();
      return \PEAR::raiseError("Database Error (code: sig.300)");
    }
    $this->dbh->commit();
    displayredirectpage("Folder Updated", TEOSURL.$uri);
    return true;
  }

  function delete()
  {
    $currentmemberid = getcurrentmemberid();
    
    $uri = isset($_REQUEST["uri"]) ? $_REQUEST["uri"] : null;
    if ($uri === null)
    {
      logentry("sig.400: delete() passed null for uri");
      return \PEAR::raiseError("Input Error (code: sig.400)");
    }
    
    setreturnto(TEOSURL.$uri."delete");

    $path = buildpath($uri);
    $sig = getsig($path);
    if (\PEAR::isError($sig))
    {
      logentry("sig.410: " . $sig->toString());
      return \PEAR::raiseError("Database Error (code: sig.410)");
    }
    if ($sig === null)
    {
      logentry("sig.420: getsig(".var_export($path, true).") returned null");
      return \PEAR::raiseError("Input Error (code: sig.420)");
    }

    $sig["uri"] = $uri;
    
    if (accesssig("delete", $sig, $currentmemberid) === False)
    {
      logentry("sig.430: permission denied trying to delete ".var_export($path, true));
      displaypermissiondenied("You do not have permission to delete this sig");
      return;
    }
    $confirm = isset($_REQUEST["confirm"]) ? true : False;
    if ($confirm === False)
    {
      $title = $sig["title"];
      displaydeleteconfirmation("Are you sure you want to delete <i>{$title}</i>?", TEOSURL.$uri."delete?confirm", "Yes", TEOSURL.$uri, "No");
      return;
    }

    $res = $this->dbh->autoExecute("sig", null, MDB2_AUTOQUERY_DELETE, "path=".$this->dbh->quote($path, "text"));
    if (\PEAR::isError($res))
    {
      logentry("sig.440: ".$res->toString());
      return \PEAR::raiseError("Database Error (code: sig.440)");
    }
    displayredirectpage("Sig Deleted", "/");
    return;
  }
*/  
  function links($labelpath)
  {
    \bbsengine6\util\logentry("teos.teos.links.100: labelpath=".var_export($labelpath, true));

    $links = [];
//   $sql = "select id from vulcan.link as l where l.sigs @> array[cast(? as ltree)]";
//    $sql = "select id from vulcan.link as l where l.sigs @> array[".$this->dbh->quote($labelpath, "text")."::ltree]";
//    $sql = "select id from vulcan.link as l where ? = ".$this->dbh->quote($labelpath, "text"). " = any(l.sigs)";
    $sql = "select url from vulcan.link as l where sigs ~ ?";
/*
    if (\bbsengine6\member\lib\checkflag("SYSOP") === false)
    {
      $sql.= " and l.broken='f' and l.approved='t'";
    }
*/
    $sql.= " order by l.dateposted desc";

    $pdo = \bbsengine6\database\connect(\SYSTEMDSN);
    $stmt = $pdo->prepare($sql);
    $stmt->execute([$labelpath]);
    $res = $stmt->fetchAll();
    //$res = $this->dbh->getAll($sql, ["integer"], [$labelpath], ["text"]);
    //if (PEAR::isError($res))
    //{
    //  logentry("sig.links.540: " . $res->toString());
    //  return;
    //}

    foreach ($res as $d)
    {
//      \bbsengine6\util\logentry("teos.sig.links.100: d=".var_export($d, true));
      $url = $d["url"];
      $link = \vulcan\lib\getlinkbyurl($url);
      if (\PEAR::isError($link))
      {
        logentry("teos.links.101: ". $link->toString());
        continue;
      }
      if ($link === null)
      {
        logentry("teos.links.102: getlinkbyurl(".var_export($url, true).") returned null");
        continue;
      }
      if (\vulcan\lib\access("view", $link) === true)
      {
        if (\bbsengine6\util\toboolean($link["broken"]) === false)
        {
          $link["icon"] = "fa-link";
        }
        else
        {
          $link["icon"] = "fa-link-broken";
        }
        $links[] = $link;
      }
    }
    return $links;
  }
  
  function sigs($labelpath)
  {
    $currentmemberid = \bbsengine6\member\lib\getcurrentid();
    
    \bbsengine6\util\logentry("teos.sigs.100: ".var_export($labelpath, true));

    
//    $sql = "select s.id, s.path, s.title, public.teosurl(text(path)) as uri from engine.sig as s where s.path ~ ? order by s.title asc";
    $sql = "select * from engine.folder where folder.path ~ ? order by folder.title asc";
    $dat = ["{$labelpath}.*{1}"];
    
    $pdo = \bbsengine6\database\connect(\SYSTEMDSN);
    $stmt = $pdo->prepare($sql);
    $stmt->execute($dat);
    $res = $stmt->fetchAll();
    \bbsengine6\util\logentry("res=".var_export($res, true));
//    return [];

    $sigs = [];
    foreach ($res as $rec)
    {
//      \bbsengine6\util\logentry("sig.200: rec=".var_export($rec, true));
      $rec["actions"] = \bbsengine6\buildsigactions($rec);
      $sigs[] = $rec;
    }

    return $sigs;
  }

  function posts($labelpath)
  {
    $currentmemberid = \bbsengine6\member\lib\getcurrentid();

    \bbsengine6\util\logentry("teos.posts.100: ".var_export($labelpath, true));

    $sql = "select id from sophia.post as p, sophia.map_post_sig as m where p.id = m.postid and m.siglabelpath ~ ? and p.parentid is null order by p.dateposted desc";
    $dat = ["{$labelpath}.*{1}"];
    $pdo = \bbsengine6\database\connect(\SYSTEMDSN);
    $stmt = $pdo->prepare($sql);
    $stmt->execute($dat);
    $res = $stmt->fetchAll();

    $posts = [];
    foreach ($res as $rec)
    {
      $id = $rec["id"];
      $post = \bbsengine6\getpost($id);
      if (\bbsengine6\accesspost("view", $post, \bbsengine6\member\lib\getcurrentmoniker()) === false)
      {
        continue;
      }
      $post["id"] = $id;
      $posts[] = $post;
    }
    return $posts;
  }

/*
  function amznitems($sigpath)
  {
    $sql = "select id from agora.amznitem where sigs ~ ? order by datecreated desc";
//    $sql = "select engine.node.* from engine.node, engine.map_node_sig where engine.node.id = engine.map_node_sig.nodeid and engine.map_node_sig.sigpath=?";
    $dat = [$sigpath];
    $pdo = \bbsengine6\database\connect(\zoid6\SYSTEMDSN);
    $stmt = $pdo->prepare($sql);
    $stmt->execute($dat);
    $res = $stmt->fetchAll();
    //$res = $this->dbh->getAll($sql, null, $dat, ["text"]);
    //if (PEAR::isError($res))
    //{
    //  logentry("teos.sig.amznitems.100: " . $res->toString());
    //  return [];
    //}

//    logentry("amznitems.100: sigpath=".var_export($sigpath, true)); // . " res=".var_export($res, true));

    $amznitems = [];
    foreach ($res as $rec)
    {
      $id = $rec["id"];
      $amznitem = getamznitembynodeid($id);
      if (accessamznitem("view", $amznitem) === false)
      {
        continue;
      }
      $comments = getamznitemcomments($id);
      if (\PEAR::isError($comments))
      {
          logentry("teos.amznitems.120: " . $comments->toString());
          $comments = [];
      }
      $amznitem["comments"] = $comments;
      $amznitems[] = $amznitem;
    }
    return $amznitems;
  }
*/

  /**
   * Build topbar choices for teos
   * Includes default zoid6 navigation plus teos-specific actions based on permissions
   *
   * @param array|null $currentsig Current sig object with permissions
   * @return array Choices array formatted for topbar display
   */
  private function buildchoices($currentsig = null)
  {
    $choices = [];
    
    // Add teos-specific actions if sig is provided
    if ($currentsig !== null)
    {
      if (\bbsengine6\accesssig("link.add", $currentsig) === true)
      {
        $choices[] = [
          "name" => "link.add",
          "title" => "add link",
          "url" => TEOSURL . $currentsig['uri'] . "add-link",
          "desc" => "add a link to this sig"
        ];
      }
      if (\bbsengine6\accesssig("post.add", $currentsig) === true)
      {
        $choices[] = [
          "name" => "post.add",
          "title" => "add post",
          "url" => TEOSURL . $currentsig['uri'] . "add-post",
          "desc" => "add a post to this sig"
        ];
      }
      if (\bbsengine6\accesssig("add", $currentsig) === true)
      {
        $choices[] = [
          "name" => "folder.add",
          "title" => "add sig",
          "url" => TEOSURL . $currentsig['uri'] . "add-sig",
          "desc" => "add a subsig to this sig"
        ];
      }
      if (\bbsengine6\accesssig("edit", $currentsig) === true)
      {
        $choices[] = [
          "name" => "folder.edit",
          "title" => "edit sig",
          "url" => TEOSURL . $currentsig['uri'] . "edit-sig",
          "desc" => "edit sig"
        ];
      }
    }
    
    // Pass to zoid6 which adds default navigation (teos, achilles, asimov, www)
    return \zoid6\buildchoices($choices);
  }

  function browse()
  {
    $uri = isset($_REQUEST["uri"]) ? $_REQUEST["uri"] : null;
    $normalizeduri = \bbsengine6\normalizeuri($uri);
    if ($normalizeduri == "/")
    {
      $labelpath = defined('TEOSLABELPREFIX') ? TEOSLABELPREFIX : "top";
    }
    else
    {
      $labelpath = \bbsengine6\buildlabelpath("teos", $normalizeduri);
    }
    
    \bbsengine6\util\logentry("browse.100: uri=".var_export($uri, true). " labelpath=".var_export($labelpath, true));
    \bbsengine6\setreturnto(\bbsengine6\getcurrenturi());

    \bbsengine6\util\logentry("browse.120: trace");

    if ($labelpath === (defined('TEOSLABELPREFIX') ? TEOSLABELPREFIX : "top"))
    {
      \bbsengine6\setcurrentpage("index");
    }
    else
    {
      \bbsengine6\setcurrentpage($labelpath);
    }

    if (strpos($labelpath, "top.eros") === 0 && \bbsengine6\member\lib\checkflag("EROS") === False)
    {
      \bbsengine6\displaypermissiondenied();
      return;
    }

//    $normalizeduri = $normalizeduri."/";
    \bbsengine6\util\logentry("teos.teos.browse.120: uri=".var_export($uri, true)." labelpath=".var_export($labelpath, true)." normalizeduri=".var_export($normalizeduri, true));
/*
    if ($uri != $normalizeduri)
    {
      logentry("sig.browse.150: adding trailing slash!");
      displayredirectpage("OK", joinpath(TEOSURL, $normalizeduri), 0);
      return;
    }
*/
    \bbsengine6\setcurrentaction("browse");


    $currentsig = \bbsengine6\getsig($labelpath);
    \bbsengine6\util\logentry("teos.browse.50: currentsig=".var_export($currentsig, true));
    if (\PEAR::isError($currentsig))
    {
      \bbsengine6\util\logentry("teos.browse.100:".$currentsig->toString());
      return PEAR::raiseError("Database Error (code: teos.browse.44)");
    }
    if ($currentsig === null)
    {
      $filepath = TEOSFILEPATH . $uri;

      if (is_file($filepath . ".md")) {
        $this->display_markdown_file($filepath . ".md", $uri);
        return;
      }

      if (is_dir($filepath)) {
        $this->display_directory_listing($filepath, $uri);
        return;
      }

      $data = [];
      $data["choices"] = $this->buildchoices();
      \bbsengine6\page\error("folder not found", 404, "folder not found", "errormessage.tmpl", $data);
      return;
    }

    $currentsig["uri"] = $uri;

    $currentmemberid = \bbsengine6\member\lib\getcurrentid();
    
    $actions = [];
    $actions["folder.edit"] = \bbsengine6\accesssig("folder.edit", $currentsig);
    $actions["folder.add"] = \bbsengine6\accesssig("folder.add", $currentsig);
    $actions["folder.delete"] = \bbsengine6\accesssig("folder.delete", $currentsig);
    $currentsig["actions"] = $actions;
    
    $data = [];
//    $data["sigs"] = \bbsengine6\getsubsigs($labelpath); // $this->sigs($labelpath);

    $currentsig["links"] = $this->links($labelpath);

    //$posts = $this->posts($labelpath);
    //$data["posts"] = $posts;
    $data["posts"] = [];

    $data["amznitems"] = [];
    if (\bbsengine6\member\lib\checkflag("AUTHENTICATED") == true)
    {
      $amznitems = $this->amznitems($labelpath);
      $data["amznitems"] = $amznitems;
    }

    \bbsengine6\setreturnto(\bbsengine6\getcurrenturi());

    $breadcrumbs = \bbsengine6\buildbreadcrumbs($labelpath, false);
//    logentry("teos.sig.200: breadcrumbs=".var_export($breadcrumbs, True));
    
    $sidebar = [];
    if (\bbsengine6\accesssig("link.add", $currentsig) === true)
    {
      $sidebar[] = array("name" => "link.add", "url" => TEOSURL."{$uri}add-link", "desc" => "add a link to this sig", "title" => "add link");
    }
    if (\bbsengine6\accesssig("post.add", $currentsig) === true)
    {
      $sidebar[] = array("name" => "post.add", "url" => TEOSURL."{$uri}add-post", "desc" => "add a post to this sig", "title" => "add post");
    }
    if (\bbsengine6\accesssig("add", $currentsig) === true)
    {
      $sidebar[] = array("name" => "folder.add", "url" => TEOSURL."{$uri}add-sig", "desc" => "add a subsig to this sig", "title" => "add sig");
    }
    if (\bbsengine6\accesssig("edit", $currentsig) === true)
    {
      $sidebar[] = array("name" => "folder.edit", "url" => TEOSURL."{$uri}edit-sig", "desc" => "edit sig", "title" => "edit sig");
    }
    
    $currentsigpath = $currentsig["path"];
    $parentsig = \bbsengine6\getparentsig($currentsigpath);
    if ($parentsig === null)
    {
      \bbsengine6\util\logentry("-----> teos.folder.browse.300: parentsig is null");
    }
    
//    \bbsengine6\util\logentry("teos.sig.browse.320: parentsig=".var_export($parentsig, true));
//    \bbsengine6\util\logentry("teos.sig.browse.200: currentsigpath=".var_export($currentsigpath, true));
    array_unshift($currentsig["sigs"], $parentsig);
//    \bbsengine6\util\logentry("teos.sig.browse.220: data.sigs.0=".var_export($data["sigs"][0], true));
    $data["currentsig"] = $currentsig;

    $data["breadcrumbs"] = $breadcrumbs;
    $data["choices"] = $this->buildchoices($currentsig);
//    $data["posts"] = []; // $posts;
//    $data["links"] = $links;
//    $data["agora"] = []; // $amznitems;
    $data["sidebar"] = $sidebar;
    return \bbsengine6\displaypage($data, "browse.tmpl");
  }

/*
  function add()
  {
    if (\bbsengine6\accesssig("add") === False)
    {
      \bbsengine6\logentry("sig.25: permission denied. op=add memberid=".var_export($currentmemberid, true)." labelpath=".var_export($labelpath, true));
      \bbsengine6\displaypermissiondenied("You do not have permission to add sigs here. (code: sig.25)");
      return;
    }

    \bbsengine6\setcurrentpage("sig");
    \bbsengine6\setcurrentaction("add");

    $uri = isset($_REQUEST["uri"]) ? $_REQUEST["uri"] : null;
    $labelpath = \bbsengine6\buildlabelpath("teos", $uri);
    
    $currentmemberid = \bbsengine6\getcurrentmemberid();
    
    \bbsengine6\setreturnto(TEOSURL.$uri);
    
    \bbsengine6\logentry("sig.49: labelpath=".var_export($labelpath, true));

    $form = \bbsengine6\getquickform("teos-add");
    \bbsengine6\buildsigfieldset($form);
    $form->addElement("submit", "addsig", array("value" => "add"));

    $defaults = array();
    $defaults["parentlabelpath"] = $labelpath;

    $form->addDataSource(new HTML_QuickForm2_DataSource_Array($defaults));

    $const = array();
    $const["mode"] = "add";
    $const["memberid"] = \bbsengine6\getcurrentmemberid();
    $form->addDataSource(new HTML_QuickForm2_DataSource_Array($const));

    $renderer = \bbsengine6\getquickformrenderer();
    $form->render($renderer);
    $res = \bbsengine6\handleform($form, array($this, "insert"), "add sig");
    if (\PEAR::isError($res))
    {
      \bbsengine6\logentry("sig.300: ". $res->toString());
      return \PEAR::raiseError("unable to handle form. (code: sig.300)");
    }
    if ($res === true)
    {
      \bbsengine6\logentry("sig.302: handleform(...) returned true");
      return;
    }
    $res = \bbsengine6\displayform($renderer, "add sig");
    return;
  }

  function insert($values)
  {
    $title = $values["title"];
    $labelpath = $values["parentlabelpath"];    
    $name = !empty($values["name"]) ? $values["name"] : buildlabel($title);

    logentry("sig.22: name=".var_export($name, true)." title=".var_export($title, true)." labelpath=".var_export($labelpath, true));

    $currentmemberid = \bbsengine6\getcurrentmemberid();
    
    $sig = array();
    $sig["path"] = \bbsengine6\normalizelabelpath($labelpath, $name);
    $sig["title"] = $title;
    $sig["intro"] = $values["intro"];
    $sig["name"] = $name;
    $sig["postedbyid"] = $currentmemberid;
    $sig["dateposted"] = "now()";
    $sig["lastmodified"] = "now()";
    $sig["lastmodifiedbyid"] = $currentmemberid;
    
    $res = $this->dbh->autoExecute("engine.__folder", $sig, MDB2_AUTOQUERY_INSERT);
    if (\PEAR::isError($res))
    {
      \bbsengine6\logentry("sig.28: " . $res->toString());
      return \PEAR::raiseError("Error Inserting Folder (code: sig.28)");
    }
    
    $siguri = \bbsengine6\normalizelabelpath($labelpath, $name);
    $siguri = str_replace(".", "/", $siguri);
    \bbsengine6\displayredirectpage("SIG added", TEOSURL.$siguri);
    return true;
  }
*/
  function blurb()
  {
    $path = isset($_REQUEST["path"]) ? $_REQUEST["path"] : "";
    $path = trim($path, "/");

    if (empty($path))
    {
      return $this->browse();
    }

    $parts = explode("/", $path);
    if (count($parts) < 2)
    {
      return \bbsengine6\page\error("Invalid teos blurb URL", 404);
    }

    $sigpath = implode(".", array_slice($parts, 0, -1));
    $filename = array_pop($parts);

    if (!preg_match("/^(.+)-blurb\\.md$/", $filename, $matches))
    {
      return \bbsengine6\page\error("Invalid blurb filename", 404);
    }

    $blurbname = $matches[1];
    $blurbdir = defined('\config\BLURBDIR') ? \config\BLURBDIR : "/srv/www/blurbs/teos/";
    $blurbfile = $blurbdir . $sigpath . "/" . $blurbname . "-blurb.md";

    if (!file_exists($blurbfile))
    {
      return \bbsengine6\page\error("Blurb not found: " . htmlspecialchars($blurbfile), 404);
    }

    $content = file_get_contents($blurbfile);
    $content = Markdown::defaultTransform($content);

    $sigpathltree = str_replace(".", "_", $sigpath);
    $sql = "select b.id, b.kind, b.attributes, b.datecreated, b.createdbymoniker 
            from engine.blurb b 
            join engine.map_blurb_sig m on b.id = m.blurbid 
            where m.sigpath = :sigpath 
            and b.attributes->>'name' = :blurbname
            limit 1";
    $dat = ["sigpath" => $sigpathltree, "blurbname" => $blurbname];

    try {
      $pdo = \bbsengine6\database\connect(\SYSTEMDSN);
      $stmt = $pdo->prepare($sql);
      $stmt->execute($dat);
      $blurb = $stmt->fetch();
    } catch (\Throwable $e) {
      \bbsengine6\util\echo_traceback("teos.blurb.100: " . $e->getMessage());
      $blurb = null;
    }

    if (function_exists('bbsengine6\blurb\buildbreadcrumbs')) {
      $breadcrumbs = \bbsengine6\blurb\buildbreadcrumbs($sigpathltree);
    } else {
      $breadcrumbs = [];
    }

    \bbsengine6\setcurrentpage("teos/" . $sigpath . "/" . $blurbname . "-blurb.md");

    $data = [];
    $data["content"] = $content;
    $data["blurb"] = $blurb;
    $data["breadcrumbs"] = $breadcrumbs;

    return \bbsengine6\displaypage($data, "page-markdown.tmpl");
  }

  function main()
  {
    \bbsengine6\session\start();

    \bbsengine6\setcurrentsite(\config\SITENAME);
    \bbsengine6\setcurrentpage("index");

    $mode = isset($_REQUEST["mode"]) ? $_REQUEST["mode"] : null;
//    logentry("sig.500: mode=".var_export($mode, True));
    switch($mode)
    {
      case "browse":
      {
        $r = $this->browse();
        break;
      }
      case "add":
      {
        $r = $this->add();
        break;
      }
      case "edit":
      {
        $r = $this->edit();
        break;
      }
      case "delete":
      {
        $r = $this->delete();
        break;
      }
      case "detail":
      {
        $r = $this->detail();
        break;
      }
      case "blurb":
      {
        $r = $this->blurb();
        break;
      }
      default:
      {
        $r = $this->browse();
        break;
      }
    }
    return $r;
  }

  function display_markdown_file($filepath, $uri)
  {
    $content = file_get_contents($filepath);

    $metadata = [];
    if (preg_match('/^---\s*\n(.*?)\n---/s', $content, $matches)) {
      $metadata = $this->parse_yaml_frontmatter($matches[1]);
      $content = preg_replace('/^---\s*\n.*?\n---\s*\n/s', '', $content);
    }

    $html = Markdown::defaultTransform($content);

    $title = isset($metadata['title']) ? htmlspecialchars($metadata['title']) : basename($filepath, '.md');
    $date = isset($metadata['date']) ? htmlspecialchars($metadata['date']) : '';

    echo "<html><head><title>" . $title . "</title></head><body>";
    if ($date) {
      echo "<p class=\"date\">" . $date . "</p>";
    }
    echo $html;
    echo "</body></html>";
  }

  function display_directory_listing($dirpath, $uri)
  {
    $files = glob($dirpath . "/*.md");
    sort($files);

    $title = htmlspecialchars(ucfirst(basename($uri)));
    echo "<html><head><title>" . $title . "</title></head><body>";
    echo "<h1>" . $title . "</h1>";
    echo "<ul>";

    foreach ($files as $filepath) {
      $filename = basename($filepath, '.md');
      $fileuri = $uri . "/" . $filename;

      $metadata = [];
      $display_title = $filename;

      $filecontent = file_get_contents($filepath);
      if (preg_match('/^---\s*\n(.*?)\n---/s', $filecontent, $matches)) {
        $metadata = $this->parse_yaml_frontmatter($matches[1]);
        if (isset($metadata['title'])) {
          $display_title = htmlspecialchars($metadata['title']);
        }
      }

      echo "<li><a href=\"/teos/" . htmlspecialchars($fileuri) . "\">" . $display_title . "</a></li>";
    }

    echo "</ul>";
    echo "</body></html>";
  }

  function parse_yaml_frontmatter($yaml)
  {
    $metadata = [];
    $lines = explode("\n", $yaml);
    foreach ($lines as $line) {
      if (preg_match('/^(\w+):\s*(.*)$/', $line, $matches)) {
        $key = trim($matches[1]);
        $value = trim($matches[2]);
        $metadata[$key] = $value;
      }
    }
    return $metadata;
  }
};

$a = new folder();
$b = $a->main();
if (\PEAR::isError($b))
{
  \bbsengine6\util\logentry("teos.100: " . $b->toString());
  $data = [];
  $choices = [];
  $data["choices"] = \zoid6\buildchoices($choices);
  \bbsengine6\page\error($b->getMessage(), 500, "error", "errormessage.tmpl", $data);
}
?>
