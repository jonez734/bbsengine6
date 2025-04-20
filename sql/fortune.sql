\echo fortune.sql
--CREATE TABLE engine.__mantra (
--    id serial unique not null primary key,
--    description text,
--    author text,
--    reference text,
--    datecreated timestamp with time zone,
--    createdbyid integer constraint fk_mantra_postedbyid references engine.__member(id) on update cascade on delete set null,
--    dateupdated timestamp with time zone,
--    updatedbyid integer constraint fk_mantra_modifiedbyid references engine.__member(id) on update cascade on delete set null
--);

create view engine.fortune as
    select 
        *,
        (attributes->>'description') as description,
        (attributes->>'author') as author,
        (attributes->>'reference') as reference
    from engine.__blurb
;

grant select on engine.fortune to web;
