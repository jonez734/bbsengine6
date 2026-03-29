-- Migration: Add UNIQUE INDEX to map_member_flag table
-- Date: 2026-03-28
-- Purpose: Enable UPSERT operations on map_member_flag using INSERT...ON CONFLICT
--
-- The map_member_flag table previously had no UNIQUE constraint or index,
-- which prevented the use of PostgreSQL's INSERT...ON CONFLICT...DO UPDATE syntax.
-- This migration adds a UNIQUE INDEX on (moniker, name) to enable
-- atomic UPSERT operations for flag updates.
--
-- Why UNIQUE INDEX instead of PRIMARY KEY?
-- - map_member_flag is a join table, following the codebase pattern of
--   using UNIQUE indexes on join tables (see map_group_member, map_sigop_sigpath)
-- - No explicit PRIMARY KEY on join tables preserves schema design
-- - UNIQUE INDEX enables INSERT...ON CONFLICT just as effectively
--
-- The constraint is safe to add because:
-- 1. (moniker, name) is semantically unique - each member can only have one value per flag
-- 2. FK constraints on both columns ensure referential integrity
-- 3. If duplicates exist in legacy data, they must be cleaned up first

-- Check if index already exists (idempotent)
DO $$
BEGIN
    -- Try to add the unique index
    -- This will fail silently if it already exists
    IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE tablename = 'map_member_flag'
        AND indexname = 'idx_map_member_flag'
    ) THEN
        -- First, remove any duplicate (moniker, name) pairs if they exist
        DELETE FROM engine.map_member_flag mmf1
        WHERE EXISTS (
            SELECT 1 FROM engine.map_member_flag mmf2
            WHERE mmf1.moniker = mmf2.moniker
            AND mmf1.name = mmf2.name
            AND mmf1.ctid > mmf2.ctid  -- Keep the older row, delete the newer
        );
        
        -- Now add the unique index
        CREATE UNIQUE INDEX idx_map_member_flag ON engine.map_member_flag (moniker, name);
        
        RAISE NOTICE 'Added UNIQUE INDEX idx_map_member_flag on map_member_flag (moniker, name)';
    ELSE
        RAISE NOTICE 'UNIQUE INDEX idx_map_member_flag already exists on map_member_flag';
    END IF;
END $$;
