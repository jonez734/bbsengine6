--\echo pgrole.sql
--
-- Per-member PostgreSQL role tracking for direct psql access.
-- Auth is by ident (see handbook/specs/pg-ident-auth.md); the
-- l_<loginid> roles are created here with no password.
--
-- The 'member' group role below is the "every approved member" floor.
-- All l_<loginid> roles are GRANTed membership in 'member', and the
-- baseline SELECT/usage grants are issued to 'member' rather than to
-- each l_<loginid> role individually.

create table engine.pgrole (
  memberid     bigint primary key references engine.__member(id) on delete cascade,
  rolname      name not null unique,
  osuser       text,
  created_at   timestamptz not null default now(),
  last_ack_at  timestamptz
);

grant select, insert, update, delete on engine.pgrole to web;

-- 'member' group role. NOLOGIN, NOINHERIT so grants don't accidentally
-- chain through l_* roles to DSN users.
do $$ begin
  if not exists (select 1 from pg_roles where rolname = 'member') then
    create role member nologin noinherit nosuperuser nocreatedb nocreaterole;
  end if;
end $$;

-- Baseline: schema usage and SELECT on existing tables in both
-- engine and bank. New per-member write tables should grant to
-- 'member' explicitly.
grant usage on schema engine to member;
grant select on all tables in schema engine to member;
alter default privileges in schema engine grant select on tables to member;

-- bank schema is optional; the engine_member group is still useful
-- without it. Grant lazily so pgrole.sql is safe to apply in
-- minimal/dev environments.
do $$ begin
  if exists (select 1 from pg_namespace where nspname = 'bank') then
    execute 'grant usage on schema bank to member';
    execute 'grant select on all tables in schema bank to member';
    execute 'alter default privileges in schema bank grant select on tables to member';
  end if;
end $$;

-- 'member' may need to read its own tracking row in engine.pgrole
-- when the deferred 'web -> psql via SET LOCAL ROLE' work is picked
-- up. Granting now keeps the migration trivial when that day comes.
grant select on engine.pgrole to member;
