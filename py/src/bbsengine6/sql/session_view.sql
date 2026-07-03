create view engine.session as
    select
        s.*,
        extract(epoch from s.expiry) as expiryepoch,
        extract(epoch from s.lastactivity) as lastactivityepoch,
        timezone(currentmember.tz, lastactivity) as lastactivitylocal,
        timezone(currentmember.tz, expiry) as expirylocal

    from engine.__session as s
    left outer join engine.__member as currentmember on (currentmember.loginid = CURRENT_USER)
;

create unique index idx_session_sessionid_unique on engine.__session(id);

grant select on engine.session to web, term, sysop, member;
