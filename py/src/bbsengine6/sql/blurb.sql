\echo blurb.sql

create table if not exists engine.__blurb (
    "id" bigserial unique not null primary key,
    "parentid" bigint constraint fk_engine_blurb_parentid references engine.__blurb(id) on update cascade on delete set null,
    "prg" text,
--    "flags" jsonb,
    "attributes" jsonb,
    "datecreated" timestamptz,
    "createdbymoniker" citext constraint fk_engine_blurb_createdbyid references engine.__member(moniker) on update cascade on delete set null,
    "dateupdated" timestamptz,
    "updatedbymoniker" citext constraint fk_engine_blurb_updatedbyid references engine.__member(moniker) on update cascade on delete set null,
    "dateapproved" timestamptz,
    "approvedbymoniker" citext constraint fk_engine_blurb_approvedbyid references engine.__member(moniker) on update cascade on delete set null
);

-- create index idx_node_tags on engine.__node using gist(tags);

grant insert, update, delete on engine.__blurb to web, term;

create index idx_blurb_attributes ON engine.__blurb USING GIN (attributes);

create table if not exists engine.map_blurb_sig (
    "blurbid" bigint constraint fk_engine_map_blurb_sig_blurbid references engine.__blurb(id) on update cascade on delete cascade,
    "sigpath" ltree constraint fk_engine_map_blurb_sig_sigpath references engine.__sig(path) on update cascade on delete cascade
);

create unique index if not exists idx_map_blurb_sig on engine.map_blurb_sig (blurbid, sigpath);

grant insert, update, delete, select on engine.map_blurb_sig to web;

\echo grant engine.__blurb_id_seq
grant select, update on engine.__blurb_id_seq to web;

-- alter table engine.__node add column parentid bigint;
-- alter table engine.__node add constraint fk_engine_node_parentid foreign key (parentid) references engine.__node(id) on update cascade on delete set null;
-- create unique index if not exists idx_node_attr_playername_unique on engine.__node( (attributes->>'playername') ); -- playername) ); -- attributes->>'playername') ) ;
