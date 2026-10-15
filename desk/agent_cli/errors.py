"""Exit codes (A-13) and the one exception every command raises to stop."""
from __future__ import annotations

EXIT_OK, EXIT_ERROR, EXIT_USAGE, EXIT_TIMEOUT, EXIT_MEMORY, EXIT_NOT_FOUND, EXIT_SANDBOX = 0, 1, 2, 3, 4, 5, 6


class CliError(Exception):
    def __init__(self, exit_code: int, code: str, message: str, hint: str | None = None):
        super().__init__(message)
        self.exit_code, self.code, self.message, self.hint = exit_code, code, message, hint


class Interrupted(Exception):
    """Raised from the SIGINT/SIGTERM handler; images decides cancel vs. keep-running by signum (A-25)."""
    def __init__(self, signum: int):
        super().__init__(signum)
        self.signum = signum
