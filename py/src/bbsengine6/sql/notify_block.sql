--\echo notify_block

-- One-way blocking relationships (blocker blocks sender)
create table engine.__notify_block (
    "blocker_moniker" citext not null constraint fk_notify_block_blocker
        references engine.__member(moniker) on update cascade on delete cascade,
    "sender_moniker" citext not null constraint fk_notify_block_sender
        references engine.__member(moniker) on update cascade on delete cascade,
    "datecreated" timestamptz default now(),
    "createdbymoniker" citext constraint fk_notify_block_createdby
        references engine.__member(moniker) on update cascade on delete set null,
    constraint pk_notify_block primary key (blocker_moniker, sender_moniker)
);

-- Indexes for __notify_block
create index idx_engine_notify_block_sender on engine.__notify_block(sender_moniker);

-- Grants
grant all on engine.__notify_block to web, sysop, term;
