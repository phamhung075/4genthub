"""
Base classes for hook system following SOLID principles.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import json
import sys


class HookBase(ABC):
    """Abstract base class for all hooks."""
    
    @abstractmethod
    def execute(self, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute the hook logic."""
        pass
    
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate input data."""
        pass


class ToolHook(HookBase):
    """Base class for tool-related hooks."""
    
    def __init__(self):
        self.validators: List['Validator'] = []
        self.processors: List['Processor'] = []
        self.hints: List['HintProvider'] = []
    
    def add_validator(self, validator: 'Validator') -> None:
        """Add a validator to the hook."""
        self.validators.append(validator)
    
    def add_processor(self, processor: 'Processor') -> None:
        """Add a processor to the hook."""
        self.processors.append(processor)
    
    def add_hint_provider(self, hint_provider: 'HintProvider') -> None:
        """Add a hint provider to the hook."""
        self.hints.append(hint_provider)
    
    def validate(self, data: Dict[str, Any]) -> bool:
        """Run all validators."""
        for validator in self.validators:
            if not validator.validate(data):
                return False
        return True
    
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Run all processors."""
        result = data
        for processor in self.processors:
            result = processor.process(result)
        return result
    
    def get_hints(self, data: Dict[str, Any]) -> List[str]:
        """Collect hints from all providers."""
        all_hints = []
        for provider in self.hints:
            hints = provider.get_hints(data)
            if hints:
                all_hints.extend(hints if isinstance(hints, list) else [hints])
        return all_hints


class Validator(ABC):
    """Abstract base for validators."""
    
    @abstractmethod
    def validate(self, data: Dict[str, Any]) -> bool:
        """Validate data according to specific rules."""
        pass
    
    @abstractmethod
    def get_error_message(self) -> str:
        """Get validation error message."""
        pass


class Processor(ABC):
    """Abstract base for data processors."""
    
    @abstractmethod
    def process(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process and potentially modify data."""
        pass


class HintProvider(ABC):
    """Abstract base for hint providers."""
    
    @abstractmethod
    def get_hints(self, data: Dict[str, Any]) -> Optional[List[str]]:
        """Generate hints based on data."""
        pass