-- Grants that let the bed service role act for members.
-- Run by the owner of engine.pgrole (jam). Idempotent.
--
-- 1. bed reads the member-role tracking table, to find a member's role.
GRANT SELECT ON engine.pgrole TO bed;

-- 2. bed may switch to a member's role for that member's own work.
--    One grant per member served by bed. zoid6's member jam maps to role jam.
GRANT jam TO bed;
