#!/usr/bin/env python3
"""Fix parameter names in git branch test file"""

import re

file_path = '/home/daihungpham/__projects__/agentic-project/4genthub_main/src/tests/unit/task_management/application/services/git_branch_application_service_test.py'

with open(file_path, 'r') as f:
    content = f.read()

# Replace parameter names
content = re.sub(r'\bgit_branch_name\b', 'branch_name', content)
content = re.sub(r'\bgit_branch_description\b', 'description', content)

with open(file_path, 'w') as f:
    f.write(content)

print("Fixed parameter names in test file")