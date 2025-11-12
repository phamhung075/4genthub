from __future__ import annotations as _annotations

import inspect
from pathlib import Path
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator
from pydantic.fields import FieldInfo, ModelPrivateAttr
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

from fastmcp.utilities.logging import get_logger

logger = get_logger(__name__)

LOG_LEVEL = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

DuplicateBehavior = Literal["warn", "error", "replace", "ignore"]


class ExtendedEnvSettingsSource(EnvSettingsSource):
    """
    A special EnvSettingsSource that allows for multiple env var prefixes to be used.

    Raises a deprecation warning if the old `FASTMCP_SERVER_` prefix is used.
    """

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:
        if prefixes := self.config.get("env_prefixes"):
            for prefix in prefixes:
                self.env_prefix = prefix
                env_val, field_key, value_is_complex = super().get_field_value(
                    field, field_name
                )
                if env_val is not None:
                    if prefix == "FASTMCP_SERVER_":
                        # Deprecated in 2.8.0
                        logger.warning(
                            "Using `FASTMCP_SERVER_` environment variables is deprecated. Use `FASTMCP_` instead.",
                        )
                    return env_val, field_key, value_is_complex

        return super().get_field_value(field, field_name)


class ExtendedSettingsConfigDict(SettingsConfigDict, total=False):
    env_prefixes: list[str] | None


class DynamicDotEnvSettingsSource(DotEnvSettingsSource):
    """
    A DotEnvSettingsSource that respects the instance-level _env_file attribute.
    This allows tests to modify Settings._env_file and have it take effect.
    """

    def __init__(
        self,
        settings_cls: type[BaseSettings],
        env_file: str | Path | None = None,
        env_file_encoding: str | None = None,
        case_sensitive: bool | None = None,
        env_prefix: str | None = None,
        env_nested_delimiter: str | None = None,
    ):
        # Use the current value of _env_file from the class
        # Access via __dict__ to get the raw value
        if "_env_file" in settings_cls.__dict__:
            env_file_raw = settings_cls.__dict__["_env_file"]
            # Unwrap ModelPrivateAttr if needed
            if isinstance(env_file_raw, ModelPrivateAttr):
                env_file = env_file_raw.default if hasattr(env_file_raw, 'default') else None
            else:
                env_file = env_file_raw

        super().__init__(
            settings_cls,
            env_file=env_file,
            env_file_encoding=env_file_encoding,
            case_sensitive=case_sensitive,
            env_prefix=env_prefix,
            env_nested_delimiter=env_nested_delimiter,
        )


