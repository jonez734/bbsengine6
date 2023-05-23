\echo session.sql
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
    memberid bigint constraint fk_session_memberid references engine.__member(id) on update cascade on delete cascade
);



--alter table engine.__session
--add constraint "fk_session_memberid"
--foreign key (memberid)
--references engine.__member(id) on update cascade on delete set null;

create view engine.session as
    select
        s.*,
        extract(epoch from s.expiry) as expiryepoch,
        extract(epoch from s.lastactivity) as lastactivityepoch
    from engine.__session as s
;

create unique index idx_session_sessionid_unique on engine.__session(id);

grant select on engine.session to "www-data";
grant insert, update, delete on engine.__session to "www-data";
