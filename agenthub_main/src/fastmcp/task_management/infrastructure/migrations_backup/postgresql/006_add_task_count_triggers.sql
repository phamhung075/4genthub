-- Migration 006: Add automatic task count synchronization triggers
-- This migration creates database triggers to automatically update
-- task_count and completed_task_count in project_git_branchs table
-- whenever tasks are created, updated, or deleted.

-- Drop existing triggers if they exist (for re-running migration)
DROP TRIGGER IF EXISTS update_branch_task_counts_on_insert ON tasks;
DROP TRIGGER IF EXISTS update_branch_task_counts_on_update ON tasks;
DROP TRIGGER IF EXISTS update_branch_task_counts_on_delete ON tasks;
DROP FUNCTION IF EXISTS update_branch_task_counts();

-- Function to recalculate and update branch task counts
CREATE OR REPLACE FUNCTION update_branch_task_counts()
RETURNS TRIGGER AS $$
DECLARE
    branch_id_to_update UUID;
    total_count INTEGER;
    completed_count INTEGER;
BEGIN
    -- Determine which branch to update based on trigger operation
    IF TG_OP = 'DELETE' THEN
        branch_id_to_update := OLD.git_branch_id;
    ELSE
        branch_id_to_update := NEW.git_branch_id;
    END IF;

    -- Handle UPDATE operations where git_branch_id might change
    IF TG_OP = 'UPDATE' AND OLD.git_branch_id != NEW.git_branch_id THEN
        -- Update counts for both old and new branches

        -- Update old branch
        SELECT COUNT(*),
               COUNT(CASE WHEN status = 'done' THEN 1 END)
        INTO total_count, completed_count
        FROM tasks
        WHERE git_branch_id = OLD.git_branch_id;

        UPDATE project_git_branchs
        SET task_count = total_count,
            completed_task_count = completed_count,
            updated_at = NOW()
        WHERE id = OLD.git_branch_id;

        -- Update new branch
        SELECT COUNT(*),
               COUNT(CASE WHEN status = 'done' THEN 1 END)
        INTO total_count, completed_count
        FROM tasks
        WHERE git_branch_id = NEW.git_branch_id;

        UPDATE project_git_branchs
        SET task_count = total_count,
            completed_task_count = completed_count,
            updated_at = NOW()
        WHERE id = NEW.git_branch_id;

        RETURN NEW;
    END IF;

    -- For INSERT, DELETE, or UPDATE with same branch_id
    -- Calculate actual counts from tasks table
    SELECT COUNT(*),
           COUNT(CASE WHEN status = 'done' THEN 1 END)
    INTO total_count, completed_count
    FROM tasks
    WHERE git_branch_id = branch_id_to_update;

    -- Update the branch counts
    UPDATE project_git_branchs
    SET task_count = total_count,
        completed_task_count = completed_count,
        updated_at = NOW()
    WHERE id = branch_id_to_update;

    -- Return appropriate record based on operation
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- Trigger for INSERT operations
CREATE TRIGGER update_branch_task_counts_on_insert
    AFTER INSERT ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_branch_task_counts();

-- Trigger for UPDATE operations (handles status changes and branch moves)
CREATE TRIGGER update_branch_task_counts_on_update
    AFTER UPDATE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_branch_task_counts();

-- Trigger for DELETE operations
CREATE TRIGGER update_branch_task_counts_on_delete
    AFTER DELETE ON tasks
    FOR EACH ROW
    EXECUTE FUNCTION update_branch_task_counts();

-- Initial synchronization: Fix any existing count discrepancies
DO $$
DECLARE
    branch_record RECORD;
    actual_total INTEGER;
    actual_completed INTEGER;
    fixes_applied INTEGER := 0;
BEGIN
    RAISE NOTICE 'Starting initial task count synchronization...';

    -- Loop through all branches and fix their counts
    FOR branch_record IN
        SELECT id, name, task_count, completed_task_count
        FROM project_git_branchs
    LOOP
        -- Calculate actual counts
        SELECT COUNT(*),
               COUNT(CASE WHEN status = 'done' THEN 1 END)
        INTO actual_total, actual_completed
        FROM tasks
        WHERE git_branch_id = branch_record.id;

        -- Update if counts don't match
        IF actual_total != COALESCE(branch_record.task_count, 0) OR
           actual_completed != COALESCE(branch_record.completed_task_count, 0) THEN

            UPDATE project_git_branchs
            SET task_count = actual_total,
                completed_task_count = actual_completed,
                updated_at = NOW()
            WHERE id = branch_record.id;

            fixes_applied := fixes_applied + 1;

            RAISE NOTICE 'Fixed branch "%" (ID: %): % → % total, % → % completed',
                branch_record.name,
                branch_record.id,
                COALESCE(branch_record.task_count, 0),
                actual_total,
                COALESCE(branch_record.completed_task_count, 0),
                actual_completed;
        END IF;
    END LOOP;

    RAISE NOTICE 'Initial synchronization complete. Fixed % branches.', fixes_applied;
END;
$$;

-- Add comments for documentation
COMMENT ON FUNCTION update_branch_task_counts() IS
'Automatically updates task_count and completed_task_count in project_git_branchs table when tasks are modified';

COMMENT ON TRIGGER update_branch_task_counts_on_insert ON tasks IS
'Automatically updates branch task counts when new tasks are created';

COMMENT ON TRIGGER update_branch_task_counts_on_update ON tasks IS
'Automatically updates branch task counts when tasks are modified or moved between branches';

COMMENT ON TRIGGER update_branch_task_counts_on_delete ON tasks IS
'Automatically updates branch task counts when tasks are deleted';

-- Verify the triggers were created successfully
DO $$
DECLARE
    trigger_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO trigger_count
    FROM information_schema.triggers
    WHERE trigger_name LIKE '%branch_task_counts%';

    RAISE NOTICE 'Migration 006 completed successfully - % triggers installed', trigger_count;
END;
$$;