CREATE OR REPLACE FUNCTION public.manage_secondary_role(
    role_name TEXT,
    action TEXT,
    secondary_role TEXT
) RETURNS VOID AS
$$
BEGIN
    IF action = 'grant' THEN
        EXECUTE format('GRANT %I TO %I', secondary_role, role_name);
    ELSIF action = 'revoke' THEN
        EXECUTE format('REVOKE %I FROM %I', secondary_role, role_name);
    ELSE
        RAISE EXCEPTION 'Invalid action. Must be "grant" or "revoke".';
    END IF;
END;
$$
LANGUAGE plpgsql;

grant execute on function public.manage_secondary_role to sysop;
