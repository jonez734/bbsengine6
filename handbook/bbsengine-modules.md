> **STATUS (2026-07-22): PARTIALLY OBSOLETE.** This document
> predates the current bbsengine6 module API. The "required
> functions" section (init/access/buildargs/main) and the
> `bbsengine6.module` reference are still accurate; everything
> else has been superseded. See
> `handbook/module.md` and `handbook/specs/module.md` for the
> current, complete spec.

version: python bbsengine5

modules
===

modules are small python scripts that are loaded at run-time.

in order to work, a module must define functions 'init', 'access', 'buildargs', and 'main'

- buildargs(args=None, subparser=None, **kwargs) -> argparse.ArgumentParser | None
    * args: argparse.ArgumentParser instance (optional)
    * subparser: argparse subparser instance (optional, see CLI subcommands below)
    * **kwargs: backward compatibility for bbsengine6 module system
    * returns argparse.ArgumentParser when called normally, or None when called with subparser

- access(args, op="run", **kwargs) -> bool:
    * required
    * 'args' is an argparse instance
    * op is currently only 'run' and is reserved for future use
    * when access() returns True, access is granted. any other return value will give a 'permission denied' message.

- main(args, **kwargs) -> bool:
    * 'args' as always
    * **kw is the keyword arguments. this is used, for example, in games
      like empyre where the current object needs to be passed to a module

- after init() is called and access() passes, main() is called.

- bbsengine.runmodule(args, module, **kwargs)
    * kw arg of 'buildargs' set to True will attempt to call <module>.buildargs()
    * return value is same as return value of <module>.main()

bbsengine6
===

- every module must have:
    * init()
    * buildargs()
    * access()
    * main()

- buildargs() is allowed to return None.
- runsubmodule() is no longer part of bbsengine

CLI Subcommands (buildargs with subparser)
---

When a parent application (like empyre) uses argparse subparsers to implement git-style
subcommands, it calls each module's buildargs() with a subparser argument:

    subparsers = parser.add_subparsers(dest="command")
    sp = subparsers.add_parser("mymodule")
    module.buildargs(subparser=sp)

When buildargs() is called with subparser != None, it should:
- Add CLI arguments to the subparser using subparser.add_argument()
- Return None (the parent parser handles the return value)

When buildargs() is called without subparser (subparser=None), it should:
- Behave as before: create and return an argparse.ArgumentParser, or return None

Example signature supporting both modes:

    def buildargs(args=None, subparser=None, **kwargs):
        if subparser is not None:
            subparser.add_argument("--myflag", action="store_true")
            return None
        # Backward compatibility: create and return a parser
        parser = argparse.ArgumentParser("mymodule")
        return parser

This allows modules to register CLI arguments dynamically without the parent
application hardcoding argparse arguments for each module.
