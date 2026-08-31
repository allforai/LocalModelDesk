"""Transport-neutral carriers for library responses."""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FileSlice:
    """A byte range to stream from a file."""

    path: Path
    start: int
    length: int

    def read(self) -> bytes:
        with open(self.path, "rb") as file:
            file.seek(self.start)
            return file.read(self.length)


@dataclass(frozen=True)
class LibRequest:
    path_params: dict = field(default_factory=dict)
    query: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    body: bytes = b""


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict
    body: object
