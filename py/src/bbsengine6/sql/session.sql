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

-- member is intentionally NOT granted write on __session; see pgrole.sql
-- and handbook/specs/pg-ident-auth.md.
grant select, insert, update, delete on engine.__session to web, term, sysop;

--alter table engine.__session
--add constraint "fk_session_memberid"
--foreign key (memberid)
--references engine.__member(id) on update cascade on delete set null;

