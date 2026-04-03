<?php

use function \bbsengine6\member\lib\getDSN;

namespace bbsengine6\blurb
{
  /**
   * return a list of dictionaries with keys 'title' and 'uri' for each part of $sigpath (ltree)
   *
   * @since 20151118
   */
  function buildbreadcrumbs($sigpath, $skiptop=true, $hidepath=null)
  {
    try {
      $sql = "select title, path, uri from engine.sig where path @> :sigpath order by path asc";
      $dat = ["sigpath" => $sigpath];
      $dbh = \bbsengine6\database\connect(getDSN());
      $stmt = $dbh->prepare($sql);
      $stmt->execute($dat);
      if ($stmt->rowCount() == 0)
      {
        return [];
      }
      $res = $stmt->fetchAll();

      $crumbs = [];
      foreach ($res as $sig)
      {
        if ($skiptop === true && $sig["path"] === "top")
        {
          continue;
        }
        if (is_string($hidepath) === true && $sig["path"] === $hidepath)
        {
          continue;
        }

        $crumbs[] = $sig;
      }
      return $crumbs;
    } catch (\Throwable $e) {
      \bbsengine6\util\echo_traceback("blurb.buildbreadcrumbs.100: " . $e->getMessage());
      return [];
    }
  }

    /**
     * @since 20230707 copied from zoidweb4
     */
    function buildbreadcrumblist($blurbid)
    {
      try {
        $dbh = \bbsengine6\database\connect(getDSN());
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
        return $breadcrumbs;
      } catch (\Throwable $e) {
        \bbsengine6\util\echo_traceback("blurb.buildbreadcrumblist.100: " . $e->getMessage());
        return [];
      }
    }
};

?>
