"""Miscellaneous utility functions."""

from __future__ import annotations

import re
import unicodedata


def sanitise_filename(filename: str) -> str:
    """Remove dangerous characters from a filename."""
    # Normalise unicode
    filename = unicodedata.normalize("NFKD", filename)
    # Remove path separators and null bytes
    filename = re.sub(r'[/\\:\x00]', '_', filename)
    # Collapse whitespace
    filename = re.sub(r'\s+', '_', filename).strip("_.")
    return filename[:255] if filename else "unnamed"


def truncate(text: str, max_length: int = 500) -> str:
    """Truncate text to *max_length* characters with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
