--\set web web
--\set bbs term
--\set term term
--\set sysop sysop

\echo ltree
\i ltree.sql
\echo extensions
\i extensions.sql
\echo schema
\i schema.sql
\echo roles
\i roles.sql
\echo buildsiguri
\i buildsiguri.sql
\i member.sql
\i session.sql
\i alert.sql
\echo notify
\i notify.sql
\echo notify_recipient
\i notify_recipient.sql
\echo notify_block
\i notify_block.sql
\echo notify_group
\i notify_group.sql
\echo notify_type
\i notify_type.sql
\echo notify_rate_limit
\i notify_rate_limit.sql
\echo notifyview
\i notifyview.sql
\i sig.sql
\i tag.sql
--\i blurb.sql
\i flag.sql
\i flagdata.sql
--\i tagmap.sql
--\i blurbview.sql

--\i fortune.sql
\echo memberview
\i memberview.sql
\echo memberinet
\i memberinet.sql
--\i subscribe.sql

\echo manage_secondary_role
\i manage_secondary_role.sql
\echo manage_role_privs
\i manage_role_privs.sql
\echo createrol
\i createrol.sql
\echo get_role_privs
\i get_role_privs.sql
\echo checkflag
\i checkflag.sql
\echo getflags
\i getflags.sql