class Settings(BaseSettings):
    """FastMCP settings."""

    # Find project root and determine which env file to use
    _project_root = Path(__file__).parent.parent.parent.parent
    _env_dev_path = _project_root / ".env.dev"
    _env_path = _project_root / ".env"

    # Use .env.dev if it exists, otherwise .env
    _env_file = str(_env_dev_path) if _env_dev_path.exists() else str(_env_path)

    # Log which file is being used (only if .env.dev exists)
    if _env_dev_path.exists():
        logger.info("Loading configuration from .env.dev (development mode)")

    # Class-level model_config for Pydantic's internal use
    # Note: env_file is determined dynamically by DynamicDotEnvSettingsSource
    model_config = ExtendedSettingsConfigDict(
        env_prefixes=["FASTMCP_", "FASTMCP_SERVER_"],
        env_file=_env_file,  # Default, overridden by DynamicDotEnvSettingsSource
        extra="ignore",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
    )

    @property
    def effective_env_file(self) -> str:
        """
        Return the actual env_file being used.
        This respects dynamic changes to _env_file for testing.
        """
        return self.__class__._env_file

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        # Use custom sources that respect dynamic env_file and env_prefixes
        # Access _env_file from __dict__ and unwrap if needed
        env_file_raw = settings_cls.__dict__.get("_env_file", None)
        if isinstance(env_file_raw, ModelPrivateAttr):
            env_file_value = env_file_raw.default if hasattr(env_file_raw, 'default') else None
        else:
            env_file_value = env_file_raw

        return (
            init_settings,
            ExtendedEnvSettingsSource(settings_cls),
            DynamicDotEnvSettingsSource(
                settings_cls,
                env_file=env_file_value,
                env_file_encoding=settings_cls.model_config.get("env_file_encoding"),
                case_sensitive=settings_cls.model_config.get("case_sensitive"),
                env_nested_delimiter=settings_cls.model_config.get(
                    "env_nested_delimiter"
                ),
            ),
            file_secret_settings,
        )

    @property
    def settings(self) -> Self:
        """
        This property is for backwards compatibility with FastMCP < 2.8.0,
        which accessed fastmcp.settings.settings
        """
        # Deprecated in 2.8.0
        logger.warning(
            "Using fastmcp.settings.settings is deprecated. Use fastmcp.settings instead.",
        )
        return self

    home: Path = Path.home() / ".fastmcp"

    test_mode: bool = False
    log_level: LOG_LEVEL = "INFO"
    enable_rich_tracebacks: Annotated[
        bool,
        Field(
            description=inspect.cleandoc(
                """
                If True, will use rich tracebacks for logging.
                """
            )
        ),
    ] = True

    deprecation_warnings: Annotated[
        bool,
        Field(
            description=inspect.cleandoc(
                """
                Whether to show deprecation warnings. You can completely reset
                Python's warning behavior by running `warnings.resetwarnings()`.
                Note this will NOT apply to deprecation warnings from the
                settings class itself.
                """,
            )
        ),
    ] = True

    client_raise_first_exceptiongroup_error: Annotated[
        bool,
        Field(
            default=True,
            description=inspect.cleandoc(
                """
                Many MCP components operate in anyio taskgroups, and raise
                ExceptionGroups instead of exceptions. If this setting is True, FastMCP Clients
                will `raise` the first error in any ExceptionGroup instead of raising
                the ExceptionGroup as a whole. This is useful for debugging, but may
                mask other errors.
                """
            ),
        ),
    ] = True

    resource_prefix_format: Annotated[
        Literal["protocol", "path"],
        Field(
            default="path",
            description=inspect.cleandoc(
                """
                When perfixing a resource URI, either use path formatting (resource://prefix/path)
                or protocol formatting (prefix+resource://path). Protocol formatting was the default in FastMCP < 2.4;
                path formatting is current default.
                """
            ),
        ),
    ] = "path"

    tool_attempt_parse_json_args: Annotated[
        bool,
        Field(
            default=False,
            description=inspect.cleandoc(
                """
                Note: this enables a legacy behavior. If True, will attempt to parse
                stringified JSON lists and objects strings in tool arguments before
                passing them to the tool. This is an old behavior that can create
                unexpected type coercion issues, but may be helpful for less powerful
                LLMs that stringify JSON instead of passing actual lists and objects.
                Defaults to False.
                """
            ),
        ),
    ] = False

    client_init_timeout: Annotated[
        float | None,
        Field(
            description="The timeout for the client's initialization handshake, in seconds. Set to None or 0 to disable.",
        ),
    ] = None

    @model_validator(mode="after")
    def setup_logging(self) -> Self:
        """Finalize the settings."""
        from fastmcp.utilities.logging import configure_logging

        configure_logging(
            self.log_level, enable_rich_tracebacks=self.enable_rich_tracebacks
        )

        return self

    # HTTP settings
    host: str = "127.0.0.1"
    port: int = 8000
    sse_path: str = "/sse/"
    message_path: str = "/messages/"
    streamable_http_path: str = "/mcp/"
    debug: bool = False

    # error handling
    mask_error_details: Annotated[
        bool,
        Field(
            default=False,
            description=inspect.cleandoc(
                """
                If True, error details from user-supplied functions (tool, resource, prompt)
                will be masked before being sent to clients. Only error messages from explicitly
                raised ToolError, ResourceError, or PromptError will be included in responses.
                If False (default), all error details will be included in responses, but prefixed
                with appropriate context.
                """
            ),
        ),
    ] = False

    server_dependencies: Annotated[
        list[str],
        Field(
            default_factory=list,
            description="List of dependencies to install in the server environment",
        ),
    ]

    # StreamableHTTP settings
    json_response: bool = False
    stateless_http: bool = (
        False  # If True, uses true stateless mode (new transport per request)
    )

    # Auth settings
    default_auth_provider: Annotated[
        Literal["bearer_env"] | None,
        Field(
            description=inspect.cleandoc(
                """
                Configure the authentication provider. This setting is intended only to
                be used for remote confirugation of providers that fully support
                environment variable configuration.

                If None, no automatic configuration will take place.

                This setting is *always* overriden by any auth provider passed to the
                FastMCP constructor.
                """
            ),
        ),
    ] = None

    include_tags: Annotated[
        set[str] | None,
        Field(
            default=None,
            description=inspect.cleandoc(
                """
                If provided, only components that match these tags will be
                exposed to clients. A component is considered to match if ANY of
                its tags match ANY of the tags in the set.
                """
            ),
        ),
    ] = None
    exclude_tags: Annotated[
        set[str] | None,
        Field(
            default=None,
            description=inspect.cleandoc(
                """
                If provided, components that match these tags will be excluded
                from the server. A component is considered to match if ANY of
                its tags match ANY of the tags in the set.
                """
            ),
        ),
    ] = None

    # Event system settings
    enable_async_event_queue: Annotated[
        bool,
        Field(
            default=False,
            description=inspect.cleandoc(
                """
                Enable async event queue for non-blocking event publishing.
                When enabled, events are queued and processed asynchronously,
                reducing request latency. When disabled, events are processed
                synchronously (backward compatible mode).
                """
            ),
        ),
    ] = False

    event_queue_max_size: Annotated[
        int,
        Field(
            default=10000,
            description=inspect.cleandoc(
                """
                Maximum number of events in queue before backpressure is applied.
                When queue is full, publishing will block briefly or fall back
                to synchronous processing.
                """
            ),
        ),
    ]


settings = Settings()
