<?php

namespace {
  require_once("util.php");
  require_once("database.php");
  require_once("libpassword.php");
}

namespace bbsengine6\member\lib
{
    \bbsengine6\util\logentry("namespace=".var_export(__NAMESPACE__, true));

    /**
     * Helper function to get the database DSN - delegates to database namespace
     * @return string DSN connection string
     * @deprecated Use \bbsengine6\database\getDSN() instead
     */
    function getDSN(): string
    {
      return \bbsengine6\database\getDSN();
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
      $value = $stmt->fetchColumn();
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

      $dbh = \bbsengine6\database\connect(\bbsengine6\database\getDSN());

      $stmt = \bbsengine6\database\query($dbh, 'SELECT 1 FROM $engine.member WHERE moniker ilike $1', [$value]);
      if ($stmt === false || $stmt->rowCount() == 0)
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
        \bbsengine6\util\logentry("refcodevalid.100: no need to check ".var_export($value, true));
        return true;
      }

      $dbh = \bbsengine6\database\connect(getDSN());
      $stmt = \bbsengine6\database\query($dbh, 'SELECT * FROM $engine.refcode WHERE code = :refcode', [":refcode" => $value]);
      if ($stmt === false || $stmt->rowCount() == 0)
      {
        \bbsengine6\util\logentry("refcodevalid.120: refcode ".var_export($value, true)." not found");
        return false;
      }
      $res = $stmt->fetch();
      if ($res["status"] == "active")
      {
        \bbsengine6\util\logentry("refcodevalid.140: refcode ".var_export($value, true)." active. returning true");
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
     * Check plaintext password against stored hash.
     *
     * No PostgreSQL round-trip: the stored hash is fetched with one
     * SELECT and verified locally via
     * \bbsengine6\password\verify_password(). On a successful verify
     * against a legacy/unhealthy hash, the column is transparently
     * rewritten with a fresh bcrypt hash (matches Python's
     * audit_password_hash + opportunistic-rehash pattern).
     *
     * @since 20240825 copied from bbsengine4
     * @since 20260823 rewrote to use local PHP password_verify (no
     *                crypt() round-trip), with legacy-hash rehash.
     * @param string $password Plaintext password from the form.
     * @param string $moniker  Moniker to check against.
     * @return bool True iff $password matches the stored hash.
     */
    function checkpassword($password, $moniker)
    {
      if ($moniker === null || $moniker === "") {
        return false;
      }
      $pdo = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
      $stmt = \bbsengine6\database\query(
        $pdo,
        "SELECT password FROM \$engine.__member WHERE moniker = :moniker",
        [":moniker" => $moniker]
      );
      if ($stmt === false || $stmt->rowCount() !== 1) {
        return false;
      }
      $row = $stmt->fetch();
      $stored = $row["password"] ?? null;

      if ($stored === null || $stored === "") {
        return $password === "";
      }

      $ok = \bbsengine6\password\verify_password($password, $stored);
      if (!$ok) {
        \bbsengine6\util\logentry(
          "libmember.checkpassword.100: verify failed for {$moniker} " .
          "(stored=" . \bbsengine6\password\classify_hash($stored) . ")"
        );
        return false;
      }

      if (\bbsengine6\password\needs_rehash($stored)) {
        \bbsengine6\util\logentry(
          "libmember.checkpassword.110: opportunistic rehash for {$moniker} " .
          "(was=" . \bbsengine6\password\classify_hash($stored) . ")"
        );
        \bbsengine6\member\lib\rehashpassword($moniker, $password, $pdo);
      }
      return true;
    }

    /**
     * Rewrite engine.__member.password for $moniker with a fresh
     * bcrypt hash of $plaintext. Single UPDATE, no
     * crypt()/gen_salt() round-trip.
     *
     * @since 20260823
     */
    function rehashpassword($moniker, $plaintext, $pdo = null)
    {
      if ($pdo === null) {
        $pdo = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
      }
      try {
        $hash = \bbsengine6\password\hash_password($plaintext);
      } catch (\Throwable $e) {
        \bbsengine6\util\logentry(
          "libmember.rehashpassword.100: hash failed for {$moniker}: " .
          $e->getMessage()
        );
        return false;
      }
      $stmt = \bbsengine6\database\query(
        $pdo,
        "UPDATE \$engine.__member SET password = :hash WHERE moniker = :moniker",
        [":hash" => $hash, ":moniker" => $moniker]
      );
      return $stmt !== false && $stmt->rowCount() === 1;
    }

    /**
     * Set engine.__member.password for $moniker to a fresh bcrypt hash
     * of $plaintext.
     *
     * No PostgreSQL round-trip: the hash is produced locally by
     * \bbsengine6\password\hash_password() (single source of truth for
     * new password hashes, cost factor and prefix in lock-step with
     * PG gen_salt('bf')). One UPDATE statement.
     *
     * @since 20240825 copied from bbsengine4
     * @since 20260823 rewrote to use local PHP password_hash (no
     *                gen_salt('bf') round-trip).
     * @param string $moniker   Moniker whose password is being set.
     * @param string $plaintext New plaintext password.
     * @return bool True iff one row was updated.
     */
    function setpassword($moniker, $plaintext)
    {
      $pdo = \bbsengine6\database\connect(\bbsengine6\database\getDSN());
      try {
        $hash = \bbsengine6\password\hash_password($plaintext);
      } catch (\Throwable $e) {
        \bbsengine6\util\logentry(
          "libmember.setpassword.100: hash failed for {$moniker}: " .
          $e->getMessage()
        );
        return false;
      }
      $stmt = \bbsengine6\database\query(
        $pdo,
        "UPDATE \$engine.__member SET password = :hash WHERE moniker = :moniker",
        [":hash" => $hash, ":moniker" => $moniker]
      );
      return $stmt !== false && $stmt->rowCount() === 1;
    }

    function approved($moniker)
    {
      return checkflag("approved", $moniker);
    }

    function updatelastlogin($moniker)
    {
      $lastloginfrom = \bbsengine6\util\getremoteaddr();

      \bbsengine6\util\actionlog("login", null, $moniker);
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
      $dbh = \bbsengine6\database\connect(getDSN());
      $stmt = \bbsengine6\database\query($dbh, 'SELECT * FROM $engine.member WHERE moniker = :moniker', [":moniker" => $moniker]);
      if ($stmt === false || $stmt->rowCount() == 0)
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
      \bbsengine6\database\query($dbh, 'DELETE FROM $engine.map_member_flag WHERE memberid = :memberid AND name = :name', [":name" => $name, ":memberid" => $memberid]);

      \bbsengine6\database\query($dbh, 'INSERT INTO $engine.map_member_flag(name, value, memberid) VALUES (:name, :value, :memberid)', [":name" => $name, ":value" => $value, ":memberid" => $memberid]);
    }
    
}
?>
