"""Text extraction from uploaded documents.

PDF  -> PyMuPDF (fitz)
DOCX -> python-docx (paragraphs and table cells)
TXT  -> UTF-8, falling back to Latin-1

Every failure raises DocumentError with a stable machine-readable code so
the API and UI can show a specific message (e.g. offer OCR for scanned PDFs).
"""

from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass, field

MAX_FILE_BYTES = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}
MIN_TEXT_CHARS = 50

_MAGIC = {
    "pdf": b"%PDF",
    "docx": b"PK\x03\x04",
}


class DocumentError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass
class ExtractedDocument:
    text: str
    file_type: str
    page_count: int | None = None
    layout_signals: dict = field(default_factory=dict)


def extension_of(filename: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else ""


def extract(filename: str, data: bytes) -> ExtractedDocument:
    ext = extension_of(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise DocumentError("UNSUPPORTED_TYPE", "Upload a PDF, DOCX or TXT file.")
    if len(data) == 0:
        raise DocumentError("EMPTY_FILE", "The file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise DocumentError("FILE_TOO_LARGE", "The file is larger than 10 MB.")
    magic = _MAGIC.get(ext)
    if magic and not data.startswith(magic):
        raise DocumentError("TYPE_MISMATCH", f"The file content is not a valid {ext.upper()} file.")

    if ext == "pdf":
        doc = _extract_pdf(data)
    elif ext == "docx":
        doc = _extract_docx(data)
    else:
        doc = _extract_txt(data)

    if len(doc.text.strip()) < MIN_TEXT_CHARS:
        if ext == "pdf":
            raise DocumentError(
                "OCR_REQUIRED",
                "No readable text was found. This PDF looks scanned or image-based; "
                "OCR processing is needed to read it.",
            )
        raise DocumentError("EMPTY_DOCUMENT", "The document contains no readable text.")
    return doc


def _extract_pdf(data: bytes) -> ExtractedDocument:
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:  # pragma: no cover - depends on install
        raise DocumentError("PDF_UNAVAILABLE", "PDF support is not installed on the server.") from exc
    try:
        pdf = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise DocumentError("CORRUPTED_FILE", "The PDF could not be opened. It may be damaged.") from exc
    if pdf.needs_pass:
        raise DocumentError("PASSWORD_PROTECTED", "The PDF is password-protected. Remove the password and try again.")

    pages_text: list[str] = []
    image_count = 0
    multi_column_pages = 0
    for page in pdf:
        pages_text.append(page.get_text("text", sort=True))
        image_count += len(page.get_images(full=False))
        # Rough multi-column signal: text blocks starting in both page halves
        # on the same vertical band.
        blocks = [b for b in page.get_text("blocks") if b[4].strip()]
        mid = page.rect.width / 2
        left = [b for b in blocks if b[2] < mid]
        right = [b for b in blocks if b[0] > mid]
        if left and right and min(len(left), len(right)) >= 3:
            multi_column_pages += 1
    signals = {
        "images": image_count,
        "multi_column_pages": multi_column_pages,
        "page_count": pdf.page_count,
    }
    return ExtractedDocument("\n".join(pages_text), "pdf", pdf.page_count, signals)


def _extract_docx(data: bytes) -> ExtractedDocument:
    try:
        import docx  # python-docx
    except ImportError as exc:  # pragma: no cover
        raise DocumentError("DOCX_UNAVAILABLE", "DOCX support is not installed on the server.") from exc
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
        body_xml = archive.read("word/document.xml")
        document = docx.Document(io.BytesIO(data))
    except Exception as exc:
        raise DocumentError("CORRUPTED_FILE", "The DOCX file could not be opened. It may be damaged.") from exc

    parts = [p.text for p in document.paragraphs]
    table_cells = 0
    for table in document.tables:
        for row in table.rows:
            cells = []
            for cell in row.cells:
                table_cells += 1
                if cell.text.strip() and cell.text not in cells:
                    cells.append(cell.text)
            parts.extend(cells)
    # Text boxes are not part of document.paragraphs; pull their text out too.
    from docx.oxml.ns import qn

    for box in document.element.body.iter(qn("w:txbxContent")):
        for para in box.iter(qn("w:p")):
            box_text = "".join(t.text or "" for t in para.iter(qn("w:t")))
            if box_text.strip():
                parts.append(box_text)
    header_footer_text = 0
    for section in document.sections:
        for part in (section.header, section.footer):
            header_footer_text += sum(len(p.text.strip()) for p in part.paragraphs)
    text_boxes = body_xml.count(b"<w:txbxContent")
    signals = {
        "tables": len(document.tables),
        "table_cells": table_cells,
        "header_footer_chars": header_footer_text,
        "text_boxes": text_boxes,
        "images": len(document.inline_shapes),
    }
    return ExtractedDocument("\n".join(parts), "docx", None, signals)


def _extract_txt(data: bytes) -> ExtractedDocument:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
    if "\x00" in text:
        raise DocumentError("TYPE_MISMATCH", "The file is not a plain text document.")
    return ExtractedDocument(text, "txt")
