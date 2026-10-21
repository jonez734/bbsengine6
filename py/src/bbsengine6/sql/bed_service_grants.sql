-- Grants for the bed service role. Run by the owner of engine.pgrole. Idempotent.
--
-- bed reads the member-role tracking table, to find a member's role.
-- bed holds no standing membership in any member role (including jam):
-- it must not act as other roles.
GRANT SELECT ON engine.pgrole TO bed;
