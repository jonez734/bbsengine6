<?php

require_once("config.php");
require_once("bbsenginedotorg.php");
require_once("bbsengine4.php");

require_once("Calendar/Calendar.php");
require_once("Calendar/Year.php");
require_once("Calendar/Month.php");

class archive
{
  var $dbh = null;
  
  function getfilesforreleaseid($releaseid)
  {
    $sql = "select * from repo.file as f where f.releaseid=?";
    $dat = array($releaseid);
    $res = $this->dbh->getAll($sql, null, $dat, array("integer"));
    if (PEAR::isError($res))
    {
      logentry("archive.12: " . $res->toString());
      return PEAR::raiseError($res);
    }
    return $res;
  }

  function displayyear($y)
  {
    $y = intval($y);
    $yy = $y + 1;
    $foo = sprintf("%04d-01-01", $y);
    $sql = <<<SQL
select s2.month, coalesce(count, 0) as count, to_char(('{$y}-'||s2.month||'-01')::date,'Month') as monthname
from
  (select extract(month from datereleased) as month, count(r.datereleased)
   from repo.release as r, repo.project as p
   where datereleased >= '{$foo}' and datereleased < (timestamptz '{$foo}' + interval '1 year')
   and p.hidden='f' and r.hidden='f' and p.id = r.projectid and (p.name='bbsengine' or p.name='bbsengine3' or p.name='bbsengine4')
   group by extract(month from datereleased)) as s1
right join generate_series(1, 12) as s2(month) on (s1.month = s2.month)
order by s2.month;
SQL;
    $res = $this->dbh->getAll($sql);
    if (PEAR::isError($res))
    {
      logentry("archive.displayyear.0: " . $res->toString());
      return $res;
    }

    $year = new Calendar_Year($y);
    $year->build();
    
    $data = [];
    $data["months"] = $res;
    $data["year"] = $y;
    $data["pagetemplate"] = "archive-year.tmpl";
/*
    $page = getpage("bbsenine3 release archive - {$y}");
    $page->addBodyContent(fetchpageheader());

    $months = $year->fetchAll();
    $tmpl = getsmarty();
    $tmpl->assign("months", $res);
    $tmpl->assign("year", $y);
    $page->addBodyContent($tmpl->fetch("archive-year.tmpl"));
    $page->addBodyContent(fetchpagefooter());
    $page->display();
*/
    displaypage(null, $data);
    return;
  }

  function displaymonth($y, $m)
  {
    $y = intval($y);
    $yy = $y + 1;

    $m = intval($m);
    $mm = $m + 1;

    $thisMonth = new Calendar_Month($y, $m);
    $thisMonth->adjust();
    $thisMonth->build();

    if ($thisMonth->thisMonth() == 12)
    {
      $nextMonth = new Calendar_Month($y+1, $thisMonth->nextMonth());
    }
    else
    {
      $nextMonth = new Calendar_Month($y, $thisMonth->nextMonth());
    }
    $nextMonth->adjust();
    $nextMonth->build();
    
    $daysInMonth = $thisMonth->size();

    $yy = $nextMonth->thisYear();
    $mm = sprintf("%02d", $nextMonth->thisMonth());

    $foo = sprintf("%04d-%02d-01", $y, $m);
    $sql = <<<SQL
select s2.day, coalesce(count, 0) as count, to_char(s2.day, 'FM00') as twodigitday
from 
  (select extract(day from r.datereleased) as day, 
    count(r.datereleased)
  from repo.release as r, repo.project as p
  where datereleased >= '{$foo}' and datereleased < (timestamptz '{$foo}' + interval '1 month') 
  and p.hidden='f' and r.hidden='f' and p.id = r.projectid and (p.name='bbsengine' or p.name='bbsengine3' or p.name='bbsengine4')
  group by extract(day from datereleased)) as s1 
left join generate_series(1, {$daysInMonth}) as s2(day) on (s1.day = s2.day) 
order by s2.day;
SQL;
    $res = $this->dbh->getAll($sql);
    if (PEAR::isError($res))
    {
      logentry("archive.displaymonth.0: " . $res->toString());
      return $res;
    }

    $month = new Calendar_Month($y, $m);
    $month->adjust();
    $month->build();
    
    $cal = array();
    $cal["shortmonthname"] = date("M", $month->getTimeStamp());
    $cal["longmonthname"] = date("F", $month->getTimeStamp());
    $cal["twodigitmonth"] = sprintf("%02d", $month->thisMonth());
    $cal["year"] = date("Y", $month->getTimeStamp());
    
    $days = $month->fetchAll();

    $heading = date("M Y", $thisMonth->getTimeStamp());

    $data = [];
    $data["heading"] = $heading;
    $data["days"] = $res;
    $data["cal"] = $cal;
    $data["pagetemplate"] = "archive-month.tmpl";
    
/*
    $page = getpage("bbsengine3 release archive {$heading}");
    $page->addBodyContent(fetchpageheader());
    $tmpl = getsmarty();
    $tmpl->assign("heading", $heading);
    $tmpl->assign("days", $res);
    $tmpl->assign("cal", $cal);
    $page->addBodyContent($tmpl->fetch("archive-month.tmpl"));
    $page->addBodyContent(fetchpagefooter());
    $page->display();
*/
    displaypage(null, $data);
    return;
  }

