-- notifyd schema initialization
-- Creates tables for tracking IMAP state and notification history

-- Table: engine.__notify_imap_state
-- Purpose: Track last-seen email UID per server/mailbox to avoid duplicates
-- Ensures we don't send duplicate notifications for the same email
CREATE TABLE IF NOT EXISTS engine.__notify_imap_state (
    id SERIAL PRIMARY KEY,
    server VARCHAR(255) NOT NULL,
    mailbox VARCHAR(255) NOT NULL,
    max_uid INTEGER DEFAULT 0,
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(server, mailbox)
);

CREATE INDEX IF NOT EXISTS idx___notify_imap_state_server
    ON engine.__notify_imap_state(server, mailbox);

-- Table: engine.__notify_history
-- Purpose: Audit log of all notifications sent by notifyd
-- Tracks notification type, recipients, delivery status, and metadata
CREATE TABLE IF NOT EXISTS engine.__notify_history (
    id SERIAL PRIMARY KEY,
    notification_type VARCHAR(255) NOT NULL,
    recipients TEXT[] DEFAULT ARRAY[]::TEXT[],
    datesent TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    notification_id INTEGER,
    data JSONB,
    status VARCHAR(50) DEFAULT 'sent',
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx___notify_history_type
    ON engine.__notify_history(notification_type);

CREATE INDEX IF NOT EXISTS idx___notify_history_datesent
    ON engine.__notify_history(datesent DESC);

CREATE INDEX IF NOT EXISTS idx___notify_history_status
    ON engine.__notify_history(status);
