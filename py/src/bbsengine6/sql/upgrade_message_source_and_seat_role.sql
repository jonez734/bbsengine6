-- Run as the owner of the tables (jam), in zoid6. Review before applying.
-- Adds the message source tag and the named-source registry, and the table role.

BEGIN;

ALTER TABLE engine.__message
    ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'member';
CREATE INDEX IF NOT EXISTS idx_engine_message_source ON engine.__message(source);

CREATE TABLE IF NOT EXISTS engine.__message_source (
    source        text NOT NULL,
    group_prefix  text NOT NULL,
    description   text,
    datecreated   timestamptz DEFAULT now(),
    PRIMARY KEY (source),
    UNIQUE (source, group_prefix)
);
CREATE INDEX IF NOT EXISTS idx_engine_message_source_prefix ON engine.__message_source(group_prefix);

-- Match the sibling engine.__message_group grants (sysop has full access).
GRANT SELECT, INSERT, UPDATE, DELETE ON engine.__message_source TO sysop;

-- Existing seats are players. Role defaults to 'player'; no row is lost.
ALTER TABLE casino.map_cardtable_player
    ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'player';
ALTER TABLE casino.map_cardtable_player
    DROP CONSTRAINT IF EXISTS ck_map_cardtable_player_role;
ALTER TABLE casino.map_cardtable_player
    ADD CONSTRAINT ck_map_cardtable_player_role CHECK (role IN ('player','spectator','dealer'));
CREATE UNIQUE INDEX IF NOT EXISTS uq_map_cardtable_player_member
    ON casino.map_cardtable_player (cardtablemoniker, playermoniker) WHERE playermoniker IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_map_cardtable_player_dealer
    ON casino.map_cardtable_player (cardtablemoniker) WHERE role = 'dealer';

COMMIT;
