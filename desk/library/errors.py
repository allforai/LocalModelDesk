"""Typed exceptions for the library module."""


class LibraryError(Exception):
    """Base error for the library module."""


class NotFoundError(LibraryError):
    """A requested target was not found."""


class ValidationError(LibraryError):
    """Input was invalid and was not persisted."""
