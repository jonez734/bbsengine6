-- messageview.sql
-- SQL views for unified message system (matching notify view pattern)

-- Core message view - primary work interface
CREATE OR REPLACE VIEW engine.message AS
WITH RECURSIVE all_members AS (
    SELECT moniker FROM engine.__member WHERE approved = TRUE
    UNION ALL
    SELECT gm.member_moniker
    FROM engine.__message_group_member gm
    JOIN engine.__message_group g ON g.id = gm.group_id
    JOIN all_members a ON a.moniker = g.createdby
)

SELECT
    m.id,
    m.channel,
    m.sender_moniker,
    m.content,
    m.data,
    m.urgency,
    m.template,
    m.template_vars,
    m.datestamp,
    m.datestamp AS datecreated,
    timezone(currentmember.tz, m.datestamp) AS datecreatedlocal,
    r.status,
    r.datedelivered,
    timezone(currentmember.tz, r.datedelivered) AS datedeliveredlocal,
    r.dateread,
    timezone(currentmember.tz, r.dateread) AS datereadlocal,
    r.recipient_moniker,
    mt.type_name,
    mt.description AS type_description,
    mt.rate_limit_per_hour,
    mt.requires_approval,
    (
        SELECT mb.blocker_moniker 
        FROM engine.__message_block mb 
        WHERE mb.blocked_moniker = r.recipient_moniker 
        AND mb.blocker_moniker = m.sender_moniker 
        LIMIT 1
    ) AS sender_is_blocked,
    CASE
        WHEN r.status = 'read' THEN TRUE
        WHEN r.status = 'delivered' AND r.datedelivered IS NOT NULL THEN TRUE
        WHEN r.status = 'pending' AND r.datedelivered IS NOT NULL THEN TRUE
        ELSE FALSE
    END AS read_by_user,
    CASE
        WHEN r.status = 'pending' AND m.urgency IN ('URGENT', 'CRITICAL') THEN TRUE
        WHEN r.status = 'delivered' AND m.urgency IN ('URGENT', 'CRITICAL') AND r.dateread IS NOT NULL THEN TRUE
        ELSE FALSE
    END AS urgent,
    CASE
        WHEN m.sender_moniker IS NULL THEN TRUE
        ELSE FALSE
    END AS system_message
FROM engine.__message m
LEFT JOIN engine.__message_recipient r ON r.message_id = m.id
LEFT JOIN engine.__message_type mt ON mt.type_name = m.channel
LEFT JOIN engine.__member currentmember ON currentmember.moniker = r.recipient_moniker
WHERE r.recipient_moniker IN (SELECT moniker FROM all_members)
ORDER BY m.datestamp DESC,
         r.status IN ('delivered', 'read') DESC,
         r.datedelivered DESC;

-- Unread messages view
CREATE OR REPLACE VIEW engine.message_unread AS
WITH RECURSIVE all_members AS (
    SELECT moniker FROM engine.__member WHERE approved = TRUE
    UNION ALL
    SELECT gm.member_moniker
    FROM engine.__message_group_member gm
    JOIN engine.__message_group g ON g.id = gm.group_id
    JOIN all_members a ON a.moniker = g.createdby
)

SELECT *
FROM engine.message
WHERE recipient_moniker IS NOT NULL AND status = 'pending'
AND urgency NOT IN ('URGENT', 'CRITICAL')
ORDER BY datestamp DESC;

-- Urgent messages view
CREATE OR REPLACE VIEW engine.message_urgent AS
WITH RECURSIVE all_members AS (
    SELECT moniker FROM engine.__member WHERE approved = TRUE
    UNION ALL
    SELECT gm.member_moniker
    FROM engine.__message_group_member gm
    JOIN engine.__message_group g ON g.id = gm.group_id
    JOIN all_members a ON a.moniker = g.createdby
)

SELECT *
FROM engine.message
WHERE recipient_moniker IS NOT NULL 
  AND status IN ('pending', 'delivered')
  AND urgency IN ('URGENT', 'CRITICAL')
ORDER BY urgency DESC,
         datestamp DESC;

-- Blocked view (messages from blocked senders)
CREATE OR REPLACE VIEW engine.message_blocked AS
WITH RECURSIVE all_members AS (
    SELECT moniker FROM engine.__member WHERE approved = TRUE
    UNION ALL
    SELECT gm.member_moniker
    FROM engine.__message_group_member gm
    JOIN engine.__message_group g ON g.id = gm.group_id
    JOIN all_members a ON a.moniker = g.createdby
)

SELECT
    m.id,
    m.channel,
    m.sender_moniker,
    m.content,
    m.data,
    m.urgency,
    m.template,
    m.template_vars,
    m.datestamp,
    r.status,
    r.datedelivered,
    r.dateread,
    r.recipient_moniker,
    mb.blocked_moniker,
    timezone(currentmember.tz, m.datestamp) AS datecreatedlocal
FROM engine.__message m
LEFT JOIN engine.__message_recipient r ON r.message_id = m.id
LEFT JOIN engine.__message_block mb ON mb.blocker_moniker = r.recipient_moniker 
                                      AND mb.blocked_moniker = m.sender_moniker
LEFT JOIN engine.__member currentmember ON currentmember.moniker = r.recipient_moniker
WHERE r.recipient_moniker IN (SELECT moniker FROM all_members)
  AND mb.blocker_moniker IS NOT NULL
ORDER BY m.datestamp DESC;

-- Grants
GRANT SELECT ON engine.message TO web, sysop, term;
GRANT SELECT ON engine.message_unread TO web, sysop, term;
GRANT SELECT ON engine.message_urgent TO web, sysop, term;
GRANT SELECT ON engine.message_blocked TO web, sysop, term;
