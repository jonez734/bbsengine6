\echo buildsiguri.sql
create extension "ltree_plpython3u" cascade;

--create or replace language "plpython3u";

create or replace function engine.buildsiguri(sigpath ltree)
returns text as $$
    res = []
    for p in sigpath:
      if p is not None:
        p = p.replace("top", "")
        p = p.replace("top.", "")
        p = p.replace("_", "-")
#        p = p.replace(".", "/")
#        p = p + "/"
#        p = p.replace("//", "/")
#        p = p.lstrip("/")
        if p is not None and p != "":
          res.append(p)
    uri = "/".join(res)+"/"
    uri = uri.lstrip("/")
    return uri

$$
language plpython3u transform for type ltree;
