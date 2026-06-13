--\echo notify_type

-- Notification type registration and rate limit configuration
drop table if exists engine.__notify_type;
create table engine.__notify_type (
    "type_name" text primary key,
    "default_urgency" engine.notify_urgency_enum default 'ROUTINE'::engine.notify_urgency_enum,
    "max_per_user_per_hour" integer default 10,
    "persist_by_default" boolean default true,
    "dateregistered" timestamptz default now(),
    "registeredbymoniker" citext constraint fk_notify_type_registeredby
        references engine.__member(moniker) on update cascade on delete set null
);

-- Grants
grant all on engine.__notify_type to web, sysop, term;
