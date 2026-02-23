version: python bbsengine5

modules
===

modules are small python scripts that are loaded at run-time.

in order to work, a module must define functions 'init', 'access', 'buildargs', and 'main'

- buildargs(args, **kw) -> argparse | None
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
