-- \echo message

-- Core message storage for unified pub/sub system
create table engine.__message (
    "id" bigserial unique not null primary key,
    "channel" text not null,
    "sender_moniker" citext constraint fk_message_sender_moniker 
        references engine.__member(moniker) on update cascade on delete set null,
    "content" text not null,
    "data" jsonb,
    "urgency" engine.notify_urgency_enum default 'ROUTINE'::engine.notify_urgency_enum,
    "template" text,
    "template_vars" jsonb,
    "datestamp" timestamptz default now()
);

-- Indexes for __message
create index idx_engine_message_channel on engine.__message(channel);
create index idx_engine_message_sender on engine.__message(sender_moniker);
create index idx_engine_message_datestamp on engine.__message(datestamp desc);
create index idx_engine_message_data on engine.__message using gin(data);

-- Per-recipient delivery tracking
create table engine.__message_recipient (
    "id" bigserial unique not null primary key,
    "message_id" bigint not null constraint fk_message_recipient_message 
        references engine.__message(id) on delete cascade,
    "recipient_moniker" citext not null constraint fk_message_recipient_recipient 
        references engine.__member(moniker) on update cascade on delete cascade,
    "status" text not null default 'pending'::text,  -- pending, delivered, read
    "datedelivered" timestamptz,
    "dateread" timestamptz,
    unique(message_id, recipient_moniker)
);

-- Indexes for __message_recipient
create index idx_engine_message_recipient_msg on engine.__message_recipient(message_id);
create index idx_engine_message_recipient_recipient on engine.__message_recipient(recipient_moniker);
create index idx_engine_message_recipient_status on engine.__message_recipient(status);

-- Grants
grant all on engine.__message to web, sysop, term;
grant all on engine.__message_id_seq to web, sysop, term;
grant all on engine.__message_recipient to web, sysop, term;
grant all on engine.__message_recipient_id_seq to web, sysop, term;
