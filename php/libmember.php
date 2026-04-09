<?php

namespace {
  require_once("util.php");
  require_once("database.php");
}

namespace bbsengine6\member\lib
{
    \bbsengine6\util\logentry("namespace=".var_export(__NAMESPACE__, true));

    /**
     * Helper function to get the database DSN with fallback
     * @return string DSN connection string
     */
    function getDSN()
    {
      // Try config namespace first, then fallback to bare constant
      if (defined('\config\SYSTEMDSN')) {
        return \config\SYSTEMDSN;
      } elseif (defined('\SYSTEMDSN')) {
        return \SYSTEMDSN;
      }
      // Final fallback - return empty string which will cause database error with proper error handling
      return '';
    }

    function getcurrentid()
    {
        $res = isset($_SESSION["currentmemberid"]) ? intval($_SESSION["currentmemberid"]) : null;
        return $res;
    }

    function setcurrentid($id)
    {
        \bbsengine6\util\logentry("setcurrentid.10: id=".var_export($id, true));

        $_SESSION["currentmemberid"] = intval($id);
    }

    function getcurrentmoniker()
    {
        return isset($_SESSION["currentmoniker"]) ? $_SESSION["currentmoniker"] : null;
    }

    function setcurrentmoniker($moniker)
    {
        \bbsengine6\util\logentry("setcurrentmoniker.10: moniker=".var_export($moniker, true));
        $_SESSION["currentmoniker"] = $moniker;
    }

    
/*
    function checkflag($flag, $moniker=null)
    {
      $sql = "select engine.checkflag(:flag, :moniker)";
      $dat = ["flag" => $flag, "moniker" => $moniker];

      $pdo = \bbsengine6\database\connect(getDSN());
      if (\PEAR::isError($pdo))
      {
        \bbsengine6\util\logentry("libmember.approved.100: " . $pdo->toString());
        return false;
      }
      $stmt = $pdo->prepare($sql);
      $stmt->execute($dat);
      if ($stmt->rowCount() == 0)
      {
        return null;
      }
      return $stmt->fetch()["checkflag"];
    }
*/
/*
    function getflag($flag, $memberid, $dsn=null)
    {
        $sql = <<<SQL
    select 
      f.name, 
      coalesce(mmf.value, f.defaultvalue) as value 
    from engine.member_flag as f
    left outer join engine.map_member_flag as mmf on (f.name=mmf.name and mmf.memberid=?) 
    where f.name=?;
SQL;

      $dat = [$memberid, $flag];
      $pdo = \bbsengine6\database\connect($dsn);
      $stmt = $pdo->prepare($sql);
      $stmt->execute($dat);
      if ($stmt->rowCount() === 0)
      {
        return null;
      }
      $res = $stmt->fetch();
      if ($res["value"] === 't')
      {
        return true;
      }
      return false;
    }
*/
    /**
     * return the set of flags and their values for a given membermoniker
     * rewritten 2011-jun-23 so it actually works without smarty3 throwing notices about undefined vars
     *
     * @since 20081002
     * @param text $moniker
     * @return array
     */
    function getflags($moniker)
    {
      $sql = "select engine.getflags(:moniker)";
      $dat = ["moniker" => $moniker];
      $pdo = \bbsengine6\database\connect(getDSN());
      $stmt = $pdo->prepare($sql);
      $stmt->execute($dat);
      return $stmt->fetchAll();
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
     * @param string $moniker
     * @return boolean
     * @since 20080324
     * @since 20221116
     */ 
    function checkflag($name, $moniker=null)
    {
      if ($moniker === null)
      {
        $moniker = getcurrentmoniker();
      }
            
      $sql = "select engine.checkflag(:name, :moniker)";
      $dat = ["name" => $name, "moniker" => $moniker];
      $pdo = \bbsengine6\database\connect(getDSN());
      $stmt = $pdo->prepare($sql);
      $stmt->execute($dat);
      if ($stmt->rowCount() == 0)
      {
        \bbsengine6\util\logentry("query for flag {$name} for moniker {$moniker} failed.");
        return null;
      }
      $value = $stmt->fetchColumn()["checkflag"];
      if ($value === null) // invalid flag
      {
        \bbsengine6\util\logentry("invalid flag {$name} for moniker {$moniker} requested");
        return null;
      }
      return $value;
    }

    /**
     * @since 20121017
     *
     * a quickform2 callback to see if the given $value exists in the name field of the member table
     */
    function uniquemonikercallback($value)
    {
//      logentry("uniqueusernamecallback.0");

      $value = trim($value);
      $value = strip_tags($value);
      $sql = "select 1 from engine.member where moniker ilike ?";
      $dat = array($value);

      $dbh = \bbsengine6\database\connect(getDSN());
      if (\PEAR::isError($dbh))
      {
        logentry("uniqueusernamecallback.1: " . $res->toString());
        return \PEAR::raiseError($dbh);
      }

      $stmt = $dbh->prepare($sql);
      $stmt->execute($dat);
      if ($stmt->rowCount() == 0)
      {
        return true;
      }
      return false;
    }

    // @since 20240925
    function refcodevalid($value)
    {
      $value = trim($value);
      $value = strip_tags($value);

      if ($value === null || $value == "")
      {
        util\logentry("refcodevalid.100: no need to check ".var_export($value, true));
        return true;
      }

      $sql = "select * from engine.refcode where code=:refcode";
      $dat = ["refcode" => $value];
      $dbh = \bbsengine6\database\connect(getDSN());
      $stmt = $dbh->prepare($sql);
      $stmt->execute($dat);
      if ($stmt->rowCount() == 0)
      {
        util\logentry("refcodevalid.120: refcode ".var_export($value, true)." not found");
        return false;
      }
      $res = $stmt->fetch();
      if ($res["status"] == "active")
      {
        util\logentry("refcodevalid.140: refcode ".var_export($value, true)." active. returning true");
        return true;
      }
      return false;
    }

    function buildfieldset($form)
    {
      $fieldset = $form->addFieldset("member");
      $fieldset->setLabel("account");

      $moniker = $fieldset->addText("moniker");
      $moniker->setLabel("moniker");
      $moniker->addRule("required", "'moniker' is a required field");
      $moniker->addRule("callback", "Moniker is currently in use", "bbsengine6\\member\\lib\\uniquemonikercallback");

      $email = $fieldset->addText("email");
      $email->setLabel("e-mail address (must be valid for account verification)");
      $email->addRule("required", "'E-Mail address' is a required field.");

      $refcode = $fieldset->addText("refcode");
      $refcode->setLabel("refcode (optional)");
      $refcode->addRule("callback", "refcode invalid", "bbsengine6\\member\\lib\\refcodevalid");
      
/*
      $realname = $fieldset->addText("realname");
      $realname->setLabel("real name");
*/      
      if (checkflag("sysop") === true)
      {
        $credits = $fieldset->addText("credits", ["id" => "credits"]);
        $credits->setLabel("credits");
        $credits->addRule("regex", "'Credits' must be an integer", '/^[0-9]+$/');
      }
      return;
    }
    
    function update($pdo, $memberid, $member)
    {
      $member["dateupdated"] = "now()";
      $member["updatedbyid"] = getcurrentmoniker();
      \bbsengine6\database\update($pdo, "engine.__member", $memberid, $member);
    }

    /**
     * @since 20240825 copied from bbsengine4
     * @param text $password plain text password i.e. from a quickform
     * @param text $moniker moniker to check against
     * 
     */
    function checkpassword($password, $moniker)
    {
      $sql = "select 1 as valid from engine.member where moniker=:moniker and password=crypt(:password, password)";
      $dat = ["moniker" => $moniker, "password" => $password];

//      \bbsengine6\logentry("checkpassword.100: password=".var_export($password, true)." memberid=".var_export($memberid, true));
      $pdo = \bbsengine6\database\connect(getDSN());
      if (\PEAR::isError($pdo))
      {
        \bbsengine6\util\logentry("checkpassword.100: " . $pdo->toString());
        return false;
      }
      $stmt = $pdo->prepare($sql);
      $stmt->execute($dat);
      return $stmt->rowCount() === 1;
    }

    function setpassword($moniker, $plaintext)
    {
      $sql = "update engine.__member set password=crypt(:password, gen_salt('bf')) where moniker=:moniker";
      $dat = ["password" => $plaintext, "moniker" => $moniker];
      $pdo = \bbsengine6\database\connect(getDSN());
      $stmt = $pdo->prepare($sql);
      $stmt->execute($dat);
      if ($stmt->rowCount() == 1)
      {
        return true;
      }
      return false;
    }

    function approved($moniker)
    {
      return checkflag("approved", $moniker);
    }

    function updatelastlogin($moniker)
    {
      $lastloginfrom = \bbsengine6\util\getremoteaddr();

      \bbsengine6\util\actionlog(name: "login", moniker: $moniker);
/*
      $sql = "update engine.__member set lastlogin=:lastlogin, lastloginfrom=:lastloginfrom where moniker=:moniker";
      $dat = ["lastlogin" => "now()", "lastloginfrom" => $lastloginfrom, "moniker" => $moniker];
      $dbh = \bbsengine6\database\connect(getDSN());
      $stmt = $dbh->prepare($sql);
      $stmt->execute($dat);

      \bbsengine6\util\logentry("lastlogin for {$moniker} from {$lastloginfrom} updated");
*/
      return true;
    }

    function getbymoniker($moniker)
    {
      $sql = "select * from engine.member where moniker=:moniker";
      $dat = ["moniker" => $moniker];
      $dbh = \bbsengine6\database\connect(getDSN());
      $stmt = $dbh->prepare($sql);
      $stmt->execute($dat);
      if ($stmt->rowCount() == 0)
      {
        return ["moniker" => null];
      }
      $res = $stmt->fetch();
      $res["password"] = null;
      return $res;
    }
    
    function setflag($name, $value, $memberid=0)
    {
      if ($memberid == 0)
      {
        $memberid = getcurrentid();
      }
      $dbh = \bbsengine6\database\connect(getDSN());
      $dbh->beginTransaction();
      $sql = "delete from engine.map_member_flag where memberid=:memberid and name=:name";
      $dat = ["name" => $name, "memberid" => $memberid];
      $stmt = $dbh->prepare($sql);
      $stmt->execute($dat);

      $sql = "insert into engine.map_member_flag(name, value, memberid) values (:name, :value, :memberid)";
      $dat = ["name" => $name, "value" => $value, "memberid" => $memberid];
      $stmt = $dbh->prepare($sql);
      $stmt->execute($dat);
      $dbh->commit();
    }
    
}
?>
