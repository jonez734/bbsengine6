create table if not exists engine.map_blurb_tag (
    "blurbid" bigint constraint fk_engine_map_blurb_tag_blurbid references engine.__blurb(id) on update cascade on delete cascade,
    "tag" text constraint fk_engine_map_blurb_tag_tag references engine.__tag(name) on update cascade on delete cascade
);

create unique index if not exists idx_map_blurb_tag on engine.map_blurb_tag (blurbid, tag);
