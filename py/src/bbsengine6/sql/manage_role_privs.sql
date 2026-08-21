CREATE OR REPLACE FUNCTION public.manage_role_privs(role_name TEXT, action TEXT, priv TEXT)
RETURNS VOID
security definer
language plpgsql
AS $$
BEGIN
    -- Only a SUPERUSER may ALTER ROLE on a role that has rolsuper=True.
    -- manage_role_privs runs as the SECURITY DEFINER owner (zoid6,
    -- NOSUPERUSER), so trying to alter a SUPERUSER role raises
    -- InsufficientPrivilege and rolls back the caller's transaction.
    -- Skip silently (with a NOTICE) when the target is SUPERUSER: the
    -- operator asked us not to remove SUPERUSER automatically.
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = role_name AND rolsuper) THEN
        RAISE NOTICE 'manage_role_privs: role % has SUPERUSER; skipping % % (requires SUPERUSER to alter)',
            role_name, action, priv;
        RETURN;
    END IF;

    -- Check if action is 'grant' or 'revoke'
    IF action = 'grant' THEN
        -- Grant privilege to the role
        EXECUTE format('ALTER ROLE %I %s', role_name, priv);
    ELSIF action = 'revoke' THEN
        -- Revoke privilege from the role
        EXECUTE format('ALTER ROLE %I NO%s', role_name, priv);
    ELSE
        RAISE EXCEPTION 'Invalid action. Use ''grant'' or ''revoke''.';
    END IF;
END;
$$;

grant execute on function public.manage_role_privs to sysop;
