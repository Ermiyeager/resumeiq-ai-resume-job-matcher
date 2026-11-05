import io

import pytest

from app.engine.extraction import DocumentError, extract


def _docx_bytes(paragraphs):
    docx = pytest.importorskip("docx")
    doc = docx.Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_valid_docx_upload_extracts_text():
    data = _docx_bytes(["Jordan Reyes", "Experience", "Handled inbound customer calls for national brands."])
    doc = extract("resume.docx", data)
    assert "inbound customer calls" in doc.text
    assert doc.file_type == "docx"


def test_docx_tables_are_flagged_for_ats():
    docx = pytest.importorskip("docx")
    d = docx.Document()
    d.add_paragraph("Skills and experience listed in the table below for the reviewer.")
    t = d.add_table(rows=1, cols=2)
    t.cell(0, 0).text = "Python"
    t.cell(0, 1).text = "Customer support across inbound and outbound calls"
    buf = io.BytesIO()
    d.save(buf)
    doc = extract("resume.docx", buf.getvalue())
    assert doc.layout_signals["tables"] == 1
    assert "Customer support" in doc.text


def test_valid_txt_upload():
    doc = extract("resume.txt", b"Alex Morgan\nSkills\nPython, Java, PostgreSQL, Git and more tools here.")
    assert "PostgreSQL" in doc.text


def test_empty_file_rejected():
    with pytest.raises(DocumentError) as e:
        extract("resume.txt", b"")
    assert e.value.code == "EMPTY_FILE"


def test_empty_document_rejected():
    with pytest.raises(DocumentError) as e:
        extract("resume.txt", b"   \n  ")
    assert e.value.code == "EMPTY_DOCUMENT"


def test_unsupported_file_rejected():
    with pytest.raises(DocumentError) as e:
        extract("resume.exe", b"MZ\x90\x00")
    assert e.value.code == "UNSUPPORTED_TYPE"


def test_file_too_large_rejected():
    with pytest.raises(DocumentError) as e:
        extract("resume.txt", b"a" * (10 * 1024 * 1024 + 1))
    assert e.value.code == "FILE_TOO_LARGE"


def test_disguised_file_rejected():
    """A file named .pdf whose content is not a PDF is rejected before parsing."""
    with pytest.raises(DocumentError) as e:
        extract("resume.pdf", b"<script>alert(1)</script>" * 10)
    assert e.value.code == "TYPE_MISMATCH"


def test_corrupted_docx_rejected():
    with pytest.raises(DocumentError) as e:
        extract("resume.docx", b"PK\x03\x04" + b"\x00garbage" * 50)
    assert e.value.code == "CORRUPTED_FILE"


def test_corrupted_pdf_rejected():
    pytest.importorskip("fitz")
    with pytest.raises(DocumentError) as e:
        extract("resume.pdf", b"%PDF-1.7\n" + b"\x00broken" * 50)
    assert e.value.code == "CORRUPTED_FILE"


def test_valid_pdf_upload_extracts_text():
    fitz = pytest.importorskip("fitz")
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Alex Morgan - Software Developer with Python and Java experience.")
    page.insert_text((72, 100), "Experience: Developed RESTful services using Spring Boot.")
    doc = extract("resume.pdf", pdf.tobytes())
    assert "Spring Boot" in doc.text


def test_scanned_pdf_requests_ocr():
    """An image-only PDF must not be treated as an empty resume."""
    fitz = pytest.importorskip("fitz")
    pdf = fitz.open()
    pdf.new_page()  # a page with no text layer, like a scan
    with pytest.raises(DocumentError) as e:
        extract("scan.pdf", pdf.tobytes())
    assert e.value.code == "OCR_REQUIRED"
