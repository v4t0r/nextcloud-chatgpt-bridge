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


@dataclass(slots=True, frozen=True)
class NavigationAppInfo:
    app_id: str
    display_name: str


@dataclass(slots=True, frozen=True)
class SearchProviderInfo:
    provider_id: str
    display_name: str


@dataclass(slots=True, frozen=True)
class SearchResultInfo:
    title: str
    subline: str | None = None
    resource_path: str | None = None


@dataclass(slots=True, frozen=True)
class ShareInfo:
    share_id: str
    share_type: int | None
    item_type: str | None
    path: str | None
    permissions: int | None
    shared_with: str | None
    expiration: str | None
