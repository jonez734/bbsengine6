CREATE OR REPLACE FUNCTION public.get_role_privs(rolname_input text)
RETURNS jsonb AS $$
DECLARE
    role_privileges jsonb;
BEGIN
    SELECT jsonb_build_object(
        'rolname', rolname,
        'rolsuper', rolsuper,
        'rolcreaterole', rolcreaterole,
        'rolcreatedb', rolcreatedb,
        'rolcanlogin', rolcanlogin,
        'rolreplication', rolreplication,
        'rolbypassrls', rolbypassrls
    )
    INTO role_privileges
    FROM pg_roles
    WHERE rolname = rolname_input;

    RETURN COALESCE(role_privileges, '{}'::jsonb); -- Return empty JSON if no privileges found
END;
$$ LANGUAGE plpgsql;

grant execute on function public.get_role_privs to sysop, term, web;
