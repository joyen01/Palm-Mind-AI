"""Text extraction for supported upload types (.pdf and .txt)."""

import io
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from ingestion.exceptions import DocumentExtractionError, UnsupportedFileError


class FileType(StrEnum):
    PDF = "pdf"
    TXT = "txt"


SUPPORTED_EXTENSIONS: Mapping[str, FileType] = {
    ".pdf": FileType.PDF,
    ".txt": FileType.TXT,
}


def detect_file_type(filename: str) -> FileType:
    file_type = SUPPORTED_EXTENSIONS.get(Path(filename).suffix.lower())
    if file_type is None:
        raise UnsupportedFileError("Only .pdf and .txt files are supported.")
    return file_type


def extract_text(content: bytes, file_type: FileType) -> str:
    if file_type is FileType.PDF:
        return _extract_pdf(content)
    return _extract_txt(content)


def _extract_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        if reader.is_encrypted:
            raise DocumentExtractionError("Encrypted PDFs are not supported.")
        pages = [page.extract_text() or "" for page in reader.pages]
    except (PdfReadError, ValueError) as exc:
        raise DocumentExtractionError("The PDF file could not be read.") from exc
    return "\n\n".join(page.strip() for page in pages if page.strip())


def _extract_txt(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise DocumentExtractionError("TXT files must be UTF-8 encoded.") from exc
