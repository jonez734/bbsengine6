-- bbsengine6/sql/migrate_session_remoteaddr.sql
-- Renames the session address column to remoteaddr and adds remoteaddr_source (the address's
-- origin: utmp or ssh_env). Idempotent. Run once per existing database; fresh installs get the
-- same shape from session.sql.
--
-- The address column is dropped and re-added, not renamed. That is only safe when no session has
-- an address. The guard below stops the migration if any does, so nothing is discarded silently.
-- Check by hand first:
--   select count(*) from engine.__session where ipaddress is not null;
--
-- engine.session selects s.*, so it is recreated after the column change (definition copied from
-- session_view.sql, which must be kept in step with this file).

begin;

do $$
declare
    n bigint;
begin
    if exists (
        select 1 from information_schema.columns
        where table_schema = 'engine' and table_name = '__session' and column_name = 'ipaddress'
    ) then
        execute 'select count(*) from engine.__session where ipaddress is not null' into n;
        if n > 0 then
            raise exception 'engine.__session has % rows with ipaddress set; migrate them by hand first', n;
        end if;
    end if;
end
$$;

drop view if exists engine.session;

alter table engine.__session drop column if exists ipaddress;
alter table engine.__session add column if not exists remoteaddr inet;
alter table engine.__session add column if not exists remoteaddr_source text;

do $$
begin
    if not exists (
        select 1 from pg_constraint
        where conrelid = 'engine.__session'::regclass
          and conname in ('remoteaddr_source_check', '__session_remoteaddr_source_check')
    ) then
        alter table engine.__session
            add constraint remoteaddr_source_check
            check (remoteaddr_source in ('utmp', 'ssh_env'));
    end if;
end
$$;

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

create unique index if not exists idx_session_sessionid_unique on engine.__session(id);

grant select on engine.session to web, term, sysop, member;

commit;
