--\echo sig
create table engine.__sig (
    "path" ltree unique not null primary key,
    "uri"  text unique,
    "title" text,
    "intro" text,
    "attrs" jsonb,
    "access" jsonb,
    "dateupdated" timestamptz,
    "updatedbymoniker" citext constraint fk_engine_sig_updatedbymoniker references engine.__member(moniker) on update cascade on delete set null,
    "dateapproved" timestamptz,
    "approvedbymoniker" citext constraint fk_engine_sig_approvedbymoniker references engine.__member(moniker) on update cascade on delete set null,
    "datecreated" timestamptz,
    "createdbymoniker" citext constraint fk_engine_sig_createdbymoniker references engine.__member(moniker) on update cascade on delete set null
);

CREATE INDEX idx_sig_attrs ON engine.__sig USING gin (attrs);

grant select on table engine.__sig to web;
grant all on table engine.__sig to sysop, term;
