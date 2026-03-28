--\echo notify_recipient

-- Per-recipient notification tracking (delivery, read, blocked status)
create table engine.__notify_recipient (
    "notify_id" bigint not null constraint fk_notify_recipient_notify_id
        references engine.__notify(id) on update cascade on delete cascade,
    "recipient_moniker" citext not null constraint fk_notify_recipient_moniker
        references engine.__member(moniker) on update cascade on delete cascade,
    "sessionid" text constraint fk_notify_recipient_sessionid
        references engine.__session(id) on update cascade on delete set null,
    "is_blocked" boolean default false,
    "delivered_at" timestamptz,
    "read_at" timestamptz,
    "datecreated" timestamptz default now(),
    constraint pk_notify_recipient primary key (notify_id, recipient_moniker)
);

-- Indexes for __notify_recipient
create index idx_engine_notify_recipient_moniker on engine.__notify_recipient(recipient_moniker);
create index idx_engine_notify_recipient_read on engine.__notify_recipient(read_at) where read_at is null;
create index idx_engine_notify_recipient_blocked on engine.__notify_recipient(is_blocked) where is_blocked = true;
create index idx_engine_notify_recipient_session on engine.__notify_recipient(sessionid);

-- Grants
grant all on engine.__notify_recipient to web, sysop, term;
