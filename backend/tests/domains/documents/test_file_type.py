"""Magic-byte detection. VAL-022: extension and Content-Type are both
client-controlled and neither is trustworthy. Check the bytes.
"""

import pytest

from app.domains.documents.file_type import detect_content_type


@pytest.mark.parametrize(
    ("head", "expected"),
    [
        (b"%PDF-1.7\n%\xe2\xe3\xcf\xd3", "application/pdf"),
        (b"\xff\xd8\xff\xe0\x00\x10JFIF", "image/jpeg"),
        (b"\x89PNG\r\n\x1a\n\x00\x00\x00\r", "image/png"),
    ],
)
def test_detect_content_type_recognises_pdf_jpeg_png(head, expected):
    assert detect_content_type(head) == expected


@pytest.mark.parametrize(
    "head",
    [
        b"plain text, not a document at all",
        b"PK\x03\x04",  # a zip/docx signature — VAL-020's ".docx upload"
        b"",
    ],
)
def test_detect_content_type_rejects_an_unknown_signature(head):
    assert detect_content_type(head) is None


def test_detect_content_type_ignores_the_extension():
    # VAL-020: a .txt renamed to .pdf. The function never sees a filename at
    # all — there is no parameter for one — so this is true by construction,
    # and the test exists to keep that true on purpose.
    plain_text_content = b"just some text, however it was named on disk"

    assert detect_content_type(plain_text_content) is None
