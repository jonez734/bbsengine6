create table engine.member_flag (
  "name" citext unique not null primary key,
  "description" text,
  "defaultvalue" boolean
);

grant select on engine.member_flag to web, term, member;
grant insert, delete, update on engine.member_flag to sysop;
