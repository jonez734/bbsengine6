create table if not exists bank.__account (
    "id" bigserial primary key,
    "moniker" citext unique not null constraint chk_bankaccount_moniker_format check (
        moniker ~ '^[a-zA-Z0-9_]+$' OR moniker ~ '^[a-zA-Z0-9_]+:[a-zA-Z0-9_]+$'
    ),
    "balance" numeric(10,0) default 0,
    "minbalance" numeric(10,0) default 0,
    "maxtransfer" numeric(10,0) default 1000,
    "overdraft_limit" numeric(10,0) default 0,
    "attrs" jsonb default '{}',
    "created" timestamptz default now()
);

create index idx_bankaccount_moniker on bank.__account(moniker);

grant select on bank.__account to web;
grant all on bank.__account to term, sysop;
grant all on bank.__account_id_seq to term, sysop;
