--\echo flag

create table engine.flag (
  "name" citext unique not null primary key,
  "description" text,
  "defaultvalue" boolean
);

grant select on engine.flag to web, term;
grant all on engine.flag to sysop;

create table engine.blurb_flag (
  "name" citext unique not null primary key,
  "description" text
);

grant select on engine.blurb_flag to web, term;
grant all on engine.blurb_flag to sysop;

create table engine.map_blurb_flag (
  "blurbid" bigint constraint fk_mbf_blurbid references engine.__blurb(id) on update cascade on delete cascade,
  "name" citext not null constraint fk_mbf_name references engine.blurb_flag(name) on update cascade on delete cascade,
  "value" text
);

create unique index if not exists idx_map_blurb_flag on engine.map_blurb_flag (blurbid, name);

grant select on engine.map_blurb_flag to web;
grant all on engine.map_blurb_flag to term;
