--\echo flag
create table engine.flag (
  "name" citext unique not null primary key,
  "description" text,
  "defaultvalue" boolean
);

grant select on engine.flag to web, term;
grant all on engine.flag to sysop;

--create table engine.map_blurb_flag (
--  "blurbid" bigint constraint fk_mbf_blurbid references engine.__blurb(id) on update cascade on delete cascade,
--  "name" text not null constraint fk_mbf_name references engine.flag(name) on update cascade on delete cascade,
--  "value" text
--);

---grant all on engine.flag, engine.map_member_flag to apache;
--grant select on engine.flag, engine.map_member_flag, engine.map_blurb_flag to :web;
--grant all on engine.flag, engine.map_member_flag, engine.map_blurb_flag to :bbs;
