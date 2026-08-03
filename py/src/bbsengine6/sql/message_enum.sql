-- message_enum.sql
-- Urgency enum used by the unified message system.
-- Extracted from notify.sql to allow message system to be installed
-- without the notify system.

CREATE TYPE engine.notify_urgency_enum AS ENUM (
    'ROUTINE',
    'IMPORTANT',
    'URGENT',
    'CRITICAL'
);

GRANT USAGE ON TYPE engine.notify_urgency_enum TO web, sysop, term;
