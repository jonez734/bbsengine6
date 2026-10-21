-- Named message sources (system senders). A source is a string such as
-- 'casino.dealer:<table>' or 'postoffice'. A named source may address only
-- the group-name prefixes registered here. Unregistered sources may address
-- nothing. 'member' and 'operator' are not rows here: they are governed by
-- the existing sender rules.
create table engine.__message_source (
    "source" text not null primary key,
    "group_prefix" text not null,
    "description" text,
    "datecreated" timestamptz default now(),
    unique(source, group_prefix)
);

create index idx_engine_message_source_prefix on engine.__message_source(group_prefix);
