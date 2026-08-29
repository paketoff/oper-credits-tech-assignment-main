"""Blobs on disk, under keys nobody outside this module chooses. VAL-023, DOC-003."""

from uuid import uuid4

import pytest

from app.core.errors import StorageError
from app.core.storage import LocalStorage

_APPLICATION = uuid4()


@pytest.fixture
def storage(tmp_path) -> LocalStorage:
    return LocalStorage(tmp_path / "blobs")


async def test_save_returns_generated_key(storage):
    # VAL-023: {application_id}/{uuid4}. The caller does not pass a key and
    # cannot, which is what keeps a client-controlled string off the filesystem.
    key = await storage.save(_APPLICATION, b"%PDF-1.7 ...")

    prefix, _, suffix = key.partition("/")
    assert prefix == str(_APPLICATION)
    assert suffix


async def test_two_saves_never_collide(storage):
    first = await storage.save(_APPLICATION, b"a")
    second = await storage.save(_APPLICATION, b"b")

    assert first != second
    assert await storage.load(first) == b"a"


async def test_load_roundtrips_content(storage):
    content = b"\x89PNG\r\n\x1a\n" + b"payload"

    key = await storage.save(_APPLICATION, content)

    assert await storage.load(key) == content


async def test_path_traversal_filename_cannot_escape_blob_root(storage, tmp_path):
    # VAL-020: `../../etc/passwd`. Keys are generated so this should be
    # unreachable, but a key arrives here from a database row and the cost of
    # being wrong about that is arbitrary file read.
    outside = tmp_path / "secret.txt"
    outside.write_bytes(b"not yours")

    with pytest.raises(StorageError) as exc:
        await storage.load("../secret.txt")

    assert exc.value.code == "STORAGE_CORRUPT"


async def test_missing_key_raises_domain_error(storage):
    # A row pointing at a blob that is not on disk is an inconsistency, not a
    # missing page — which is why it is STORAGE_CORRUPT and not a 404.
    with pytest.raises(StorageError) as exc:
        await storage.load(f"{_APPLICATION}/{uuid4()}")

    assert exc.value.code == "STORAGE_CORRUPT"


async def test_delete_is_idempotent(storage):
    key = await storage.save(_APPLICATION, b"gone soon")

    await storage.delete(key)
    await storage.delete(key)

    with pytest.raises(StorageError):
        await storage.load(key)


async def test_the_original_filename_never_reaches_a_path(storage):
    # DOC-003, VAL-023. The borrower's filename is metadata on the row; the
    # bytes land under a generated key that carries no trace of it.
    key = await storage.save(_APPLICATION, b"payload")

    assert "loonfiche" not in key
    assert ".pdf" not in key
