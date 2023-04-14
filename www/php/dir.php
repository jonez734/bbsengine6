<?php
/**
 * handle 'directory index' for /v4, /v5, etc.
 */
require_once("config.php");
require_once("bbsenginedotorg.php");
require_once("bbsengine4.php");

/**
 * class 'dir'
 *
 * @since 20190806
 */
class dir
{
    function main()
    {
        startsession();
        
        $version = isset($_REQUEST["version"]) ? $_REQUEST["version"] : null;
        if ($version === null)
        {
            logentry("dir.100: dir is null");
            return PEAR::raiseError("no version specified (code: dir.100)");
        }
        $path = "/".joinpath(DOCUMENTROOT, $version);
        if (is_dir($path) === false)
        {
            logentry("dir.120: path is not a dir. path=".var_export($path, true));
            return PEAR::raiseError("path is not a dir (code: dir.120)");
        }
        if (is_readable($path) === false)
        {
            logentry("dir.130: path is not readable");
            return PEAR::raiseError("path is not readable (code: dir.130)");
        }
        $dirs = scandir($path);
        $items = [];
        foreach ($dirs as $dir)
        {
            if (in_array($dir, [".",".."]) === true)
            {
                logentry("dir.150: found '.' or '..'.. skipped");
                continue;
            }
            $filename = "/".joinpath($path, $dir);
            logentry("dir.152: filename=".var_export($filename, true));
            if (is_readable($filename) === false)
            {
                logentry("dir.140: ".var_export($filename, true)." is not readable. skipped.");
                continue;
            }
            if (is_dir($filename) === true)
            {
                $item = $dir."/";
            }
            if (is_file($filename) === true)
            {
                $item = $dir;
            }
            logentry("dir.142: item=".var_export($item, true));
            $items[] = $item;
        }

        logentry("dir.150: items=".var_export($items, true));

        $data = [];
        $data["items"] = $items;
        $data["pagetemplate"] = "dir.tmpl";
        $data["version"] = $version;
        
        $page = getpage("bbsengine4 - simple and elegant application framework in php and python");
        $res = displaypage($page, $data);

        return;
        
    }
};

$a = new dir();
$b = $a->main();
if (PEAR::isError($b))
{
    logentry("dir.110: " . $b->toString());
    displayerrorpage($b->getMessage());
    exit;
}
