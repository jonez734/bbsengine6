<?php

require_once("config.php");
require_once("vfw10058.php");
require_once("bbsengine3.php");

class post
{
  var $dbh = null;
  var $form = null;
  
  function buildpostfieldset()
  {
    $this->form = getquickform("vfw10058-post");
    $this->form->addElement("header", "", "Post");

    $this->form->addElement("text", "title", "Title");

    $this->form->addRule("title", "'Title' is a required field.", "required");

    $this->form->addElement("checkbox", "membersonly", "Post will only be visible to <i>members</i>.");
    
    $this->form->addElement("textarea", "body", "Message", array("cols" => 45, "rows" => 15));
    buildcaptchafieldset($this->form);
    return;
  }
  
  function update($values)
  {
    if (!flag("ADMIN"))
    {
      logentry("post.46: permission denied trying to update post");
      displaypermissiondenied();
      return;
    }

    $postid = $values["id"];
    $currentmemberid = getcurrentmemberid();
    $post = array();
    $post["title"] = $values["title"];
    $post["body"] = $values["body"];
    $post["modifiedbyid"] = $currentmemberid;
    $post["datemodified"] = "now()";
    $post["membersonly"] = isset($values["membersonly"]) ? True : False;
    
    $res = $this->dbh->autoExecute("__post", $post, MDB2_AUTOQUERY_UPDATE, "id=".$this->dbh->quote($postid, "integer"));
    if (PEAR::isError($res))
    {
      logentry("post.44: " . $res->toString());
      return PEAR::raiseError("Database Error (code: post.44)");
    }
    displayredirectpage("OK. Post Updated");
    return;
  }
  
  function edit()
  {
    $id = isset($_REQUEST["id"]) ? intval($_REQUEST["id"]) : null;
    
    $post = getpost($id);
    if (PEAR::isError($post))
    {
      logentry("post.40: " . $post->toString());
      return PEAR::raiseError("Database Error (code: post.40)");
    }
    
    if ($post === null)
    {
      logentry("post.42: getpost() returned null for id=".var_export($id, true));
      return PEAR::raiseError("Input Error (code: post.42)");
    }
    
    if (!access_post("edit", $post))
    {
      logentry("post.44: edit permission denied for post #{$id}");
      displaypermissiondenied();
      return;
    }

    $this->buildpostfieldset();
    $buttons = array();
    $buttons[] = &HTML_QuickForm::createElement("submit", null, "Edit Post");
    $this->form->addGroup($buttons);

    $const = array();
    $const["mode"] = "edit";
    $const["id"] = $id;
    $this->form->setConstants($const);

    $def = $post;
    $this->form->setDefaults($def);

    if ($this->form->isSubmitted() && $this->form->validate())
    {
      $this->form->freeze();
      $this->form->applyFilter("__ALL__", "trim");
      $this->form->applyFilter("__ALL__", "strip_tags");
      $res = $this->form->process(array($this, "update"), True);
      if (PEAR::isError($res))
      {
        logentry("post.40: " . $res->toString());
        return PEAR::raiseError("Post Failed (code: post.40)");
      }
      return;
    }

    if ($this->form->elementExists("captcha"))
    {
      $elem = $this->form->getElement("captcha");
      $elem->setValue("");
    }

    $renderer = new HTML_QuickForm_Renderer_Array(True);
    $this->form->accept($renderer);

    $page = getpage("Post");
    $page->addStyleSheet(SKINURL . "css/vfw10058.css");

    $page->addStyleSheet(SKINURL . "css/form.css");
    $page->addBodyContent(fetchheader());
    $tmpl = getsmarty();
    $tmpl->assign("form", $renderer->toArray());
    $page->addBodyContent($tmpl->fetch("form.tmpl"));
    $page->addBodyContent(fetchfooter());
    $page->display();
    return;
    
  }
  
  function insert($values)
  {
    setcurrentpage("blog");
    
    $currentmemberid = getcurrentmemberid();
    
    $this->dbh->beginTransaction();

    $post = array();
    $post["title"] = $values["title"];
    $post["dateposted"] = "now()";
    $post["postedbyid"] = $currentmemberid;
    $post["modifiedbyid"] = $currentmemberid;
    $post["datemodified"] = "now()";
    $post["name"] = buildname($post["title"]);
    $post["body"] = $values["body"];
    $post["approved"] = "f";
    $post["membersonly"] = isset($values["membersonly"]) ? True : False;

//    var_export($post);
//    return;
    $res = $this->dbh->autoExecute("__post", $post, MDB2_AUTOQUERY_INSERT);
    if (PEAR::isError($res))
    {
      logentry("post.30: " . $res->toString());
      $this->dbh->rollback();
      return PEAR::raiseError("Database Error (code: post.30)");
    }

    $postid = $this->dbh->lastInsertId("__post");
//    print "postid=".var_export($postid, true);

    $categories = array("top");
    foreach ($categories as $category)
    {
      $map = array();
      $map["postid"] = $postid;
      $map["categorypath"] = $category;
      $res = $this->dbh->autoExecute("map_post_category", $map, MDB2_AUTOQUERY_INSERT);
      if (PEAR::isError($res))
      {
        logentry("post.40: " . $res->toString());
        $this->dbh->rollback();
        return PEAR::raiseError("Database Error (code: post.40)");
      }
    }
    $this->dbh->commit();
    displayredirectpage("OK. Post Added.");
    
    return;
  }

