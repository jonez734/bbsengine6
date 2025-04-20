CREATE OR REPLACE FUNCTION createschema(name text)
RETURNS void AS $$
BEGIN
    EXECUTE format('CREATE SCHEMA %I', name);
END;
$$ LANGUAGE plpgsql;
