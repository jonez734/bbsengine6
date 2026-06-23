-- message_groups.sql
-- Phase 1C: Groups, Blocking, Rate Limiting for unified message system

-- Message groups (distribution lists)
create table engine.__message_group (
    "id" bigserial unique not null primary key,
    "name" text not null unique,
    "description" text,
    "createdby" citext constraint fk_msg_group_creator 
        references engine.__member(moniker) on update cascade on delete set null,
    "datecreated" timestamptz default now()
);

create index idx_engine_message_group_name on engine.__message_group(name);

-- Group membership
create table engine.__message_group_member (
    "id" bigserial unique not null primary key,
    "group_id" bigint not null constraint fk_msg_group_member_group 
        references engine.__message_group(id) on delete cascade,
    "member_moniker" citext not null constraint fk_msg_group_member_moniker 
        references engine.__member(moniker) on update cascade on delete cascade,
    "addedby" citext constraint fk_msg_group_addedby 
        references engine.__member(moniker) on update cascade on delete set null,
    "dateadded" timestamptz default now(),
    unique(group_id, member_moniker)
);

create index idx_engine_message_group_member_group on engine.__message_group_member(group_id);
create index idx_engine_message_group_member_moniker on engine.__message_group_member(member_moniker);

-- Message blocks (senders blocked by recipients)
create table engine.__message_block (
    "id" bigserial unique not null primary key,
    "blocker_moniker" citext not null constraint fk_msg_block_blocker 
        references engine.__member(moniker) on update cascade on delete cascade,
    "blocked_moniker" citext not null constraint fk_msg_block_blocked 
        references engine.__member(moniker) on update cascade on delete cascade,
    "datereviewed" timestamptz default now(),
    unique(blocker_moniker, blocked_moniker)
);

create index idx_engine_message_block_blocker on engine.__message_block(blocker_moniker);
create index idx_engine_message_block_blocked on engine.__message_block(blocked_moniker);

-- Message types with rate limits
create table engine.__message_type (
    "id" bigserial unique not null primary key,
    "type_name" text not null unique,
    "description" text,
    "rate_limit_per_hour" integer default 0,  -- 0 = unlimited
    "requires_approval" boolean default false,
    "datemodified" timestamptz default now()
);

create index idx_engine_message_type_name on engine.__message_type(type_name);

-- Predefined message types
insert into engine.__message_type (type_name, description, rate_limit_per_hour) values
    ('system:announcements', 'System-wide announcements', 10),
    ('system:shout', 'Global chat/shout', 60),
    ('member:direct', 'Direct member-to-member messages', 120),
    ('casino:table', 'Casino table messages', 300),
    ('empyre:island', 'Empyre island messages', 300),
    ('murdermotel:room', 'Murder Motel room messages', 300);

-- Rate limit tracking
create table engine.__message_rate_limit (
    "id" bigserial unique not null primary key,
    "sender_moniker" citext not null constraint fk_msg_rate_sender 
        references engine.__member(moniker) on update cascade on delete cascade,
    "message_type" text not null,
    "hour_bucket" timestamptz not null,  -- truncated to hour
    "message_count" integer default 1,
    unique(sender_moniker, message_type, hour_bucket)
);

create index idx_engine_message_rate_limit_sender on engine.__message_rate_limit(sender_moniker, message_type, hour_bucket);
create index idx_engine_message_rate_limit_bucket on engine.__message_rate_limit(hour_bucket);

-- Grants
grant all on engine.__message_group to web, sysop, term;
grant all on engine.__message_group_id_seq to web, sysop, term;
grant all on engine.__message_group_member to web, sysop, term;
grant all on engine.__message_group_member_id_seq to web, sysop, term;
grant all on engine.__message_block to web, sysop, term;
grant all on engine.__message_block_id_seq to web, sysop, term;
grant all on engine.__message_type to web, sysop, term;
grant all on engine.__message_type_id_seq to web, sysop, term;
grant all on engine.__message_rate_limit to web, sysop, term;
grant all on engine.__message_rate_limit_id_seq to web, sysop, term;
