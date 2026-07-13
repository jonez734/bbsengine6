create or replace view bank.transaction as
  select __transaction.*,
         extract(epoch from dateposted) as datepostedepoch
  from bank.__transaction;

grant select on bank.transaction to web, term, sysop, member;
