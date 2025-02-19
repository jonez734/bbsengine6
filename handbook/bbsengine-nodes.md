version: python, php bbsengine5

node table
===========

- fields: "id", "parentid", "prg", "attributes", created/updated/approved timestamptz and memberid
- parentid can be used to make a 'threaded discussion system' (socrates)
- prg is for the type of node, f.e. 'socrates.post'
- attributes is used for data custom to a specific type of node, f.e. 'subject' in 'socrates.post'

- typically used with a view:
create or replace view socrates.post as
    select
        n.*,
        (n.attributes->>'flags')::jsonb as flags,
        (n.attributes->>'title')::text as title,
        (n.attributes->>'body')::text as body,
        lastc.datecreated as datelastreply,
        lastc.createdbyid as lastreplycreatedbyid,
        coalesce(m1.name, 'a. nonymous'::text) as lastreplycreatedbyname
    from engine.node as n
    left join lateral (select datecreated, createdbyid from engine.node where parentid=n.id limit 1) as lastc on true left join engine.__member as m1 on (m1.id = lastc.createdbyid)
    where n.prg = 'socrates.post'
;

