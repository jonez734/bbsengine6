\echo node.sql
--create extension ltree; -- moved to extensions.sql

create table if not exists engine.__node (
    "id" bigserial unique not null primary key,
    "parentid" bigint constraint fk_engine_node_parentid references engine.__node(id) on update cascade on delete set null,
    "prg" text,
    "attributes" jsonb,
    "datecreated" timestamptz,
    "createdbyid" bigint constraint fk_engine_node_createdbyid references engine.__member(id) on update cascade on delete set null,
    "dateupdated" timestamptz,
    "updatedbyid" bigint constraint fk_engine_node_updatedbyid references engine.__member(id) on update cascade on delete set null,
    "dateapproved" timestamptz,
    "approvedbyid" bigint constraint fk_engine_node_approvedbyid references engine.__member(id) on update cascade on delete set null
);

-- create index idx_node_tags on engine.__node using gist(tags);

grant insert, update, delete on engine.__node to apache;

create index idx_node_attributes ON engine.__node USING GIN (attributes);

create table if not exists engine.map_node_sig (
    "nodeid" bigint constraint fk_engine_map_node_sig_nodeid references engine.__node(id) on update cascade on delete cascade,
    "sigpath" ltree constraint fk_engine_map_node_sig_sigpath references engine.__sig(path) on update cascade on delete cascade
);

create unique index if not exists idx_map_node_sig on engine.map_node_sig (nodeid, sigpath);

grant insert, update, delete, select on engine.map_node_sig to apache;

\echo grant engine.__node_id_seq
grant select, update on engine.__node_id_seq to apache;

-- alter table engine.__node add column parentid bigint;
-- alter table engine.__node add constraint fk_engine_node_parentid foreign key (parentid) references engine.__node(id) on update cascade on delete set null;
-- create unique index if not exists idx_node_attr_playername_unique on engine.__node( (attributes->>'playername') ); -- playername) ); -- attributes->>'playername') ) ;
