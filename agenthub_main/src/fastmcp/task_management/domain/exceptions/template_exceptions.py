"""Template Domain Exceptions"""

from __future__ import annotations

from typing import Any


class TemplateError(Exception):
    """Base template exception"""

    def __init__(self, message: str, template_id: str | None = None):
        super().__init__(message)
        self.template_id = template_id


class TemplateNotFoundError(TemplateError):
    """Template not found exception"""

    def __init__(self, template_id: str):
        super().__init__(f"Template not found: {template_id}", template_id)


class TemplateValidationError(TemplateError):
    """Template validation exception"""

    def __init__(
        self,
        message: str,
        template_id: str | None = None,
        validation_errors: list[str] | None = None,
    ):
        super().__init__(message, template_id)
        self.validation_errors = validation_errors or []


class TemplateRenderError(TemplateError):
    """Template rendering exception"""

    def __init__(
        self,
        message: str,
        template_id: str | None = None,
        render_context: dict[str, Any] | None = None,
    ):
        super().__init__(message, template_id)
        self.render_context = render_context or {}


class TemplateCompilationError(TemplateError):
    """Template compilation exception"""

    def __init__(
        self,
        message: str,
        template_id: str | None = None,
        compilation_errors: list[str] | None = None,
    ):
        super().__init__(message, template_id)
        self.compilation_errors = compilation_errors or []


class TemplateVariableError(TemplateError):
    """Template variable exception"""

    def __init__(
        self,
        message: str,
        template_id: str | None = None,
        variable_name: str | None = None,
    ):
        super().__init__(message, template_id)
        self.variable_name = variable_name


class TemplatePermissionError(TemplateError):
    """Template permission exception"""

    def __init__(
        self,
        message: str,
        template_id: str | None = None,
        required_permission: str | None = None,
    ):
        super().__init__(message, template_id)
        self.required_permission = required_permission


class TemplateVersionError(TemplateError):
    """Template version exception"""

    def __init__(
        self, message: str, template_id: str | None = None, version: int | None = None
    ):
        super().__init__(message, template_id)
        self.version = version


class TemplateCacheError(TemplateError):
    """Template cache exception"""

    def __init__(
        self, message: str, template_id: str | None = None, cache_key: str | None = None
    ):
        super().__init__(message, template_id)
        self.cache_key = cache_key


class TemplateCompatibilityError(TemplateError):
    """Template compatibility exception"""

    def __init__(
        self,
        message: str,
        template_id: str | None = None,
        agent_name: str | None = None,
    ):
        super().__init__(message, template_id)
        self.agent_name = agent_name


class TemplateRegistrationError(TemplateError):
    """Template registration exception"""

    def __init__(
        self,
        message: str,
        template_id: str | None = None,
        registration_errors: list[str] | None = None,
    ):
        super().__init__(message, template_id)
        self.registration_errors = registration_errors or []


class TemplateUsageError(TemplateError):
    """Template usage tracking exception"""

    def __init__(
        self,
        message: str,
        template_id: str | None = None,
        usage_data: dict[str, Any] | None = None,
    ):
        super().__init__(message, template_id)
        self.usage_data = usage_data or {}
