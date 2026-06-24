-- bbsengine6/sql/bank.sql
-- Generic bank/accounting schema

-- Create bank schema
create schema if not exists bank;

-- Grant access to web role
grant usage on schema bank to web;
grant select on all tables in schema bank to web;

-- Grant access to term role
grant all on schema bank to term;
grant all on all tables in schema bank to term;
grant all on all sequences in schema bank to term;

-- Grant access to sysop role
grant all on schema bank to sysop;
grant all on all tables in schema bank to sysop;
grant all on all sequences in schema bank to sysop;

-- Account table - each member can have one account
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

-- Transaction table - ledger of all account activity
create table if not exists bank.__transaction (
    "id" bigserial primary key,
    "accountid" bigint not null constraint fk_transaction_account references bank.__account(id) on delete cascade,
    "amount" numeric(10,0) not null,
    "transactiontype" text not null,  -- 'credit', 'debit', 'transfer_in', 'transfer_out', 'adjustment'
    "description" text,
    "relatedaccountid" bigint,
    "relatedmoniker" citext,
    "membermoniker" citext,  -- who initiated this transaction
    "dateposted" timestamptz default now()
);

create index idx_transaction_account on bank.__transaction(accountid);
create index idx_transaction_date on bank.__transaction(dateposted);

-- Transfer table - pending transfers requiring approval
create table if not exists bank.__transfer (
    "id" bigserial primary key,
    "fromaccountid" bigint not null constraint fk_transfer_from references bank.__account(id) on delete cascade,
    "toaccountid" bigint not null constraint fk_transfer_to references bank.__account(id) on delete cascade,
    "amount" numeric(10,0) not null,
    "status" text default 'pending',  -- 'pending', 'approved', 'rejected', 'cancelled'
    "requestedby" citext,
    "requestedat" timestamptz default now(),
    "respondedby" citext,
    "respondedat" timestamptz
);

create index idx_transfer_status on bank.__transfer(status);
create index idx_transfer_accounts on bank.__transfer(fromaccountid, toaccountid);

-- Views for easy access
create or replace view bank.account as
  select __account.*,
         extract(epoch from created) as createdepoch
  from bank.__account;

create or replace view bank.transaction as
  select __transaction.*,
         extract(epoch from dateposted) as datepostedepoch
  from bank.__transaction;

create or replace view bank.transfer as
  select __transfer.*,
         extract(epoch from requestedat) as requestedatepoch,
         extract(epoch from respondedat) as respondedatepoch
  from bank.__transfer;
