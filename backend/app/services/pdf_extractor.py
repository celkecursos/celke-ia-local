from dataclasses import dataclass
from pathlib import Path

import pymupdf

from app.core.errors import InvalidFileError


@dataclass(frozen=True)
class PageText:
    number: int  # começa em 1
    text: str


@dataclass(frozen=True)
class ExtractedPdf:
    page_count: int
    pages: list[PageText]

    @property
    def has_text(self) -> bool:
        return any(p.text.strip() for p in self.pages)


def page_count(path: Path) -> int:
    """Abre o PDF só para validar e contar as páginas (rejeita arquivo corrompido ou protegido)."""
    try:
        with pymupdf.open(path, filetype="pdf") as doc:
            if doc.needs_pass:
                raise InvalidFileError("O PDF está protegido por senha e não pode ser lido.")
            return doc.page_count
    except InvalidFileError:
        raise
    except Exception as exc:
        raise InvalidFileError("O arquivo não é um PDF válido ou está corrompido.") from exc


def extract_pdf(path: Path) -> ExtractedPdf:
    """Extrai o texto de cada página, guardando o número da página de origem."""
    try:
        with pymupdf.open(path, filetype="pdf") as doc:
            if doc.needs_pass:
                raise InvalidFileError("O PDF está protegido por senha e não pode ser lido.")
            pages = [PageText(number=i + 1, text=page.get_text("text", sort=True)) for i, page in enumerate(doc)]
            return ExtractedPdf(page_count=doc.page_count, pages=pages)
    except InvalidFileError:
        raise
    except Exception as exc:
        raise InvalidFileError(f"Não foi possível ler o PDF: {exc}") from exc
