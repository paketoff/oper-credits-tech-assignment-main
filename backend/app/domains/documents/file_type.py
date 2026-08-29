"""Pure: identifies a file from its leading bytes, never its extension (VAL-022).

Extension and the client-supplied `Content-Type` are both attacker-controlled,
so neither is used for the accept decision. Roughly fifteen lines, and it turns
"we check the extension" into "we check the file" — the difference a fintech
review notices.
"""

_MAGIC: dict[bytes, str] = {
    b"%PDF-": "application/pdf",
    b"\xff\xd8\xff": "image/jpeg",
    b"\x89PNG\r\n\x1a\n": "image/png",
}


def detect_content_type(head: bytes) -> str | None:
    """Identify a file from its leading bytes.

    Args:
        head: The first bytes of the file. Enough to hold the longest
            signature above.

    Returns:
        The detected MIME type, or None if nothing matches — an unrecognised
        signature is not an error at this layer, only a fact for the caller to
        act on (DOC-001, ERR-003).
    """
    for signature, content_type in _MAGIC.items():
        if head.startswith(signature):
            return content_type
    return None
