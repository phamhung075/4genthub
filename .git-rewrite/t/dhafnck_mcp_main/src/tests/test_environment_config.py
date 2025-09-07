# Test environment configuration for isolation and cleanup

import os
import tempfile

class IsolatedTestEnvironmentConfig:
    def __init__(self, temp_dir, test_files):
        self.temp_dir = temp_dir
        self.test_files = test_files

def isolated_test_environment(test_id):
    # Setup isolated test environment with temporary files
    class Config:
        def __init__(self):
            self.temp_dir = tempfile.mkdtemp(prefix=f'test_{test_id}_')
            self.test_files = {
                'projects': os.path.join(self.temp_dir, f'{test_id}_projects.test.json'),
                'tasks': os.path.join(self.temp_dir, f'{test_id}_tasks.test.json'),
                'agents': os.path.join(self.temp_dir, f'{test_id}_agents.test.json')
            }
            self.test_projects = {}

        def add_test_project(self, project_id, project_data):
            """
            Add a test project to the environment.
            
            Args:
                project_id (str): The ID of the project.
                project_data (dict): The project data to store.
            """
            # Store projects in a structure that supports both access patterns used by tests:
            # 1) Some tests expect a top-level key named "projects" containing the mapping.
            # 2) Other tests (e.g., production data safety) directly look for the project IDs at
            #    the root level of the JSON object.

            # Update our internal mapping
            self.test_projects[project_id] = project_data

            # Compose combined structure
            combined_data = {
                "projects": self.test_projects,  # nested representation
                **self.test_projects,              # flattened representation
            }

            with open(self.test_files['projects'], 'w') as f:
                import json
                json.dump(combined_data, f, indent=2)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            # Cleanup temporary directory after test
            if os.path.exists(self.temp_dir):
                for file_path in self.test_files.values():
                    if os.path.exists(file_path):
                        os.remove(file_path)
                os.rmdir(self.temp_dir)
    return Config()

def cleanup_test_data_files_only(test_root=None):
    # Function to clean up test data files
    count = 0
    if test_root is None:
        test_root = '/tmp'
    for root, _, files in os.walk(test_root):
        for f in files:
            if is_test_data_file(f):
                file_path = os.path.join(root, f)
                try:
                    os.remove(file_path)
                    count += 1
                except Exception as e:
                    print(f"Error removing {file_path}: {e}")
    return count

def is_test_data_file(filename):
    # Identify test data files by naming convention
    return ".test." in str(filename)
