-- public.manage_priv: one privilege dispatcher for role, schema and database privileges.
--
-- manage_role_privs, manage_schema_priv and manage_database_priv each grant or revoke one
-- privilege, and differ only in the statement they build and their guards. This function takes a
-- kind and dispatches to the same statement each old helper built, so behavior is unchanged. The
-- three old names remain as thin wrappers with their current signatures, so callers do not change.
--
-- Each branch keeps its original quoting and guards:
--   role:      ALTER ROLE (NO<priv> to revoke). A SUPERUSER target is skipped with a NOTICE.
--   schema:    GRANT/REVOKE <priv> ON SCHEMA. The privilege is not identifier-quoted.
--   database:  GRANT/REVOKE <priv> ON DATABASE. The privilege is identifier-quoted.
--
-- The role argument order is (kind, action, priv, target_name, target_role) for schema and
-- database, and (kind, action, priv, target_name) for role. Installed by checkfunctions as the
-- owner (zoid6). Idempotent.

create or replace function public.manage_priv(
    p_kind text,
    p_action text,
    p_priv text,
    p_target text,
    p_role text default null
)
returns void
language plpgsql
security definer
set search_path = public, pg_temp
as $$
begin
    if p_kind = 'role' then
        if exists (select 1 from pg_roles where rolname = p_target and rolsuper) then
            raise notice 'manage_priv: role % has SUPERUSER; skipping % % (requires SUPERUSER to alter)',
                p_target, p_action, p_priv;
            return;
        end if;
        if lower(p_action) = 'grant' then
            execute format('ALTER ROLE %I %s', p_target, p_priv);
        elsif lower(p_action) = 'revoke' then
            execute format('ALTER ROLE %I NO%s', p_target, p_priv);
        else
            raise exception 'Invalid action. Use ''grant'' or ''revoke''.';
        end if;

    elsif p_kind = 'schema' then
        if lower(p_action) = 'grant' then
            execute format('GRANT %s ON SCHEMA %I TO %I', p_priv, p_target, p_role);
        elsif lower(p_action) = 'revoke' then
            execute format('REVOKE %s ON SCHEMA %I FROM %I', p_priv, p_target, p_role);
        else
            raise exception 'Invalid action: %, must be grant or revoke', p_action;
        end if;

    elsif p_kind = 'database' then
        if p_action = 'grant' then
            execute format('GRANT %I ON DATABASE %I TO %I', p_priv, p_target, p_role);
        elsif p_action = 'revoke' then
            execute format('REVOKE %I ON DATABASE %I FROM %I', p_priv, p_target, p_role);
        else
            raise exception 'Invalid action: %, must be grant or revoke', p_action;
        end if;

    else
        raise exception 'manage_priv: unknown kind %', p_kind;
    end if;
end
$$;

alter function public.manage_priv(text, text, text, text, text) owner to zoid6;
revoke all on function public.manage_priv(text, text, text, text, text) from public;
grant execute on function public.manage_priv(text, text, text, text, text) to sysop;
