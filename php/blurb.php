<?php

namespace bbsengine6\blurb
{
  /**
   * return a list of dictionaries with keys 'title' and 'uri' for each part of $sigpath (ltree)
   *
   * @since 20151118
   */
  function buildbreadcrumbs($sigpath, $skiptop=true, $hidepath=null)
  {
  //  logentry("bbsengine4.buildbreadcrumbs.100: sigpath=".var_export($sigpath, true)." skiptop=".var_export($skiptop, true));
    $sql = "select title, path, uri from engine.sig where path @> :sigpath order by path asc";
    $dat = ["sigpath" => $sigpath];
    $dbh = \bbsengine6\database\connect(SYSTEMDSN);
    $stmt = $dbh->prepare($sql);
    $stmt->execute($dat);
    if ($stmt->rowCount() == 0)
    {
      return null;
    }
    $res = $stmt->fetchAll();

    $crumbs = [];
    foreach ($res as $sig)
    {
      if ($skiptop === true && $sig["path"] === "top")
      {
//        array_shift($res);
        continue;
      }
      if (is_string($hidepath) === true && $sig["path"] === $hidepath)
      {
        continue;
      }

      $crumbs[] = $sig;
    }
    return $crumbs;
  }

    /**
     * @since 20230707 copied from zoidweb4
     */
    function buildbreadcrumblist($blurbid)
    {
      $dbh = \bbsengine6\database\connect(SYSTEMDSN);
/*
      if (PEAR::isError($dbh))
      {
        logentry("buildbreadcrumblist.10: " . $dbh->toString());
        return $dbh;
      }
*/
      $sql = "select unnest(sigs) as path, title from engine.blurb where id=:blurbid";
      $dat = ["blurbid" => $blurbid];
      
      $stmt = $dbh->prepare($sql);
      $stmt->execute($dat);
      if ($stmt->rowCount() == 0)
      {
          return [];
      }
      $res = $stmt->fetchAll();
      $breadcrumbs = [];
      foreach ($res as $rec)
      {
        $siglabelpath = $rec["path"];
        
        $breadcrumbs[] = buildbreadcrumbs($siglabelpath);
      }
    //  logentry("buildbreadcrumblist.100: breadcrumbs=".var_export($breadcrumbs, True));
      return $breadcrumbs;
    }
};

?>
