-- engine.actionlog: the action log with the viewer's local time zone.
--
-- Reads engine.__actionlog (actionlog.sql). The join matches the current database user to a
-- member by loginid, which is the identity model approved for member lookup.
create or replace view engine.actionlog as
    select
        a.*,
        timezone(currentmember.tz, a.actiondate) as actiondatelocal
    from engine.__actionlog as a
    left outer join engine.__member as currentmember on (currentmember.loginid = CURRENT_USER)
;

grant select on engine.actionlog to web, term, sysop, member;
