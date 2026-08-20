from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class FileInfo:
    """Normalized file/folder metadata returned by storage providers."""

    path: str
    name: str
    is_dir: bool
    size: int | None = None
    content_type: str | None = None
    etag: str | None = None
    last_modified: str | None = None
