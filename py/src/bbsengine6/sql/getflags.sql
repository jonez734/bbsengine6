CREATE OR REPLACE FUNCTION engine.getflags(moniker citext)
RETURNS TABLE(name citext, description TEXT, value BOOLEAN) AS $$
BEGIN
    IF moniker IS NULL THEN
        -- Return default values when moniker is NULL
        RETURN QUERY
        SELECT
            f.name AS name,
            f.description AS description,
            f.defaultvalue AS value
        FROM
            engine.flag f;
    ELSE
        -- Return specific values when moniker is provided
        RETURN QUERY
        SELECT
            f.name AS name,
            f.description AS description,
            COALESCE(m.value, f.defaultvalue) AS value
        FROM
            engine.member_flag f
        LEFT JOIN
            engine.map_member_flag m ON m.name = f.name AND lower(m.moniker) = lower(getflags.moniker)
        WHERE
            EXISTS (SELECT 1 FROM engine.member WHERE lower(engine.member.moniker) = lower(getflags.moniker) OR lower(engine.member.loginid) = lower(getflags.moniker));
    END IF;
END;
$$ LANGUAGE plpgsql;

grant EXECUTE on function engine.getflags to web, term, sysop, member;
