\echo flag.sql
create table engine.flag (
  "name" text unique not null primary key,
  "description" text,
  "defaultvalue" boolean
);

create table engine.map_member_flag (
  "memberid" bigint constraint fk_mmf_memberid references engine.__member(id) on update cascade on delete cascade,
  "name" text not null constraint fk_mmf_name references engine.flag(name) on update cascade on delete cascade,
  "value" boolean
);

grant all on engine.flag, engine.map_member_flag to apache;
