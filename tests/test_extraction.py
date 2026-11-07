"""Tests for document text extraction and file type detection (.pdf and .txt)."""

import io

import pytest
from pypdf import PdfWriter

from ingestion.exceptions import DocumentExtractionError, UnsupportedFileError
from ingestion.extraction import FileType, detect_file_type, extract_text


def test_detect_file_type_supported() -> None:
    assert detect_file_type("document.pdf") == FileType.PDF
    assert detect_file_type("UPPERCASE.PDF") == FileType.PDF
    assert detect_file_type("notes.txt") == FileType.TXT
    assert detect_file_type("data.TXT") == FileType.TXT


def test_detect_file_type_unsupported() -> None:
    with pytest.raises(UnsupportedFileError):
        detect_file_type("spreadsheet.xlsx")
    with pytest.raises(UnsupportedFileError):
        detect_file_type("image.png")


def test_extract_txt_valid_utf8() -> None:
    content = b"Hello, world! This is a test document."
    extracted = extract_text(content, FileType.TXT)
    assert extracted == "Hello, world! This is a test document."


def test_extract_txt_utf8_with_bom() -> None:
    content = "BOM encoded text".encode("utf-8-sig")
    extracted = extract_text(content, FileType.TXT)
    assert extracted == "BOM encoded text"


def test_extract_pdf_valid() -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)

    # Empty page produces empty or whitespace-stripped string
    extracted = extract_text(buf.getvalue(), FileType.PDF)
    assert isinstance(extracted, str)


def test_extract_pdf_corrupt_data() -> None:
    corrupt_bytes = b"%PDF-1.4 completely corrupt content that cannot be parsed"
    with pytest.raises(DocumentExtractionError):
        extract_text(corrupt_bytes, FileType.PDF)
