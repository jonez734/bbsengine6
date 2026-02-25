<?php

/**
 * handles display of the index page
 *
 * @package bbsengine6
 */

/**
 * application config file 
 */
require_once("config.php");
//require_once("bbsenginedotorg.php");
require_once("engine.php");
require_once("database.php");
require_once("session.php");

/**
 * handle display of index page.
 *
 * @package bbsenginedotorg
 */
class index
{
  var $dbh = null;
  
  function _latestrelease()
  {
    $sql = "select releaseid from repo.latestrelease where projectname=:projectname";
    $stmt = $this->dbh->prepare($sql);
    $dat = ["projectname" => CURRENTPROJECTNAME];
    $stmt->execute($dat);
    $res = $stmt->fetch();
    $res = $this->dbh->getOne($sql);
//    logentry("index.99: res=".var_export($res, True));
    if (PEAR::isError($res))
    {
      logentry("index.100: " . $res->toString());
    }
    $release = array();
    $files = [];
    if ($res !== null)
    {
      $sql = "select * from repo.file as f where f.releaseid=:releaseid and f.hidden='f' order by f.filepath";
      $dat = ["releaseid" => $releaseid];
      $stmt = $this->dbh->prepare($sql);
      $stmt->execute($dat);
      if ($stmt->rowcount() === 0)
      {
        return null;
      }
      $res = $this->dbh->fetchAll();
      foreach ($res as $rec)
      {
        $file = $rec;
        $file["name"] = basename($rec["filepath"]);
        
        $files[] = $file;
      }
      
      $release["files"] = $files;
    }
    
    return $release;
  }

  function docsort($a, $b)
  {
    if ($a["updatedepoch"] === $b["updatedepoch"])
    {
      return 0;
    }
    if ($a["updatedepoch"] > $b["updatedepoch"])
    {
      return -1;
    }
    return 1;
  }

  function main()
  {
    $this->dbh = \bbsengine6\database\connect(\config\SYSTEMDSN);

    \bbsengine6\session\start();
    
    \bbsengine6\setcurrentsite("bbsenginedotorg");
    \bbsengine6\setcurrentpage("index");
    \bbsengine6\setreturnto(\bbsengine6\getcurrenturi());
    
    $latestrelease = null;

    $tmpl = \bbsengine6\getsmarty();

    $docs = [];
    $docs[] = ["title" => "handbook", "url" => \config\HANDBOOKURI, "updatedepoch" => filemtime(\config\HANDBOOKDIR)];
    $docs[] = ["title" => "API documentation", "url" => \config\APIDOCSURI, "updatedepoch" => filemtime(\config\APIDOCSDIR)];
    $docs[] = ["title" => "changelog", "url" => \config\CURRENTHANDBOOKURI . "CHANGELOG.txt", "updatedepoch" => filemtime(\config\CHANGELOG)];
    $docs[] = ["title" => "readme", "url" => \config\CURRENTHANDBOOKURI . "README.md", "updatedepoch" => filemtime(\config\README)];
    $docs[] = ["title" => "install", "url" => \config\CURRENTHANDBOOKURI. "INSTALL.md", "updatedepoch" => filemtime(\config\INSTALL)];
    $docs[] = ["title" => "releasenotes", "url" => \config\CURRENTHANDBOOKURI. "/current/RELEASENOTES.md", "updatedepoch" => filemtime(\config\RELEASENOTES)];
    
    usort($docs, [$this, "docsort"]);

    $data = [];
    $data["latestrelease"] = null; //["files" => []]; // $latestrelease;
    $data["docs"] = $docs;
//    $data["pagetemplate"] = "index.tmpl";

    $res = \bbsengine6\displaypage($data, "index.tmpl");
    return $res;
  }
}

$i = new index();
$r = $i->main();
?>
