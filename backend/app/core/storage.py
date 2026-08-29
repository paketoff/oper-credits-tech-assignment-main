"""The StorageBackend protocol and its local filesystem implementation.

Uploaded blobs are **not** in the database. They live on the filesystem at
`DATA_DIR/blobs`, and a `Document` row carries only an opaque `storage_key`
pointing at one (ARC-010, DOC-003). The two stores share a volume so neither
survives a restart without the other, and nothing else (DEP-003).

Services depend on the protocol, never on `LocalStorage` (CQ-034). Swapping in
S3 with presigned URLs is a new class and a changed dependency provider, with
no edit to any service.
"""

from pathlib import Path
from typing import Protocol
from uuid import UUID, uuid4

from app.core.errors import StorageError


class StorageBackend(Protocol):
    """Binary blob storage. Narrow on purpose (CQ-033)."""

    async def save(self, application_id: UUID, content: bytes) -> str:
        """Persist content under a generated key and return it."""
        ...

    async def load(self, key: str) -> bytes:
        """Retrieve content by storage key."""
        ...

    async def delete(self, key: str) -> None:
        """Remove content by storage key."""
        ...


class LocalStorage:
    """Blobs on the local filesystem, under one root.

    **The key is generated here, never supplied by a caller.** VAL-023 fixes it
    at `{application_id}/{uuid4}`, and DOC-003 requires it to be opaque: a caller
    that can choose the key can choose a path. The borrower's original filename
    is metadata on the row and never touches the filesystem — it is the
    `../../etc/passwd` row in VAL-020.
    """

    def __init__(self, root: Path) -> None:
        """Anchor the store at a directory.

        Args:
            root: The blob root, usually `DATA_DIR/blobs`.
        """
        self._root = root

    async def save(self, application_id: UUID, content: bytes) -> str:
        """Write a blob and return the key that finds it again.

        Args:
            application_id: Groups a borrower's files under one directory.
            content: The bytes, already validated by magic byte (VAL-022).

        Returns:
            The generated storage key.

        Raises:
            StorageError: STORAGE_UNAVAILABLE if the blob root cannot be
                written — the `/data unwritable` row in VAL-020.
        """
        key = f"{application_id}/{uuid4()}"
        destination = self._root / key
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
        except OSError as exc:
            raise StorageError(code="STORAGE_UNAVAILABLE", detail=str(exc)) from exc
        return key

    async def load(self, key: str) -> bytes:
        """Read a blob back.

        Args:
            key: A key previously returned by `save`.

        Returns:
            The stored bytes.

        Raises:
            StorageError: STORAGE_CORRUPT if a row points at a blob that is not
                on disk. That is a real inconsistency rather than a missing
                file, which is why it is not a 404.
        """
        path = self._resolve(key)
        try:
            return path.read_bytes()
        except FileNotFoundError as exc:
            raise StorageError(code="STORAGE_CORRUPT", detail=key) from exc
        except OSError as exc:
            raise StorageError(code="STORAGE_UNAVAILABLE", detail=str(exc)) from exc

    async def delete(self, key: str) -> None:
        """Remove a blob, tolerating one that is already gone.

        Deletion is idempotent because the caller's transaction may be retried,
        and a second attempt should not fail on a file the first one removed.
        """
        self._resolve(key).unlink(missing_ok=True)

    def _resolve(self, key: str) -> Path:
        """Turn a key into a path, refusing anything that escapes the root.

        Keys are generated, so nothing should ever fail this. It is here anyway:
        a key reaches this method from a database row, and the cost of being
        wrong about that assumption is arbitrary file read.
        """
        candidate = (self._root / key).resolve()
        root = self._root.resolve()
        if not candidate.is_relative_to(root):
            raise StorageError(code="STORAGE_CORRUPT", detail="key escapes the blob root")
        return candidate

    def is_writable(self) -> bool:
        """Whether the blob root can be written, for the readiness probe (DEP-037)."""
        probe = self._root / ".write-probe"
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            probe.write_bytes(b"")
            probe.unlink()
        except OSError:
            return False
        return True
