create table engine.map_member_flag (
  "moniker" citext constraint fk_mmf_membermoniker references engine.__member(moniker) on update cascade on delete cascade,
  "name" citext not null constraint fk_mmf_name references engine.flag(name) on update cascade on delete cascade,
  "value" boolean
);

create unique index if not exists idx_map_member_flag on engine.map_member_flag (moniker, name);

grant select on engine.map_member_flag to web, term;
grant all on engine.map_member_flag to sysop;
