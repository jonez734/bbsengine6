from bbsengine6.console import lib as _console_lib

buildargs = _console_lib.buildargs
setbottombar = _console_lib.setbottombar


def runmodule(args, submodule, **kwargs):
    return _console_lib.runmodule(
        args, submodule, package="bbsengine6.startup", **kwargs
    )
