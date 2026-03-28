--\echo notify_group

-- Group membership for notification targeting
create table engine.__notify_group (
    "group_name" text not null,
    "member_moniker" citext not null constraint fk_notify_group_member
        references engine.__member(moniker) on update cascade on delete cascade,
    "added_at" timestamptz default now(),
    "addedbymoniker" citext constraint fk_notify_group_addedby
        references engine.__member(moniker) on update cascade on delete set null,
    constraint pk_notify_group primary key (group_name, member_moniker)
);

-- Indexes for __notify_group
create index idx_engine_notify_group_member on engine.__notify_group(member_moniker);
create index idx_engine_notify_group_name on engine.__notify_group(group_name);

-- Grants
grant all on engine.__notify_group to web, sysop, term;
