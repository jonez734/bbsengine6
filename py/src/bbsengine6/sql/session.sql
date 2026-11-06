--\echo session.sql
--
-- Name: session; Type: TABLE; Schema: public; Owner: jam; Tablespace:
--

CREATE TABLE engine.__session (
    id text unique not null primary key,
    expiry timestamptz,
    lastactivity timestamptz,
    data jsonb not null,
    remoteaddr inet,
    -- Where remoteaddr came from. utmp: sshd's login record (written by sshd). ssh_env: the
    -- client's SSH environment (client-reported, not verified). NULL when no address was found.
    remoteaddr_source text constraint remoteaddr_source_check
        check (remoteaddr_source in ('utmp', 'ssh_env')),
    -- The login's terminal as utmp records it (pts/2, seat0, tty2), from the same record as remoteaddr.
    -- NULL when no live login record exists for this process.
    tty text,
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

