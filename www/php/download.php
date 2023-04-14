<?php

require_once("config.php");
require_once("bbsenginedotorg.php");
require_once("bbsengine3.php");

require_once("HTTP/Download.php");

class download
{
  function main()
  {
    session_start();
    
    $dbh = dbconnect(SYSTEMDSN);
    if (PEAR::isError($dbh))
    {
      logentry("download.10: " . $dbh->toString());
      return PEAR::raiseError("Database Error (code: download.10)");
    }

    $name = isset($_REQUEST["name"]) ? $_REQUEST["name"] : null;

    $sql = "select * from repo.file where filepath=?";
    $dat = array($name);

    $res = $dbh->getRow($sql, null, $dat, array("text"));

    if (PEAR::isError($res))
    {
      logentry("download.12: " . $res->toString());
      return PEAR::raiseError("Database Error (code: download.12)");
    }

    if ($res === null)
    {
      logentry("download.14: filepath not found name=".var_export($name, true));
      return PEAR::raiseError("Input Error (code: download.14)");
    }

    if (accessfile("download", $res) === False)
    {
      logentry("download.16: permission denied downloading {$name}");
      displaypermissiondenied();
      return;
    }
    $fileid = $res["id"];
    $filepath = $res["filepath"];
    logentry("download.42: filepath=".var_export($filepath, true));
    $options = array(
      "file" => RELEASESDIR . $filepath,
      "contentdisposition" => array(HTTP_DOWNLOAD_ATTACHMENT, basename($filepath))
    );
    logentry("download.44: options=".var_export($options, true));
    $dl = new HTTP_Download($options);
    $res = $dl->guessContentType();
    if (PEAR::isError($res))
    {
      logentry("download.16: " . $res->toString());
      return PEAR::raiseError("System Error (code: download.16)");
    }
    $res = $dl->send(false);
    if (PEAR::isError($res))
    {
      logentry("download.18: " . $res->toString());
      return PEAR::raiseError("System Error (code: download.18)");
    }

    $file = array();
    $file["totaldownloads"] = $res["totaldownloads"] + 1;
    $file["datelastdownloaded"] = "now()";
    $file["lastdownloadedbyid"] = getcurrentmemberid();

    $res = $dbh->autoExecute("__file", $file, MDB2_AUTOQUERY_UPDATE, "id=".$dbh->quote($fileid, "integer"));
    $dbh->disconnect();
    
    return;
    
  }
};

$a = new download();
$b = $a->main();
if (PEAR::isError($b))
{
  logentry("download.100: " . $b->toString());
  displayerrormessage($b->getMessage());
}
?>
