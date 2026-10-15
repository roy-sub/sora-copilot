"""Evidence and dossier files.

Two implementations behind one interface, mirroring the repository:

* ``SupabaseStorage`` — the ``evidence`` and ``dossiers`` buckets, private, with
  short-lived signed URLs (15 minutes, per the build spec).
* ``MemoryStorage`` — bytes held in the process, so uploading evidence and downloading a
  dossier work end to end with no account and no keys. Not durable, and it says so.

Nothing here is a cache. A dossier is a record of what was submitted, so it is stored
whole rather than regenerated on demand: regenerating it against a newer rulebase would
silently produce a different document under the same version number.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import uuid4

EVIDENCE_BUCKET = "evidence"
DOSSIER_BUCKET = "dossiers"

#: Build spec §8. Long enough to click, short enough not to be a shareable link.
SIGNED_URL_TTL_SECONDS = 15 * 60

#: Design §EvidenceUploader: 40 MB, and these formats only.
MAX_EVIDENCE_BYTES = 40 * 1024 * 1024
ALLOWED_EVIDENCE_TYPES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/msword": ".doc",
    "application/vnd.ms-excel": ".xls",
    "image/png": ".png",
    "image/jpeg": ".jpg",
}

DOCX_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class StorageError(RuntimeError):
    """The file could not be stored or read."""


class RejectedFile(StorageError):
    """The file is not acceptable. ``reason`` is written for the operator."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True, slots=True)
class StoredFile:
    path: str
    bytes: int
    content_type: str


class Storage(Protocol):
    def put(self, bucket: str, path: str, data: bytes, content_type: str) -> StoredFile: ...
    def get(self, bucket: str, path: str) -> bytes: ...
    def signed_url(self, bucket: str, path: str) -> str | None: ...
    def delete(self, bucket: str, path: str) -> None: ...

    @property
    def is_durable(self) -> bool: ...


def validate_evidence(filename: str, size: int, content_type: str | None) -> str:
    """Check a file before it is stored, and return the content type to record.

    Refusing here rather than on read means the operator learns immediately, while they
    still have the file to hand.
    """
    if size <= 0:
        raise RejectedFile("The file is empty.")
    if size > MAX_EVIDENCE_BYTES:
        mb = MAX_EVIDENCE_BYTES // (1024 * 1024)
        raise RejectedFile(f"The file is larger than {mb} MB.")

    resolved = (content_type or "").split(";")[0].strip().lower()
    if resolved in ALLOWED_EVIDENCE_TYPES:
        return resolved

    # Fall back to the extension: browsers do not always send a type for .docx.
    lower = filename.lower()
    for mime, extension in ALLOWED_EVIDENCE_TYPES.items():
        if lower.endswith(extension):
            return mime
    allowed = ", ".join(sorted({e.lstrip(".").upper() for e in ALLOWED_EVIDENCE_TYPES.values()}))
    raise RejectedFile(f"That file type is not accepted. Allowed: {allowed}.")


def evidence_path(operation_id: str, oso_id: str | None, filename: str) -> str:
    safe = "".join(c for c in filename if c.isalnum() or c in "._- ").strip() or "evidence"
    folder = (oso_id or "general").replace("#", "").replace("/", "-")
    return f"{operation_id}/{folder}/{uuid4().hex[:8]}-{safe}"


def dossier_path(operation_id: str, version: int, fmt: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"{operation_id}/sora-dossier-v{version}-{stamp}.{fmt}"


class MemoryStorage:
    """Bytes in the process. Works with no keys; lost when the process stops."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._files: dict[tuple[str, str], tuple[bytes, str]] = {}

    @property
    def is_durable(self) -> bool:
        return False

    def put(self, bucket: str, path: str, data: bytes, content_type: str) -> StoredFile:
        with self._lock:
            self._files[(bucket, path)] = (data, content_type)
        return StoredFile(path=path, bytes=len(data), content_type=content_type)

    def get(self, bucket: str, path: str) -> bytes:
        with self._lock:
            entry = self._files.get((bucket, path))
        if entry is None:
            raise StorageError(f"{bucket}/{path} is not stored in this process any more")
        return entry[0]

    def signed_url(self, bucket: str, path: str) -> str | None:
        # No object store, so there is no URL to sign. The API streams the bytes instead,
        # and says so rather than handing back a link that would not work.
        return None

    def delete(self, bucket: str, path: str) -> None:
        with self._lock:
            self._files.pop((bucket, path), None)


class SupabaseStorage:
    """Private buckets with short-lived signed URLs."""

    @property
    def is_durable(self) -> bool:
        return True

    def _bucket(self, bucket: str) -> object:
        from app.db.client import get_client

        return get_client().storage.from_(bucket)

    def put(self, bucket: str, path: str, data: bytes, content_type: str) -> StoredFile:
        try:
            self._bucket(bucket).upload(  # type: ignore[attr-defined]
                path=path,
                file=data,
                file_options={"content-type": content_type, "upsert": "true"},
            )
        except Exception as exc:
            raise StorageError(f"could not store {bucket}/{path}: {exc}") from exc
        return StoredFile(path=path, bytes=len(data), content_type=content_type)

    def get(self, bucket: str, path: str) -> bytes:
        try:
            return bytes(self._bucket(bucket).download(path))  # type: ignore[attr-defined]
        except Exception as exc:
            raise StorageError(f"could not read {bucket}/{path}: {exc}") from exc

    def signed_url(self, bucket: str, path: str) -> str | None:
        try:
            result = self._bucket(bucket).create_signed_url(path, SIGNED_URL_TTL_SECONDS)  # type: ignore[attr-defined]
        except Exception as exc:
            raise StorageError(f"could not sign {bucket}/{path}: {exc}") from exc
        if isinstance(result, dict):
            return result.get("signedURL") or result.get("signed_url")
        return None

    def delete(self, bucket: str, path: str) -> None:
        try:
            self._bucket(bucket).remove([path])  # type: ignore[attr-defined]
        except Exception as exc:
            raise StorageError(f"could not delete {bucket}/{path}: {exc}") from exc


_memory = MemoryStorage()


def get_storage() -> Storage:
    """Supabase Storage when configured; the in-process store otherwise.

    The in-process store is a module singleton rather than per-request, so an evidence
    file uploaded in one request is readable in the next.
    """
    from app.config import get_settings

    if get_settings().supabase_configured:
        return SupabaseStorage()
    return _memory


def reset_storage() -> None:
    """Drop the in-process files. Used by the tests."""
    global _memory
    _memory = MemoryStorage()
