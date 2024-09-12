<?php

namespace bbsengine6\member\lib {

    function getcurrentid()
    {
        $res = isset($_SESSION["currentmemberid"]) ? intval($_SESSION["currentmemberid"]) : null;
        return $res;
    }

    function setcurrentid($id)
    {
        \bbsengine6\logentry("setcurrentid.10: id=".var_export($id, true));

        $_SESSION["currentmemberid"] = intval($id);
    }

    function getcurrentmoniker()
    {
        return isset($_SESSION["currentmembermoniker"]) ? $_SESSION["currentmembermoniker"] : null;
    }

    function setcurrentmoniker($moniker)
    {
        \bbsengine6\logentry("setcurrentmoniker.10: id=".var_export($moniker, true));
        $_SESSION["currentmembermoniker"] = $moniker;
    }

    
    function getflag($flag, $memberid, $dsn=\config\SYSTEMDSN)
    {
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
    /**
     * return the set of flags and their values for a given memberid.
     * rewritten 2011-jun-23 so it actually works without smarty3 throwing notices about undefined vars
     *
     * @since 20081002
     * @param integer $memberid
     * @return array or PEAR_Error
     */
    function getflags($memberid)
    {
      $sql = <<<SQL
    select 
      flag.name, 
      coalesce(map_member_flag.value, flag.defaultvalue) as value
    from engine.flag 
    left outer join engine.map_member_flag on flag.name = engine.map_member_flag.name and engine.map_member_flag.memberid=:memberid
SQL;
      $dat = ["memberid" => $memberid];
      $pdo = \bbsengine6\database\connect(\config\SYSTEMDSN);
      $stmt = $pdo->prepare($sql);
      \bbsengine6\logentry(var_export($stmt->execute($dat), true));
      $res = $stmt->fetchAll();

      $flags = [];
/*
      if ($memberid > 0)
      {
        $flags["AUTHENTICATED"] = true;
      }
      else
      {
        $flags["AUTHENTICATED"] = false;
      }
*/
      foreach ($res as $rec)
      {
        $k = $rec["name"];
        $v = $rec["value"];
        $v = \bbsengine6\toboolean($v, $k);
        $flags[$k] = $v;
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
    function checkflag($name, $memberid=0)
    {
      if ($memberid == 0)
      {
        $memberid = getcurrentid();
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

      $dbh = \bbsengine6\database\connect(\config\SYSTEMDSN);
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

    function buildfieldset($form)
    {
      $fieldset = $form->addFieldset("member");
      $fieldset->setLabel("account");
      
      $moniker = $fieldset->addText("moniker");
      $moniker->setLabel("moniker");
      $moniker->addRule("required", "'moniker' is a required field");
      $moniker->addRule("callback", "Moniker is currently in use", "bbsengine6\\member\\uniquemonikercallback");

      $email = $fieldset->addText("email");
      $email->setLabel("e-mail address (must be valid for account verification)");
      $email->addRule("required", "'E-Mail address' is a required field.");
      
/*
      $realname = $fieldset->addText("realname");
      $realname->setLabel("real name");
*/      
      if (\bbsengine6\member\access("editcredits"))
      {
        $credits = $fieldset->addText("credits", ["id" => "credits"]);
        $credits->setLabel("credits");
        $credits->addRule("regex", "'Credits' must be an integer", '/^[0-9]+$/');
      }
      return;
    }

    function access($op, $data=null, $memberid=null)
    {
      if ($memberid === null)
      {
        $memberid = getcurrentid();
      }

      $member = isset($data["member"]) ? $data["member"] : null;

      switch ($op)
      {
        case "editcredits":
        {
          if (checkflag("ADMIN"))
          {
            $res = true;
            break;
          }
          $res = False;
          break;
        }
        case "detail":
        {
          $res = true;
          break;
        }
        case "changepassword":
        {
          if (checkflag("AUTHENTICATED") === False)
          {
            $res = False;
            break;
          }
          if (flag("ADMIN", $memberid) === true || ($memberid !== null && $data["id"] == $memberid))
          {
            $res = true;
            break;
          }
          $res = False; 
          break;
        }
        case "add":
        {
         $res = true;
         break;
        }
        case "edit":
        {
          if (flag("ADMIN", $memberid) === true || $data["id"] == $memberid)
          {
            $res = true; 
            break;
          }
          $res = False; 
          break;
        }
        case "editflags":
        {
          if (flag("ADMIN", $memberid) === true)
          {
            $res = true; 
            break;
          }
          $res = False; 
          break;
        }
        case "sendverifyemail":
        {
          if (flag("ADMIN", $memberid) === true)
          {
            $res = true; 
            break;
          }
          $res = False; 
          break;
        }
        default:
        {
          $res = null;
          break;
        }
      }
    //  logentry("accessmember.50: op=".var_export($op, true)." member.id=".var_export($data["id"], True)." memberid=".var_export($memberid, True)." res=".var_export($res, True));
      return $res;  
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
     * @param integer memberid memberid to check against
     * 
     * @see hashpassword()
     */
    function checkpassword($password, $memberid)
    {
      $sql = "select 1 as valid from engine.member where id=:memberid and password=crypt(:password, password)"; //  engine.__member set password=crypt(%s, gen_salt('bf')) where id=%s"
      // $sql = "select crypt(:password, password) as valid from engine.member where id=:memberid";
      $dat = ["memberid" => $memberid, "password" => $password];

//      \bbsengine6\logentry("checkpassword.100: password=".var_export($password, true)." memberid=".var_export($memberid, true));
      $pdo = \bbsengine6\database\connect(\config\SYSTEMDSN);
      if (\PEAR::isError($pdo))
      {
        \bbsengine6\logentry("checkpassword.100: " . $pdo->toString());
        return false;
      }
      $stmt = $pdo->prepare($sql);
      $stmt->execute($dat);
      if ($stmt->rowCount() == 1)
      {
        return true;
      }
      return false;
    }
    
    function getbymoniker($moniker)
    {
      $sql = "select * from engine.member where moniker=:moniker";
      $dat = ["moniker" => $moniker];
      $dbh = \bbsengine6\database\connect(\config\SYSTEMDSN);
      $stmt = $dbh->prepare($sql);
      $stmt->execute($dat);
      if ($stmt->rowCount() == 0)
      {
        return null;
      }
      return $stmt->fetch();
    }
    
    function setflag($name, $value, $memberid=0)
    {
      if ($memberid == 0)
      {
        $memberid = getcurrentid();
      }
      $dbh = \bbsengine6\database\connect(\config\SYSTEMDSN);
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
    
    function setpassword($memberid, $plaintext)
    {
      $sql = "update engine.__member set password=crypt(:password, gen_salt('bf')) where id=:memberid";
      $dat = ["password" => $plaintext, "memberid" => $memberid];
      $pdo = \bbsengine6\database\connect(\config\SYSTEMDSN);
      $stmt = $pdo->prepare($sql);
      $stmt->execute($dat);
      if ($stmt->rowCount() == 1)
      {
        return true;
      }
      return false;
    }
}
?>
