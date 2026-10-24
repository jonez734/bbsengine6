-- Migration: data roles are NOLOGIN.
--
-- A LOGIN data role lets an OS account of the same name connect directly and skip its
-- login role. Only SET ROLE reaches a data role, so the login is removed here.
--
-- Run from the console ([K] in the main menu). Not applied by checkclasses: that only
-- imports a table's SQL when the table is missing, so existing databases never re-run
-- pgrole.sql.
--
-- Idempotent: roles already NOLOGIN are not touched. Superusers and 'jam' (the legacy
-- owner mapping) are skipped. Only m_-prefixed tracked roles are changed.
do $$
declare
  r record;
begin
  for r in
    select pr.rolname
      from engine.pgrole pr
      join pg_roles pg on pg.rolname = pr.rolname
     where pr.rolname like 'm\_%'
       and pr.rolname <> 'jam'
       and pg.rolcanlogin
       and not pg.rolsuper
  loop
    execute format('alter role %I nologin', r.rolname);
    raise notice 'pgrole: set nologin on %', r.rolname;
  end loop;
end $$;
