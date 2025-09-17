"""
Workflow Hint Enhancer - Modular Architecture Module

This module has been refactored into a modular structure using service pattern.
The module exports the main WorkflowHintEnhancer class for backward compatibility.
"""

from .workflow_hint_enhancer import WorkflowHintEnhancer

__all__ = ['WorkflowHintEnhancer']