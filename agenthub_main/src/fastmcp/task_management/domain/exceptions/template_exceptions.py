"""Template Domain Exceptions"""

from typing import List, Optional, Dict, Any


class TemplateError(Exception):
    """Base template exception"""
    def __init__(self, message: str, template_id: Optional[str] = None):
        super().__init__(message)
        self.template_id = template_id


class TemplateNotFoundError(TemplateError):
    """Template not found exception"""
    def __init__(self, template_id: str):
        super().__init__(f"Template not found: {template_id}", template_id)


class TemplateValidationError(TemplateError):
    """Template validation exception"""
    def __init__(self, message: str, template_id: Optional[str] = None, validation_errors: Optional[List[str]] = None):
        super().__init__(message, template_id)
        self.validation_errors = validation_errors or []


class TemplateRenderError(TemplateError):
    """Template rendering exception"""
    def __init__(self, message: str, template_id: Optional[str] = None, render_context: Optional[Dict[str, Any]] = None):
        super().__init__(message, template_id)
        self.render_context = render_context or {}


class TemplateCompilationError(TemplateError):
    """Template compilation exception"""
    def __init__(self, message: str, template_id: Optional[str] = None, compilation_errors: Optional[List[str]] = None):
        super().__init__(message, template_id)
        self.compilation_errors = compilation_errors or []


class TemplateVariableError(TemplateError):
    """Template variable exception"""
    def __init__(self, message: str, template_id: Optional[str] = None, variable_name: Optional[str] = None):
        super().__init__(message, template_id)
        self.variable_name = variable_name


class TemplatePermissionError(TemplateError):
    """Template permission exception"""
    def __init__(self, message: str, template_id: Optional[str] = None, required_permission: Optional[str] = None):
        super().__init__(message, template_id)
        self.required_permission = required_permission


class TemplateVersionError(TemplateError):
    """Template version exception"""
    def __init__(self, message: str, template_id: Optional[str] = None, version: Optional[int] = None):
        super().__init__(message, template_id)
        self.version = version


class TemplateCacheError(TemplateError):
    """Template cache exception"""
    def __init__(self, message: str, template_id: Optional[str] = None, cache_key: Optional[str] = None):
        super().__init__(message, template_id)
        self.cache_key = cache_key


class TemplateCompatibilityError(TemplateError):
    """Template compatibility exception"""
    def __init__(self, message: str, template_id: Optional[str] = None, agent_name: Optional[str] = None):
        super().__init__(message, template_id)
        self.agent_name = agent_name


class TemplateRegistrationError(TemplateError):
    """Template registration exception"""
    def __init__(self, message: str, template_id: Optional[str] = None, registration_errors: Optional[List[str]] = None):
        super().__init__(message, template_id)
        self.registration_errors = registration_errors or []


class TemplateUsageError(TemplateError):
    """Template usage tracking exception"""
    def __init__(self, message: str, template_id: Optional[str] = None, usage_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, template_id)
        self.usage_data = usage_data or {} 