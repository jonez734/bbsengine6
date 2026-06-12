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
    try {
      $sql = "select title, path, uri from engine.sig where path @> :sigpath order by path asc";
      $dat = ["sigpath" => $sigpath];
      $dbh = \bbsengine6\database\connect(\bbsengine6\member\lib\getDSN());
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
        $dbh = \bbsengine6\database\connect(\bbsengine6\member\lib\getDSN());
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

    /**
     * Get the content directory for blurb files
     *
     * @since 2026
     */
    function getcontentdir(): string
    {
      $contentdir = getenv("BBSENGINE6_BLURB_CONTENT_DIR");
      if ($contentdir === false || $contentdir === "")
      {
        $contentdir = "/var/bbsengine6/blurb_content";
      }
      return $contentdir;
    }

    /**
     * Read blurb content from filesystem
     *
     * @since 2026
     */
    function getcontent(int $blurbid): ?string
    {
      $contentdir = getcontentdir();
      $filepath = $contentdir . "/" . $blurbid . ".txt";

      if (!file_exists($filepath))
      {
        return null;
      }

      return file_get_contents($filepath);
    }

    /**
     * Get a list of blurbs from the engine.blurb view
     *
     * @since 2026
     * @param int $offset Offset for pagination
     * @param int $limit Number of blurbs to return
     * @return array Array of blurb dictionaries
     */
    function getlist(int $offset = 0, int $limit = 20): array
    {
      try {
        $sql = "select * from engine.blurb order by datecreated desc offset :offset limit :limit";
        $dat = ["offset" => $offset, "limit" => $limit];
        $dbh = \bbsengine6\database\connect(\bbsengine6\member\lib\getDSN());
        $stmt = $dbh->prepare($sql);
        $stmt->execute($dat);
        return $stmt->fetchAll();
      } catch (\Throwable $e) {
        \bbsengine6\util\echo_traceback("blurb.getlist.100: " . $e->getMessage());
        return [];
      }
    }

    /**
     * Get a single blurb by ID
     *
     * @since 2026
     * @param int $id Blurb ID
     * @return array|null Blurb dictionary or null if not found
     */
    function getbyid(int $id): ?array
    {
      try {
        $sql = "select * from engine.blurb where id = :id";
        $dat = ["id" => $id];
        $dbh = \bbsengine6\database\connect(\bbsengine6\member\lib\getDSN());
        $stmt = $dbh->prepare($sql);
        $stmt->execute($dat);
        if ($stmt->rowCount() == 0)
        {
          return null;
        }
        $blurb = $stmt->fetch();

        $attrs = $blurb["attributes"];
        if (is_array($attrs) && isset($attrs["contentpath"]))
        {
          $contentpath = $attrs["contentpath"];
          if (file_exists($contentpath))
          {
            $blurb["content"] = file_get_contents($contentpath);
          }
          else
          {
            $blurb["content"] = getcontent($id);
          }
        }
        else
        {
          $blurb["content"] = getcontent($id);
        }

        return $blurb;
      } catch (\Throwable $e) {
        \bbsengine6\util\echo_traceback("blurb.getbyid.100: " . $e->getMessage());
        return null;
      }
    }

    /**
     * Get total count of blurbs
     *
     * @since 2026
     * @return int Total number of blurbs
     */
    function getcount(): int
    {
      try {
        $sql = "select count(*) as cnt from engine.blurb";
        $dbh = \bbsengine6\database\connect(\bbsengine6\member\lib\getDSN());
        $stmt = $dbh->query($sql);
        $row = $stmt->fetch();
        return (int)$row["cnt"];
      } catch (\Throwable $e) {
        \bbsengine6\util\echo_traceback("blurb.getcount.100: " . $e->getMessage());
        return 0;
      }
    }
};

?>
