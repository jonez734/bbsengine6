--\echo map_member_flag
create table engine.map_member_flag (
  "moniker" citext constraint fk_mmf_moniker references engine.__member(moniker) on update cascade on delete cascade,
  "name" citext not null constraint fk_mmf_name references engine.member_flag(name) on update cascade on delete cascade,
  "value" boolean,
  "dateset" timestamptz,
  "setbymoniker" citext constraint fk_mlf_moniker references engine.__member(moniker) on update cascade on delete set null
);

grant all on engine.map_member_flag to sysop;
grant select on engine.map_member_flag to web, term;
