CREATE OR REPLACE FUNCTION manage_database_priv(
    action TEXT,
    priv TEXT,
    target_db TEXT,
    target_role TEXT
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    IF action = 'grant' THEN
        EXECUTE format('GRANT %I ON DATABASE %I TO %I', priv, target_db, target_role);
    ELSIF action = 'revoke' THEN
        EXECUTE format('REVOKE %I ON DATABASE %I FROM %I', priv, target_db, target_role);
    ELSE
        RAISE EXCEPTION 'Invalid action: %, must be grant or revoke', action;
    END IF;
END;
$$;
