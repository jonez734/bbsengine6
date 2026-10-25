-- bank read functions: a member reads only their own balance and transactions.
--
-- A plain grant on bank.account or bank.transaction gives every member every row, because grants
-- are per object, not per row. These SECURITY DEFINER functions check the caller first and return
-- only the rows that caller may see. The views are then no longer granted to member.
--
-- Access: the caller's login role must be a member of the moniker's data role (m_<moniker>), or be
-- sysop or term. Anyone else gets no rows. search_path is pinned so a caller cannot redirect it.
--
-- Installed by checkfunctions as the owner. Idempotent.

create or replace function bank.get_balance(p_moniker citext)
returns table (id bigint, moniker citext, balance numeric)
language plpgsql
security definer
set search_path = bank, engine, public, pg_temp
as $$
begin
    if not (
        pg_has_role(session_user, 'm_' || p_moniker, 'MEMBER')
        or pg_has_role(session_user, 'sysop', 'MEMBER')
        or pg_has_role(session_user, 'term', 'MEMBER')
    ) then
        return;
    end if;
    return query
        select a.id, a.moniker, a.balance
          from bank.__account as a
         where a.moniker = p_moniker;
end
$$;

create or replace function bank.get_transactions(p_moniker citext, p_limit int default 50)
returns table (
    id bigint,
    amount numeric,
    transactiontype text,
    description text,
    relatedmoniker citext,
    dateposted timestamptz
)
language plpgsql
security definer
set search_path = bank, engine, public, pg_temp
as $$
begin
    if not (
        pg_has_role(session_user, 'm_' || p_moniker, 'MEMBER')
        or pg_has_role(session_user, 'sysop', 'MEMBER')
        or pg_has_role(session_user, 'term', 'MEMBER')
    ) then
        return;
    end if;
    return query
        select t.id, t.amount, t.transactiontype, t.description, t.relatedmoniker, t.dateposted
          from bank.__transaction as t
          join bank.__account as a on a.id = t.accountid
         where a.moniker = p_moniker
         order by t.dateposted desc, t.id desc
         limit greatest(p_limit, 0);
end
$$;

alter function bank.get_balance(citext) owner to zoid6;
alter function bank.get_transactions(citext, int) owner to zoid6;

revoke all on function bank.get_balance(citext) from public;
revoke all on function bank.get_transactions(citext, int) from public;

grant execute on function bank.get_balance(citext) to member;
grant execute on function bank.get_transactions(citext, int) to member;

-- Members no longer read the unfiltered views, which expose every account and transaction.
revoke select on bank.account from member;
revoke select on bank.transaction from member;
