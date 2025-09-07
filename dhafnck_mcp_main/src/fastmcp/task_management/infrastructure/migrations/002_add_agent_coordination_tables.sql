-- Migration: Add Agent Coordination tables
-- Date: 2025-01-13
-- Description: Creates tables for agent coordination, work assignments, handoffs, conflicts, and communications

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS migration_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    migration_name TEXT UNIQUE NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO migration_history (migration_name) 
VALUES ('002_add_agent_coordination_tables');

-- 1. Coordination Requests table
CREATE TABLE IF NOT EXISTS coordination_requests (
    request_id TEXT PRIMARY KEY,
    requesting_agent_id TEXT NOT NULL,
    target_agent_id TEXT,
    coordination_type TEXT NOT NULL,
    priority INTEGER DEFAULT 50,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    request_data TEXT,
    metadata TEXT,
    FOREIGN KEY (requesting_agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (target_agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_coordination_requests_agent ON coordination_requests(target_agent_id);
CREATE INDEX IF NOT EXISTS idx_coordination_requests_type ON coordination_requests(coordination_type);
CREATE INDEX IF NOT EXISTS idx_coordination_requests_created ON coordination_requests(created_at);

-- 2. Work Assignments table
CREATE TABLE IF NOT EXISTS work_assignments (
    assignment_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    assigned_agent_id TEXT NOT NULL,
    assigning_agent_id TEXT,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deadline TIMESTAMP,
    role TEXT,
    priority INTEGER DEFAULT 50,
    capabilities_required TEXT,
    context TEXT,
    metadata TEXT,
    is_completed BOOLEAN DEFAULT FALSE,
    completed_at TIMESTAMP,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
    FOREIGN KEY (assigned_agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (assigning_agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_work_assignments_task ON work_assignments(task_id);
CREATE INDEX IF NOT EXISTS idx_work_assignments_agent ON work_assignments(assigned_agent_id);
CREATE INDEX IF NOT EXISTS idx_work_assignments_deadline ON work_assignments(deadline);
CREATE INDEX IF NOT EXISTS idx_work_assignments_completed ON work_assignments(is_completed);

-- 3. Work Handoffs table
CREATE TABLE IF NOT EXISTS work_handoffs (
    handoff_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    from_agent_id TEXT NOT NULL,
    to_agent_id TEXT NOT NULL,
    initiated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    accepted_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT NOT NULL DEFAULT 'PENDING',
    reason TEXT,
    handoff_data TEXT,
    context TEXT,
    metadata TEXT,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
    FOREIGN KEY (from_agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (to_agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_work_handoffs_task ON work_handoffs(task_id);
CREATE INDEX IF NOT EXISTS idx_work_handoffs_from_agent ON work_handoffs(from_agent_id);
CREATE INDEX IF NOT EXISTS idx_work_handoffs_to_agent ON work_handoffs(to_agent_id);
CREATE INDEX IF NOT EXISTS idx_work_handoffs_status ON work_handoffs(status);
CREATE INDEX IF NOT EXISTS idx_work_handoffs_initiated ON work_handoffs(initiated_at);

-- 4. Conflict Resolutions table
CREATE TABLE IF NOT EXISTS conflict_resolutions (
    conflict_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    conflict_type TEXT NOT NULL,
    detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    resolution_strategy TEXT,
    involved_agents TEXT NOT NULL,
    conflict_details TEXT,
    resolution_details TEXT,
    resolved_by_agent_id TEXT,
    metadata TEXT,
    is_resolved BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (task_id) REFERENCES tasks(task_id),
    FOREIGN KEY (resolved_by_agent_id) REFERENCES agents(agent_id)
);

CREATE INDEX IF NOT EXISTS idx_conflict_resolutions_task ON conflict_resolutions(task_id);
CREATE INDEX IF NOT EXISTS idx_conflict_resolutions_type ON conflict_resolutions(conflict_type);
CREATE INDEX IF NOT EXISTS idx_conflict_resolutions_detected ON conflict_resolutions(detected_at);
CREATE INDEX IF NOT EXISTS idx_conflict_resolutions_resolved ON conflict_resolutions(is_resolved);

-- 5. Agent Communications table
CREATE TABLE IF NOT EXISTS agent_communications (
    message_id TEXT PRIMARY KEY,
    from_agent_id TEXT NOT NULL,
    to_agent_ids TEXT NOT NULL,
    task_id TEXT,
    communication_type TEXT NOT NULL,
    content TEXT NOT NULL,
    priority TEXT DEFAULT 'NORMAL',
    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT,
    FOREIGN KEY (from_agent_id) REFERENCES agents(agent_id),
    FOREIGN KEY (task_id) REFERENCES tasks(task_id)
);

CREATE INDEX IF NOT EXISTS idx_agent_communications_from ON agent_communications(from_agent_id);
CREATE INDEX IF NOT EXISTS idx_agent_communications_task ON agent_communications(task_id);
CREATE INDEX IF NOT EXISTS idx_agent_communications_type ON agent_communications(communication_type);
CREATE INDEX IF NOT EXISTS idx_agent_communications_sent ON agent_communications(sent_at);

-- Create a view for active assignments
CREATE VIEW IF NOT EXISTS active_assignments AS
SELECT 
    wa.*,
    t.title as task_title,
    t.status as task_status,
    a.name as agent_name
FROM work_assignments wa
JOIN tasks t ON wa.task_id = t.task_id
JOIN agents a ON wa.assigned_agent_id = a.agent_id
WHERE wa.is_completed = FALSE
AND (wa.deadline IS NULL OR wa.deadline > CURRENT_TIMESTAMP);

-- Create a view for pending handoffs
CREATE VIEW IF NOT EXISTS pending_handoffs AS
SELECT 
    wh.*,
    t.title as task_title,
    fa.name as from_agent_name,
    ta.name as to_agent_name
FROM work_handoffs wh
JOIN tasks t ON wh.task_id = t.task_id
JOIN agents fa ON wh.from_agent_id = fa.agent_id
JOIN agents ta ON wh.to_agent_id = ta.agent_id
WHERE wh.status = 'PENDING';

INSERT INTO migration_history (migration_name, applied_at) 
VALUES ('002_add_agent_coordination_tables_completed', CURRENT_TIMESTAMP)
ON CONFLICT(migration_name) DO NOTHING;

COMMIT;