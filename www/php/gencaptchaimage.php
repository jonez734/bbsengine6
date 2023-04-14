<?php

require_once("Text/CAPTCHA.php");
require_once("Text/CAPTCHA/Driver/Image.php");

session_start();

header("Content-Type: image/jpeg");

$sessionVar = (empty($_REQUEST["var"])) ? "_HTML_QuickForm_CAPTCHA" : $_REQUEST["var"];

// Force a new CAPTCHA for each one displayed

$_SESSION[$sessionVar]->setPhrase();
echo $_SESSION[$sessionVar]->getCAPTCHAAsJPEG();

?>
