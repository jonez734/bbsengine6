--\echo notify_rate_limit

-- Per-user per-type rate limit tracking (for database-accessible rate limit capacity)
create table engine.__notify_rate_limit (
    "sender_moniker" citext not null constraint fk_notify_rate_limit_sender
        references engine.__member(moniker) on update cascade on delete cascade,
    "notification_type" text not null constraint fk_notify_rate_limit_type
        references engine.__notify_type(type_name) on update cascade on delete cascade,
    "send_count" integer default 0,
    "window_start" timestamptz not null,
    "last_updated" timestamptz default now(),
    constraint pk_notify_rate_limit primary key (sender_moniker, notification_type)
);

-- Indexes for __notify_rate_limit
create index idx_engine_notify_rate_limit_window on engine.__notify_rate_limit(window_start);

-- Grants
grant all on engine.__notify_rate_limit to web, sysop, term;
