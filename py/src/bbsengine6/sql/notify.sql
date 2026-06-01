--\echo notify

-- Create ENUM type for notification urgency
create type engine.notify_urgency_enum as enum (
    'ROUTINE',
    'IMPORTANT',
    'URGENT',
    'CRITICAL'
);

-- Core notification storage
create table engine.__notify (
    "id" bigserial unique not null primary key,
    "notification_type" text not null,
    "sender_moniker" citext constraint fk_notify_sender_moniker 
        references engine.__member(moniker) on update cascade on delete set null,
    "template" text not null,
    "template_vars" jsonb,
    "rendered_message" text not null,
    "data" jsonb,
    "urgency" engine.notify_urgency_enum default 'ROUTINE'::engine.notify_urgency_enum,
    "should_persist" boolean default true,
    "datecreated" timestamptz default now(),
    "createdbymoniker" citext constraint fk_notify_createdby 
        references engine.__member(moniker) on update cascade on delete set null,
    "mac" text
);

-- Indexes for __notify
create index idx_engine_notify_type on engine.__notify(notification_type);
create index idx_engine_notify_created on engine.__notify(datecreated desc);
create index idx_engine_notify_data on engine.__notify using gin(data);
create index idx_engine_notify_sender on engine.__notify(sender_moniker);

-- Grants
grant all on engine.__notify to web, sysop, term;
grant all on engine.__notify_id_seq to web, sysop, term;
grant usage on type engine.notify_urgency_enum to web, sysop, term;
