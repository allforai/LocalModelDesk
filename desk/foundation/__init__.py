"""Foundation — single source of truth for paths and config.

The sole re-export point of the public API; grows as components land.
"""

from .errors import (
    AdoptConflictError,
    AdoptError,
    ConfigCorruptError,
    FoundationError,
    InsufficientSpaceError,
    LegacyRootError,
    NotWritableError,
)
from .config import DeskConfig, GatewayConfig, default_config, read_config, update_config, write_config
