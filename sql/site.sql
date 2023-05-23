create view engine.site as
    select
        *,
        (attributes->>'name')::text as name,
        (attributes->>'httpauth')::boolean as httpauth,
        (attributes->>'baseurl')::text as baseurl,
        (attributes->>'fqdn')::text as fqdn
    from engine.blurb
    where prg='engine.site'
---    where attributes ? 'baseurl' and attributes ? 'fqdn' and attributes ? 'httpauth' and attributes ? 'name'
;
