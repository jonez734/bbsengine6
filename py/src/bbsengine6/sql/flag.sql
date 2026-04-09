--\echo flag

create table engine.flag (
  "name" citext unique not null primary key,
  "description" text,
  "defaultvalue" boolean
);

grant select on engine.flag to web, term;
grant all on engine.flag to sysop;
