"""Best-effort text extraction from uploaded reference documents."""
import io


def extract_text(filename: str, data: bytes) -> str:
    name = (filename or "").lower()
    try:
        if name.endswith(".pdf"):
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            return "\n".join((page.extract_text() or "") for page in reader.pages)
        if name.endswith(".docx"):
            import docx
            document = docx.Document(io.BytesIO(data))
            return "\n".join(p.text for p in document.paragraphs)
        if name.endswith((".txt", ".md", ".eml", ".csv")):
            return data.decode("utf-8", errors="ignore")
    except Exception as e:
        return f"[Could not extract text from {filename}: {e}]"
    return f"[Unsupported file type for text extraction: {filename}. Content was stored but not parsed.]"
