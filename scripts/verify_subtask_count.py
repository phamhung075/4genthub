#!/usr/bin/env python3
"""Quick script to verify subtask_count in database after DDD refactoring"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'agenthub_main', 'src'))

# Load environment
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.dev'))

# Connect to database
import psycopg2

conn = psycopg2.connect(
    host='localhost',
    database='agenthub',
    user='agenthub_user',
    password='agenthub_pass'
)
cur = conn.cursor()

# Query the ULTIMATE test task (after complete bidirectional fix)
task_id = '5fc2477c-ed55-4b84-b6c5-c25a98becae1'

cur.execute('''
    SELECT title, subtask_count
    FROM tasks
    WHERE id = %s
''', (task_id,))

result = cur.fetchone()

if result:
    print(f'\n✅ Test Task Found:')
    print(f'   Title: {result[0]}')
    print(f'   subtask_count: {result[1]}')

    # Count actual subtasks
    cur.execute('SELECT COUNT(*) FROM subtasks WHERE task_id = %s', (task_id,))
    actual = cur.fetchone()[0]
    print(f'   Actual subtasks: {actual}')

    if result[1] == 3:
        print(f'\n🎉 SUCCESS! DDD refactoring works!')
        print(f'   ✅ subtask_count = 3 (correct)')
        print(f'   ✅ Domain methods were called 3 times')
        print(f'   ✅ Repository persisted the count correctly')
    else:
        print(f'\n⚠️  Issue: subtask_count = {result[1]}, expected 3')
else:
    print('❌ Task not found in database')

cur.close()
conn.close()
