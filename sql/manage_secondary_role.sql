CREATE OR REPLACE FUNCTION engine.manage_secondary_role(
    role_name TEXT,
    action TEXT,
    secondary_role TEXT
) RETURNS VOID AS
$$
BEGIN
    IF action = 'add' THEN
        EXECUTE format('GRANT %I TO %I', secondary_role, role_name);
    ELSIF action = 'remove' THEN
        EXECUTE format('REVOKE %I FROM %I', secondary_role, role_name);
    ELSE
        RAISE EXCEPTION 'Invalid action. Must be "add" or "remove".';
    END IF;
END;
$$
LANGUAGE plpgsql;

grant execute on function engine.manage_secondary_role to sysop;
