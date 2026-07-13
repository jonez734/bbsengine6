create or replace view bank.account as
  select __account.*,
         extract(epoch from created) as createdepoch
  from bank.__account;

grant select on bank.account to web, term, sysop, member;
