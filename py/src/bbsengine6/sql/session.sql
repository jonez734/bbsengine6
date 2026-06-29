--\echo session.sql
--
-- Name: session; Type: TABLE; Schema: public; Owner: jam; Tablespace: 
--

CREATE TABLE engine.__session (
    id text unique not null primary key,
    expiry timestamptz,
    lastactivity timestamptz,
    data jsonb not null,
    ipaddress inet,
    useragent text,
    datecreated timestamptz,
    dateupdated timestamptz,
    moniker citext constraint fk_session_moniker references engine.__member(moniker) on update cascade on delete cascade
);

grant select, insert, update, delete on engine.__session to web, term, sysop;
-- member is intentionally NOT granted write on __session; see pgrole.sql
-- and handbook/specs/pg-ident-auth.md.

--alter table engine.__session
--add constraint "fk_session_memberid"
--foreign key (memberid)
--references engine.__member(id) on update cascade on delete set null;

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
