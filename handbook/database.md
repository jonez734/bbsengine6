database
==

- create()
- exists()
- update()
- delete()
- getpool()
- classexists()
- schemaexists()
- createrol()
- rolexists()
- createschema()
- get_role_privs()        # SECURITY DEFINER; owned by `zoid6`
- manage_role_privs()     # SECURITY DEFINER; owned by `zoid6`
- manage_secondary_role() # SECURITY DEFINER; owned by `zoid6`
- manage_database_priv()  # SECURITY DEFINER; owned by `zoid6`
- manage_schema_priv()    # SECURITY DEFINER; owned by `zoid6`
- verify_function_owner() # allow-list gate for the 5 helpers
- cursor()
- extensionavailable()
- extensioninstalled()
- createextension()
- importsql()
- functionexists()
- query()

The five `manage_*_priv` / `get_role_privs` helpers are owned by
the dedicated `zoid6` role (`NOSUPERUSER NOCREATEDB NOCREATEROLE
NOLOGIN INHERIT`), not by the bootstrap principal. See
`handbook/specs/database.md` "SECURITY DEFINER helpers and
ownership" for the rationale and the
`database.verify_function_owner` allow-list.

Backend modules responsible for the role/ownership split:
`backend.checkzoid6role` (creates the role) and
`backend.checkzoid6owner` (reassigns the helpers).
