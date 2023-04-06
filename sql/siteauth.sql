create view siteauth as
    select 
        *,
        (attributes->>'username')::text as username,
        (attributes->>'password')::text as password,
        (attributes->>'memberid')::bigint as memberid,
        (attributes->>'site')::text as site
    from engine.node
    where attributes ? 'username' and attributes ? 'password' and attributes ? 'memberid' and attributes ? 'site'
;
