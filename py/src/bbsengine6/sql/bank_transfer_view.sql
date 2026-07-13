create or replace view bank.transfer as
  select __transfer.*,
         extract(epoch from requestedat) as requestedatepoch,
         extract(epoch from respondedat) as respondedatepoch
  from bank.__transfer;

grant select on bank.transfer to web, term, sysop, member;
