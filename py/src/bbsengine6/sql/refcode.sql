create table engine.__refcode (
    code citext unique not null primary key,
    createdbymoniker citext constraint fk_refcode_createdby references engine.__member(moniker) on update cascade on delete set null,
    datecreated timestamptz,
    status text,
    dateactivated timestamptz
);

grant select,update on engine.__refcode to web, term, member;
grant all on engine.__refcode to sysop;

create or replace view engine.refcode as
    select
        r.*,
        timezone(currentmember.tz, r.datecreated) as datecreatedlocal,
        timezone(currentmember.tz, r.dateactivated) as dateactivatedlocal
    from engine.__refcode as r
    left outer join engine.__member as currentmember on (currentmember.loginid = CURRENT_USER)
;

grant select on engine.refcode to web, term, member;
grant all on engine.refcode to sysop;

create table engine.map_refcode_use (
    code citext not null constraint fk_map_refcode_use references engine.__refcode(code) on update cascade on delete set null,
    usedbymoniker citext not null constraint fk_refcode_usedbymoniker references engine.__member(moniker) on update cascade on delete set null,
    dateused timestamptz
--    timezone(currentmember.tz, dateused) as dateusedlocal
)
--left outer join engine.__member as currentmember on (currentmember.loginid = CURRENT_USER)
;


grant all on engine.map_refcode_use to sysop;
grant select,update,insert on engine.map_refcode_use to web, term;
