-- engine.pgrole stays keyed by membermoniker, with rolname as its data role. The OS login column
-- (osuser) is removed: the member's loginid is the OS login, read from engine.__member when needed.
-- The [O] menu option is gone, so nothing writes osuser.
--
-- Idempotent: safe to run on a database already migrated. Run as one transaction:
--   psql -v ON_ERROR_STOP=1 -1 -f pgrole_loginid_migration.sql

-- 1. The view that exposes osuser is rebuilt without it, so the drop does not need CASCADE.
drop view if exists engine.pgrole_member;

-- 2. Remove the OS login column.
alter table engine.pgrole drop column if exists osuser;

-- 3. Recreate the member view on the loginid taken from engine.__member.
create or replace view engine.pgrole_member as
    select
        mm.moniker,
        mm.loginid,
        pr.rolname
      from engine.__member as mm
      left outer join engine.pgrole as pr on pr.membermoniker = mm.moniker
;
grant select on engine.pgrole_member to sysop, member;
