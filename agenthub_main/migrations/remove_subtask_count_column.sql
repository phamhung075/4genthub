-- Migration: Remove subtask_count column from tasks table
-- Reason: subtask_count is a computed property in the ORM model, not a stored field
-- Date: 2025-11-01
--
-- Background:
-- The Task entity defines subtask_count as a @property that computes the count
-- dynamically from len(self.subtasks). The database should not have this column.
--
-- This migration removes the legacy subtask_count column to align with the ORM model.

-- Remove the subtask_count column
ALTER TABLE tasks DROP COLUMN IF EXISTS subtask_count;
