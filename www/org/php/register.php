<?php

require_once("config.php");
require_once("bbsenginedotorg.php");
require_once("bbsengine3.php");

class register
{
    var $dbh = null;
    
    function process($values)
    {
        $member = array();
        $member["emailaddress"] = $values["emailaddress"];
        $member["password"] = md5($values["password"]);
        $member["fullname"] = $values["fullname"];
        $member["dateregistered"] = "now()";
        $res = $this->dbh->beginTransaction();
        $r = $this->dbh->autoExecute("member", $member, MDB2_AUTOQUERY_INSERT);
        if (PEAR::isError($r))
        {
            logentry("register.20: " . $r->toString());
            $this->dbh->rollback();
            return PEAR::raiseError("Database Error (code: register.20)");
        }
        $res = $this->dbh->commit();
        
        $page = getpage(SITETITLE . " - Thank you for registering");
        $page->addBodyContent(fetchheader());
//        $page->addBodyContent(fetchsidebar());
        $tmpl = getsmarty();
        $page->addBodyContent($tmpl->fetch("thankyouforregistering.tmpl"));
        $page->addBodyContent(fetchfooter());
        $page->display();

//        var_export($values);
        return;
    }
    
    function main()
    {
        session_start();
        
        $this->dbh = dbconnect(SYSTEMDSN);
        if (PEAR::isError($this->dbh))
        {
            logentry("register.10: " . $this->dbh->toString());
            return PEAR::raiseError("Database Error (code: register.10)");
        }
        
        setcurrentpage("register");

        $form = getquickform(LOGENTRYPREFIX."-register");
        buildprofilefieldset($form);
        buildcaptchafieldset($form);

        $buttons = array();
        $buttons[] = &HTML_QuickForm::createElement("submit", null, "Register");
        $form->addGroup($buttons);
        
        $const = array();
        $const["userid"] = isset($_REQUEST["userid"]) ? intval($_REQUEST["userid"]) : getcurrentmemberid();
        $form->setConstants($const);
  
        $defaults = array();
        $form->setDefaults($defaults);

        if ($form->isSubmitted() && $form->validate())
        {
            $captcha_question = $form->getElement("captcha_question");
            $captcha_question->destroy();
                
            // Don't need to see CAPTCHA related elements
            $form->removeElement("captcha_question");
            $form->removeElement("captcha");
              
            $form->freeze();
            $form->applyFilter("__ALL__", "trim");
            $form->applyFilter("__ALL__", "strip_tags");
            $r = $form->process(array(&$this, "process"), True);
            if (PEAR::isError($r))
            {
                return PEAR::raiseError($r);
            }
            return;
        }

        $elem = $form->getElement("captcha");
        $elem->setValue("");

        $renderer = new HTML_QuickForm_Renderer_Array(True);
        $form->accept($renderer);
        
        $page = getpage(SITETITLE . " - Register");
        $page->addStyleSheet(SKINURL . "css/form.css");
        $page->addBodyContent(fetchheader());
//        $page->addBodyContent(fetchsidebar());
        $tmpl = getsmarty();
        $tmpl->assign("form", $renderer->toArray());
        $page->addBodyContent($tmpl->fetch("form.tmpl"));
        $page->display();
    
        $this->dbh->disconnect();
        return;
    }
};

$j = new register();
$r = $j->main();
if (PEAR::isError($r))
{
    logentry("register.100: " . $r->toString());
    displayerrormessage($r->getMessage());
    exit;
}


?>