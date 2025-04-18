\echo actionlog
create table engine.__actionlog (
    moniker text constraint fk_actionlog_moniker references engine.__member(moniker) on update cascade on delete cascade,
    action text not null,
    actiondate timestamptz,
    remoteaddr inet,
    note text
);

grant all on engine.__actionlog to web, sysop, term;

create or replace view engine.actionlog as
    select 
        a.*,
        timezone(currentmember.tz, a.actiondate) as actiondatelocal
    from engine.__actionlog as a
    left outer join engine.__member as currentmember on (currentmember.loginid = CURRENT_USER)
;

grant select on engine.actionlog to web, term, sysop;
