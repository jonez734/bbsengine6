--\echo __notify

-- IMAP state tracking for notifyd daemon
CREATE TABLE IF NOT EXISTS engine.__notify_imap_state (
    id SERIAL PRIMARY KEY,
    server VARCHAR(255) NOT NULL,
    mailbox VARCHAR(255) NOT NULL,
    max_uid INTEGER DEFAULT 0,
    last_checked TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dateupdated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(server, mailbox)
);

CREATE INDEX IF NOT EXISTS idx___notify_imap_state_server
    ON engine.__notify_imap_state(server, mailbox);

-- Notification history audit log for notifyd daemon
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

-- Grants
GRANT ALL ON engine.__notify_imap_state TO web, sysop, term;
GRANT ALL ON engine.__notify_imap_state_id_seq TO web, sysop, term;
GRANT ALL ON engine.__notify_history TO web, sysop, term;
GRANT ALL ON engine.__notify_history_id_seq TO web, sysop, term;