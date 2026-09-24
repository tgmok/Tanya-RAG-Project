"""PDF / DOCX -> plain text extraction for uploaded documents.

Kept deliberately simple: extraction only. Classification (which division(s) a
document affects) lives in rag_core.py, as a separate LLM step -- text extraction
here never calls a model, so it can't silently truncate or hallucinate content.
"""
import io


def extract_text(filename: str, file_bytes: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _extract_pdf(file_bytes)
    if lower.endswith(".docx"):
        return _extract_docx(file_bytes)
    if lower.endswith(".md") or lower.endswith(".txt"):
        return file_bytes.decode("utf-8", errors="replace")
    raise ValueError(f"Unsupported file type: {filename} (use .pdf, .docx, .md, or .txt)")


def _extract_pdf(file_bytes: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n\n".join(pages).strip()


def _extract_docx(file_bytes: bytes) -> str:
    import docx
    document = docx.Document(io.BytesIO(file_bytes))
    paragraphs = [p.text for p in document.paragraphs if p.text.strip()]
    return "\n\n".join(paragraphs).strip()
