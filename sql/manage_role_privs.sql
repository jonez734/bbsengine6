CREATE OR REPLACE FUNCTION public.manage_role_privs(role_name TEXT, action TEXT, priv TEXT)
RETURNS VOID AS $$
BEGIN
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
$$ LANGUAGE plpgsql;

grant execute on function public.manage_role_privs to sysop;
