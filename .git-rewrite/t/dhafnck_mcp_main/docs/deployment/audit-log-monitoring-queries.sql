-- User Data Isolation - Audit Log Monitoring Queries
-- =====================================================
-- Use these queries to monitor the audit logging system
-- Created: 2025-08-19

-- 1. Daily User Activity Summary
-- Shows user access patterns by day
SELECT 
    DATE(timestamp) as access_date,
    user_id,
    entity_type,
    operation,
    COUNT(*) as operation_count
FROM user_access_log
WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY DATE(timestamp), user_id, entity_type, operation
ORDER BY access_date DESC, operation_count DESC;

-- 2. Most Active Users
-- Identify users with highest activity levels
SELECT 
    user_id,
    COUNT(*) as total_operations,
    COUNT(DISTINCT entity_type) as entity_types_accessed,
    COUNT(DISTINCT DATE(timestamp)) as active_days,
    MAX(timestamp) as last_activity
FROM user_access_log
WHERE timestamp >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY user_id
ORDER BY total_operations DESC
LIMIT 20;

-- 3. Suspicious Access Patterns
-- Detect potential security issues
SELECT 
    user_id,
    entity_type,
    operation,
    COUNT(*) as attempt_count,
    MIN(timestamp) as first_attempt,
    MAX(timestamp) as last_attempt
FROM user_access_log
WHERE operation IN ('unauthorized_access', 'access_denied', 'invalid_token')
   OR details LIKE '%error%'
   OR details LIKE '%denied%'
GROUP BY user_id, entity_type, operation
HAVING COUNT(*) > 3
ORDER BY last_attempt DESC;

-- 4. Cross-User Access Attempts
-- Find any attempts to access other users' data
SELECT 
    user_id as accessing_user,
    entity_id,
    entity_type,
    operation,
    timestamp,
    details
FROM user_access_log
WHERE details LIKE '%different user%'
   OR details LIKE '%unauthorized%'
   OR details LIKE '%cross-user%'
ORDER BY timestamp DESC
LIMIT 100;

-- 5. Hourly Activity Distribution
-- Understand usage patterns by hour
SELECT 
    EXTRACT(HOUR FROM timestamp) as hour_of_day,
    COUNT(*) as operation_count,
    COUNT(DISTINCT user_id) as unique_users
FROM user_access_log
WHERE timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY EXTRACT(HOUR FROM timestamp)
ORDER BY hour_of_day;

-- 6. Entity Access Frequency
-- Most frequently accessed entities
SELECT 
    entity_type,
    entity_id,
    COUNT(*) as access_count,
    COUNT(DISTINCT user_id) as unique_users,
    MAX(timestamp) as last_accessed
FROM user_access_log
WHERE entity_id IS NOT NULL
  AND timestamp >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY entity_type, entity_id
ORDER BY access_count DESC
LIMIT 50;

-- 7. Operation Type Distribution
-- Breakdown of operations performed
SELECT 
    operation,
    entity_type,
    COUNT(*) as count,
    COUNT(DISTINCT user_id) as unique_users,
    ROUND(COUNT(*)::numeric / 
          (SELECT COUNT(*) FROM user_access_log WHERE timestamp >= CURRENT_DATE - INTERVAL '1 day')::numeric * 100, 2) 
          as percentage
FROM user_access_log
WHERE timestamp >= CURRENT_DATE - INTERVAL '1 day'
GROUP BY operation, entity_type
ORDER BY count DESC;

-- 8. User Session Analysis
-- Approximate user sessions (operations within 30 minutes)
WITH user_activity AS (
    SELECT 
        user_id,
        timestamp,
        LAG(timestamp) OVER (PARTITION BY user_id ORDER BY timestamp) as prev_timestamp
    FROM user_access_log
    WHERE timestamp >= CURRENT_DATE - INTERVAL '1 day'
)
SELECT 
    user_id,
    COUNT(*) FILTER (WHERE prev_timestamp IS NULL 
                      OR timestamp - prev_timestamp > INTERVAL '30 minutes') as session_count,
    AVG(CASE 
        WHEN prev_timestamp IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (timestamp - prev_timestamp))
        ELSE NULL 
    END) as avg_seconds_between_operations
FROM user_activity
GROUP BY user_id
HAVING COUNT(*) > 10
ORDER BY session_count DESC;

-- 9. Failed Operations Report
-- Track operations that failed
SELECT 
    DATE(timestamp) as date,
    user_id,
    entity_type,
    operation,
    COUNT(*) as failure_count,
    details
FROM user_access_log
WHERE operation LIKE '%fail%'
   OR operation LIKE '%error%'
   OR details LIKE '%exception%'
GROUP BY DATE(timestamp), user_id, entity_type, operation, details
ORDER BY date DESC, failure_count DESC;

-- 10. Audit Log Growth Metrics
-- Monitor audit log table size
SELECT 
    COUNT(*) as total_records,
    MIN(timestamp) as earliest_record,
    MAX(timestamp) as latest_record,
    AGE(MAX(timestamp), MIN(timestamp)) as data_span,
    pg_size_pretty(pg_total_relation_size('user_access_log')) as table_size
FROM user_access_log;

-- 11. Real-time Activity Monitor (last 5 minutes)
SELECT 
    timestamp,
    user_id,
    entity_type,
    entity_id,
    operation,
    details
FROM user_access_log
WHERE timestamp >= NOW() - INTERVAL '5 minutes'
ORDER BY timestamp DESC;

-- 12. Data Isolation Verification
-- Ensure users only access their own data
WITH user_entity_access AS (
    SELECT 
        user_id,
        entity_type,
        entity_id,
        COUNT(*) as access_count
    FROM user_access_log
    WHERE entity_id IS NOT NULL
    GROUP BY user_id, entity_type, entity_id
)
SELECT 
    a1.entity_type,
    a1.entity_id,
    COUNT(DISTINCT a1.user_id) as users_accessing
FROM user_entity_access a1
GROUP BY a1.entity_type, a1.entity_id
HAVING COUNT(DISTINCT a1.user_id) > 1
ORDER BY users_accessing DESC;

-- =====================================================
-- ALERTING QUERIES
-- Run these periodically to detect issues
-- =====================================================

-- Alert: High volume of failures
SELECT 'ALERT: High failure rate detected' as alert_type,
       COUNT(*) as failures_last_hour
FROM user_access_log
WHERE timestamp >= NOW() - INTERVAL '1 hour'
  AND (operation LIKE '%fail%' OR operation LIKE '%error%')
HAVING COUNT(*) > 100;

-- Alert: Potential brute force attempt
SELECT 'ALERT: Potential brute force' as alert_type,
       user_id,
       COUNT(*) as failed_attempts
FROM user_access_log
WHERE timestamp >= NOW() - INTERVAL '10 minutes'
  AND operation IN ('login_failed', 'unauthorized_access')
GROUP BY user_id
HAVING COUNT(*) > 10;

-- Alert: Unusual activity spike
WITH recent_activity AS (
    SELECT COUNT(*) as recent_count
    FROM user_access_log
    WHERE timestamp >= NOW() - INTERVAL '5 minutes'
),
baseline_activity AS (
    SELECT AVG(count) as avg_count
    FROM (
        SELECT COUNT(*) as count
        FROM user_access_log
        WHERE timestamp >= NOW() - INTERVAL '1 day'
        GROUP BY DATE_TRUNC('minute', timestamp)
    ) t
)
SELECT 'ALERT: Activity spike detected' as alert_type,
       r.recent_count,
       b.avg_count as normal_average
FROM recent_activity r, baseline_activity b
WHERE r.recent_count > b.avg_count * 10;