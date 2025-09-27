"""
ORM compatibility module - provides imports from the actual database models location.
"""

# Import all models from the database models file
from ..database.models import *

# Also create a models submodule reference for compatibility
from ..database import models

__all__ = ['models']