\echo blurb.sql

-- Drop old sequence if exists (replaced by text IDs)
-- DROP SEQUENCE IF EXISTS engine.__blurb_id_seq;

CREATE TABLE IF NOT EXISTS engine.__blurb (
    "id" text UNIQUE NOT NULL PRIMARY KEY,
    "parentid" text CONSTRAINT fk_engine_blurb_parentid REFERENCES engine.__blurb(id) ON UPDATE CASCADE ON DELETE SET NULL,
    "kind" text,
    "attributes" jsonb,
    "contentfilename" text,
    "folders" ltree[],
    "datecreated" timestamptz,
    "createdbymoniker" citext CONSTRAINT fk_engine_blurb_createdbyid REFERENCES engine.__member(moniker) ON UPDATE CASCADE ON DELETE SET NULL,
    "dateupdated" timestamptz,
    "updatedbymoniker" citext CONSTRAINT fk_engine_blurb_updatedbyid REFERENCES engine.__member(moniker) ON UPDATE CASCADE ON DELETE SET NULL,
    "dateapproved" timestamptz,
    "approvedbymoniker" citext CONSTRAINT fk_engine_blurb_approvedbyid REFERENCES engine.__member(moniker) ON UPDATE CASCADE ON DELETE SET NULL
);

GRANT INSERT, UPDATE, DELETE ON engine.__blurb TO web, term;
GRANT SELECT ON engine.__blurb TO web, term;

CREATE INDEX idx_blurb_attributes ON engine.__blurb USING gin (attributes);

CREATE TABLE IF NOT EXISTS engine.map_blurb_sig (
    "blurbid" text CONSTRAINT fk_engine_map_blurb_sig_blurbid REFERENCES engine.__blurb(id) ON UPDATE CASCADE ON DELETE CASCADE,
    "sigpath" ltree CONSTRAINT fk_engine_map_blurb_sig_sigpath REFERENCES engine.__folder(path) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_map_blurb_sig ON engine.map_blurb_sig (blurbid, sigpath);
GRANT INSERT, UPDATE, DELETE, SELECT ON engine.map_blurb_sig TO web;
