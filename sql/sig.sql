\echo sig
create table engine.__sig (
--    id bigserial not null primary key,
    "path" ltree unique not null primary key,
    "uri"  text unique,
    "title" text,
    "name" text,
    "intro" text,
    "attributes" jsonb,
    "dateupdated" timestamptz,
    "updatedbyid" bigint constraint fk_engine_sig_updatedbyid references engine.__member(id) on update cascade on delete set null,
    "dateapproved" timestamptz,
    "approvedbyid" bigint constraint fk_engine_sig_approvedbyid references engine.__member(id) on update cascade on delete set null,
    "datecreated" timestamptz,
    "createdbyid" bigint constraint fk_engine_sig_createdbyid references engine.__member(id) on update cascade on delete set null
);

create view engine.sig as
 select 
  s.*,
  coalesce(m1.name, 'a. nonymous'::text) as createdbyname,
  coalesce(m2.name, 'a. nonymous'::text) as updatedbyname
 from engine.__sig as s
 left join engine.__member as m1 ON (m1.id = s.createdbyid)
 left join engine.__member as m2 ON (m2.id = s.updatedbyid)
;

--create unique index idx_engine_sig_path on engine.__sig(path);

grant select on engine.sig to apache;

grant all on table engine.__sig to apache;
--grant all on sequence engine.__sig_id_seq to apache;
