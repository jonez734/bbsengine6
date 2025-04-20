\echo buildsiguri.sql
---create or replace function engine.buildsiguri(sigpath ltree)
---returns text as $$
---    res = []
---    for p in sigpath:
---      if p is not None:
---        p = p.replace("top", "")
---        p = p.replace("top.", "")
---        p = p.replace("_", "-")
---#        p = p.replace(".", "/")
---#        p = p + "/"
---#        p = p.replace("//", "/")
---#        p = p.lstrip("/")
---        if p is not None and p != "":
---          res.append(p)
---    uri = "/".join(res)+"/"
---    uri = uri.lstrip("/")
---    return uri
---
---$$
---language plpython3u transform for type ltree;

-- @since 20241011
CREATE OR REPLACE FUNCTION engine.buildsiguri(sigpath ltree, topreplace text DEFAULT 'top')
RETURNS text
LANGUAGE plpgsql
AS $$
DECLARE
    res text[] := '{}';  -- Array to store the result segments
    p text;
    uri text;
BEGIN
    -- Iterate over each label in the ltree (ltree is an array of text elements)
    FOR p IN SELECT * FROM string_to_array(text2ltree(sigpath::text), '.') LOOP
        -- Perform replacements equivalent to the Python version
        IF p IS NOT NULL THEN
            -- Use the 'topreplace' argument for replacing 'top' or the custom value
            p := replace(p, topreplace, '');
            p := replace(p, topreplace || '.', '');
            p := replace(p, '_', '-');
            -- The following parts are commented out in the original code:
            p := replace(p, '.', '/');
            p := p || '/';
            p := replace(p, '//', '/');
            p := ltrim(p, '/');

            -- Ensure that the modified string is not empty before adding it to the result array
            IF p IS NOT NULL AND p != '' THEN
                res := array_append(res, p);
            END IF;
        END IF;
    END LOOP;

    -- Join the array elements into a URI-like structure
    uri := array_to_string(res, '/');

    -- Ensure the URI starts without leading slashes
    uri := ltrim(uri, '/');

    -- Append trailing slash
    uri := uri || '/';

    RETURN uri;
END;
$$;
