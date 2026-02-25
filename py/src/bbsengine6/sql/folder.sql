--\echo folder
create table engine.__folder (
    "path" ltree unique not null primary key,
    "uri"  text unique,
    "title" text,
    "intro" text,
    "attrs" jsonb,
    "access" jsonb,
    "dateupdated" timestamptz,
    "updatedbymoniker" citext constraint fk_engine_folder_updatedbymoniker references engine.__member(moniker) on update cascade on delete set null,
    "dateapproved" timestamptz,
    "approvedbymoniker" citext constraint fk_engine_folder_approvedbymoniker references engine.__member(moniker) on update cascade on delete set null,
    "datecreated" timestamptz,
    "createdbymoniker" citext constraint fk_engine_folder_createdbymoniker references engine.__member(moniker) on update cascade on delete set null
);

CREATE INDEX idx_folder_attrs ON engine.__folder USING gin (attrs);

grant select on table engine.__folder to web, term;
grant all on table engine.__folder to sysop;