  function add()
  {
    if (!access_post("add"))
    {
      logentry("post.46: permission denied trying to add post");
      displaypermissiondenied();
      return;
    }

    $this->buildpostfieldset();
    $buttons = array();
    $buttons[] = &HTML_QuickForm::createElement("submit", null, "Add Post");
    $this->form->addGroup($buttons);

    $const = array();
    $const["mode"] = "add";
    $this->form->setConstants($const);

    $def = array();
    $this->form->setDefaults($def);

    if ($this->form->isSubmitted() && $this->form->validate())
    {
      $this->form->freeze();
      $this->form->applyFilter("__ALL__", "trim");
      $this->form->applyFilter("__ALL__", "strip_tags");
      $res = $this->form->process(array($this, "insert"), True);
      if (PEAR::isError($res))
      {
        logentry("post.40: " . $res->toString());
        return PEAR::raiseError("Post Failed (code: post.40)");
      }
      return;
    }

    if ($this->form->elementExists("captcha"))
    {
      $elem = $this->form->getElement("captcha");
      $elem->setValue("");
    }

    $renderer = new HTML_QuickForm_Renderer_Array(True);
    $this->form->accept($renderer);

    $page = getpage("Post");
    $page->addStyleSheet(SKINURL . "css/vfw10058.css");

    $page->addStyleSheet(SKINURL . "css/form.css");
    $page->addBodyContent(fetchheader());
    $tmpl = getsmarty();
    $tmpl->assign("form", $renderer->toArray());
    $page->addBodyContent($tmpl->fetch("form.tmpl"));
    $page->addBodyContent(fetchfooter());
    $page->display();
    return;
  }

  function delete()
  {
    
    $id = isset($_REQUEST["id"]) ? intval($_REQUEST["id"]) : null;
    $sql = "select 1 from post where id=?";
    $dat = array($id);
    $res = $this->dbh->getOne($sql, null, $dat, array("integer"));
    if (PEAR::isError($res))
    {
      logentry("post.41: " . $res->toString());
      return PEAR::raiseError("Database Error (code: post.41)");
    }
    if ($res === null)
    {
      return PEAR::raiseError("Input Error (code: post.42)");
    }
    
    if (!access_post("delete", $post))
    {
      logentry("post.14: delete permission denied for post id #{$id}");
      return PEAR::raiseError("Permission Denied (code: post.14)");
    }

    $confirm = isset($_REQUEST["confirm"]) ? True : False;
    if ($confirm === False)
    {
      $post = getpost($id);
      $posttitle = $post["title"];
      displaydeleteconfirmation("Delete post with title &quot;{$posttitle}&quot;?", "/post-delete-{$id}?confirm", "Delete this post", "/", "Do not delete this post");
      return;
    }

    $res = $this->dbh->autoExecute("__post", null, MDB2_AUTOQUERY_DELETE, "id=".$this->dbh->quote($id));
    if (PEAR::isError($res))
    {
      logentry("post.44: " . $res->toString());
      return PEAR::raiseError("Database Error (code: post.44)");
    }
    displayredirectpage("Post Deleted");
    return;
  }

  function view()
  {
    $id = isset($_REQUEST["id"]) ? intval($_REQUEST["id"]) : null;
    $post = getpost($id);
    if (PEAR::isError($post))
    {
      logentry("post.52: ".$post->toString());
      return PEAR::raiseError("Database Error (code: post.52)");
    }

    if ($post === null)
    {
      logentry("post.54: getpost() returned null");
      return PEAR::raiseError("Input Error (code: post.54)");
    }
    
    if (access_post("view", $post) === False)
    {
      logentry("post.56: view permission denied for post #{$id}");
      return PEAR::raiseError("Permission Denied (code: post.56)");
    }

    setcurrentpage("sophia");
    setcurrentaction("view");
    
    $posttitle = $post["title"];
    
    $title = "Post - {$posttitle}";
    $page = getpage($title);
    $page->addStyleSheet(SKINURL . "css/vfw10058.css");

    $page->addStyleSheet(SKINURL . "css/post.css");
    $page->addBodyContent(fetchheader());
    $tmpl = getsmarty();
    $tmpl->assign("post", $post);
    $page->addBodyContent($tmpl->fetch("post.tmpl"));
    $page->addBodyContent(fetchfooter());
    $page->display();
    return;
  }

  /** 
   * access checking function influenced by gunn and drupal
   *
   * @since 20110803
   *
   */
  function access($op, $post=null, $uid=null)
  {
    return access_post($op, $post, $uid);
  }
  
  function main()
  {
    session_start();
    
    $mode = isset($_REQUEST["mode"]) ? $_REQUEST["mode"] : null;
    
    $this->dbh = dbconnect(SYSTEMDSN);
    if (PEAR::isError($this->dbh))
    {
      logentry("post.10: " . $this->dbh->toString());
      return PEAR::raiseError("Database Error (code: post.10)");
    }

    switch ($mode)
    {
      case "add":
        $res = $this->add();
        break;
      case "view":
        $res = $this->view();
        break;
      case "edit":
        $res = $this->edit();
        break;
      case "delete":
        $res = $this->delete();
        break;
      default:
        return PEAR::raiseError("Input Error (code: post.20)");
    }

    if (PEAR::isError($res))
    {
      return PEAR::raiseError($res);
    }

    $this->dbh->disconnect();
    return;
  }
};

$a = new post();
$b = $a->main();
if (PEAR::isError($b))
{
  logentry("post.100: " . $b->toString());
  displayerrormessage($b->getMessage());
  exit;
}
