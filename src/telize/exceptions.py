class TelizeError(Exception):
    """Base error for Telize."""


class ConfigError(TelizeError):
    """Invalid or unreadable agent configuration."""


class ExecutionError(TelizeError):
    """Error while executing an agent flow."""
