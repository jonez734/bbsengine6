--\echo notifyview

-- Main notification view joining __notify and __notify_recipient
create or replace view engine.notify as
select
    n.id,
    n.notification_type,
    nr.recipient_moniker,
    n.sender_moniker,
    nr.sessionid,
    n.template,
    n.template_vars,
    n.rendered_message as message,
    n.data,
    n.urgency,
    n.should_persist,
    n.datecreated,
    n.createdbymoniker,
    nr.is_blocked,
    nr.datedelivered as datedelivered,
    nr.dateread as dateread,
    nr.datecreated as recipient_datecreated,
    extract(epoch from n.datecreated) as datecreatedepoch,
    extract(epoch from nr.datedelivered) as datedeliveredepoch,
    extract(epoch from nr.dateread) as datereadepoch,
    timezone(currentmember.tz, n.datecreated) as datecreatedlocal,
    timezone(currentmember.tz, nr.datedelivered) as datedeliveredlocal,
    timezone(currentmember.tz, nr.dateread) as datereadlocal
from engine.__notify n
join engine.__notify_recipient nr on n.id = nr.notify_id
left outer join engine.__member currentmember on (currentmember.loginid = current_user);

-- Unread notifications view
create or replace view engine.notify_unread as
select *
from engine.notify
where dateread is null and is_blocked = false;

-- Urgent unread notifications view
create or replace view engine.notify_urgent as
select *
from engine.notify_unread
where urgency in ('URGENT', 'CRITICAL');

-- Blocked notifications view (audit trail)
create or replace view engine.notify_blocked as
select *
from engine.notify
where is_blocked = true;

-- Grants for views
grant select on engine.notify to web, sysop, term;
grant select on engine.notify_unread to web, sysop, term;
grant select on engine.notify_urgent to web, sysop, term;
grant select on engine.notify_blocked to web, sysop, term;