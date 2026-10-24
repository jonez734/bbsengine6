-- engine.pgrole_member: one row per member with the psql roles they use.
--
-- The data role (rolname, NOLOGIN) holds the member's privileges; the login role
-- (osuser, LOGIN NOINHERIT) is the OS username ident maps to. osuser is NULL until the
-- sysop sets one. Use this view instead of repeating the join.

create or replace view engine.pgrole_member as
    select
        mm.moniker,
        mm.loginid,
        pr.rolname,
        pr.osuser
      from engine.__member as mm
      left outer join engine.pgrole as pr on pr.membermoniker = mm.moniker
;

grant select on engine.pgrole_member to sysop, member;