  function displayday($y, $m, $d)
  {
    $foo = sprintf("%04d-%02d-%02d", $y, $m, $d);
    $sql = <<<SQL
select r.*
from repo.release as r, repo.project as p
where 
  r.datereleased >= '{$foo}' and r.datereleased < (timestamptz '{$foo}' + interval '1 day') 
  and p.hidden='f' and r.hidden='f' and p.id = r.projectid and (p.name='bbsengine' or p.name='bbsengine3' or p.name='bbsengine4')
order by datereleased desc
SQL;
    $res = $this->dbh->getAll($sql);
    if (PEAR::isError($res))
    {
      logentry("archive.displayday.0: " . $res->toString());
      return PEAR::raiseError("Database Error (code: archive.displayday.0)");
    }

    $releases = array();
    foreach ($res as $rec)
    {
      $id = $rec["id"];
      $release = $rec;
      $files = $this->getfilesforreleaseid($id);
      if (PEAR::isError($files))
      {
        logentry("archive.display.10: " . $files->toString());
        return PEAR::raiseError("Database Error (code: archive.display.10)");
      }
      $release["files"] = $files;
      $releases[] = $release;
    }
    $data = [];
    $data["day"] = $foo;
    $data["releases"] = $releases;
    $data["pagetemplate"] = "archive-day.tmpl";
    displaypage(null, $data);
/*
    $page = getpage("bbsengine3 release archive - {$foo}");
    $page->addStyleSheet(SKINURL . "css/actions.css");
    $page->addBodyContent(fetchpageheader());
    $tmpl = getsmarty();
    $tmpl->assign("day", $foo);
    $tmpl->assign("releases", $releases);
    $page->addBodyContent($tmpl->fetch("archive-day.tmpl"));
    $page->addBodyContent(fetchpagefooter());
    $page->display();
*/
    return;
  }
  
  function display()
  {
    $sql = <<<SQL
select extract(year from datereleased) as year, 
       count(*) 
from repo.release as r, repo.project as p
where p.hidden='f' and r.hidden='f' and p.id = r.projectid and (p.name='bbsengine' or p.name='bbsengine3' or p.name='bbsengine4')
group by year 
order by year;
SQL;
    $res = $this->dbh->getAll($sql);
    if (PEAR::isError($res))
    {
      logentry("archive.display.0: " . $res->toString());
      return PEAR::raiseError("Database Error (code: archive.display.0)");
    }

    $data = [];
    $data["pagetemplate"] = "archive-display.tmpl";
    $data["years"] = $res;
    
    displaypage(null, $data);
/*
    $page = getpage("bbsengine4 release archive");
    $page->addBodyContent(fetchpageheader("Release Archive"));
    $tmpl = getsmarty();
    $tmpl->assign("years", $res);
    $page->addBodyContent($tmpl->fetch("archive-display.tmpl"));
    $page->addBodyContent(fetchpagefooter());
    $page->display();
*/
    return;
  }

  function main()
  {
    session_start();
    
    $this->dbh = dbconnect(SYSTEMDSN);
    if (PEAR::isError($this->dbh))
    {
      logentry("archive.10: " . $this->dbh->toString());
      return PEAR::raiseError("Database Error (code: archive.10)");
    }
    
    setcurrentpage("archive");
    
    $year = (isset($_REQUEST["year"]) && $_REQUEST["year"] > 0) ? intval($_REQUEST["year"]) : 0;
    $month = (isset($_REQUEST["month"]) && $_REQUEST["month"] > 0) ? intval($_REQUEST["month"]) : 0;
    $day = (isset($_REQUEST["day"]) && $_REQUEST["day"] > 0) ? intval($_REQUEST["day"]) : 0;
    
    if ($year == 0 && $month == 0 && $day == 0)
    {
      $this->display();
    }
    else if ($year > 0 && $month == 0 && $day == 0)
    {
      $this->displayyear($year);
    }
    else if ($year > 0 && $month > 0 && $day == 0)
    {
      $this->displaymonth($year, $month);
    }
    else if ($year > 0 && $month > 0 && $day > 0)
    {
      $this->displayday($year, $month, $day);
    }
    else
    {
      displayerrormessage("input error (code: archive.main.0)");
    }
    
    return;
  }
};

$a = new archive();
$a->main();

?>
