"""File parsing service — extracts plain text from .txt, .doc/.docx, .pdf."""

from __future__ import annotations

import io
import logging

logger = logging.getLogger("mediextract.services.file")


class FileService:
    """Stateless service for extracting text from uploaded documents."""

    def extract_text(self, content: bytes, extension: str) -> str:
        """Dispatch to the correct parser based on file extension."""
        ext = extension.lower().lstrip(".")
        match ext:
            case "txt":
                return self._parse_txt(content)
            case "pdf":
                return self._parse_pdf(content)
            case "doc" | "docx":
                return self._parse_docx(content)
            case _:
                raise ValueError(f"Unsupported extension: .{ext}")

    # ── Parsers ──

    @staticmethod
    def _parse_txt(content: bytes) -> str:
        """Plain text — decode with fallback."""
        for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                return content.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        return content.decode("utf-8", errors="replace")

    @staticmethod
    def _parse_pdf(content: bytes) -> str:
        """Extract text from PDF using pdfplumber (fallback to PyMuPDF)."""
        try:
            import pdfplumber
            text_parts: list[str] = []
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            if text_parts:
                return "\n\n".join(text_parts)
        except Exception:
            logger.debug("pdfplumber failed, falling back to PyMuPDF")

        # Fallback: PyMuPDF
        import fitz  # pymupdf
        doc = fitz.open(stream=content, filetype="pdf")
        pages = [page.get_text() for page in doc]
        doc.close()
        return "\n\n".join(pages)

    @staticmethod
    def _parse_docx(content: bytes) -> str:
        """Extract text from .doc/.docx using python-docx."""
        from docx import Document

        doc = Document(io.BytesIO(content))
        return "\n".join(para.text for para in doc.paragraphs if para.text.strip())
