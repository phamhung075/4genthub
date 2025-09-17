"""
Mock for supabase module to allow tests to run without the actual package
"""

class MockClient:
    def __init__(self, *args, **kwargs):
        pass

def create_client(*args, **kwargs):
    return MockClient()

Client = MockClient

# Add to Python path
import sys
import os
sys.modules['supabase'] = sys.modules[__name__]