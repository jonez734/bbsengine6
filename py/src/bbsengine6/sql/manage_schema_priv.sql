-- TODO(remove-after-postgres-drop): the SET ROLE postgres / RESET ROLE
-- block below is kept for backward compatibility with databases
-- bootstrapped under the previous ownership model. Once
-- `acceptable_owners` in backend.checkengine drops "postgres" (see
-- bbsengine6/TODO_zoid6_role.md), delete the SET ROLE / RESET ROLE
-- lines and let the connecting superuser create the function; the
-- stage_zero `checkzoid6owner` module will then transfer ownership to
-- the dedicated `zoid6` role.
--
-- Run as a superuser (e.g. jam). The role switch only affects DDL,
-- and only for the duration of the connection.
SET ROLE postgres;

CREATE OR REPLACE FUNCTION manage_schema_priv(
    action TEXT,
    priv TEXT,
    target_schema TEXT,
    target_role TEXT
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    IF lower(action) = 'grant' THEN
        EXECUTE format('GRANT %s ON SCHEMA %I TO %I', priv, target_schema, target_role);
    ELSIF lower(action) = 'revoke' THEN
        EXECUTE format('REVOKE %s ON SCHEMA %I FROM %I', priv, target_schema, target_role);
    ELSE
        RAISE EXCEPTION 'Invalid action: %, must be grant or revoke', action;
    END IF;
END;
$$;

RESET ROLE;

grant execute on function public.manage_schema_priv to sysop;
