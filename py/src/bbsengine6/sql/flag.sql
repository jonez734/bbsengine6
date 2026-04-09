--\echo member_flag

create table engine.member_flag (
  "name" citext unique not null primary key,
  "description" text,
  "defaultvalue" boolean
);

grant select on engine.member_flag to web, term;
grant all on engine.member_flag to sysop;
