-- engine.pgrole_member: one row per member with the psql role they use.
--
-- The data role (rolname, NOLOGIN) holds the member's privileges. The login role is named for
-- the member's loginid, which is also the OS login ident maps to.

create or replace view engine.pgrole_member as
    select
        mm.moniker,
        mm.loginid,
        pr.rolname
      from engine.__member as mm
      left outer join engine.pgrole as pr on pr.membermoniker = mm.moniker
;

grant select on engine.pgrole_member to sysop, member;
