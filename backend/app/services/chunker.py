import re
from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.services.pdf_extractor import PageText


@dataclass(frozen=True)
class Chunk:
    page: int
    index: int  # posição do trecho no documento
    text: str


def _normalize(text: str) -> str:
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def split_pages(pages: list[PageText], chunk_size: int, chunk_overlap: int) -> list[Chunk]:
    """Divide o texto página a página, para cada trecho saber de qual página veio."""
    if chunk_overlap >= chunk_size:
        raise ValueError("A sobreposição precisa ser menor que o tamanho do trecho.")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks: list[Chunk] = []
    for page in pages:
        text = _normalize(page.text)
        if not text:
            continue
        for piece in splitter.split_text(text):
            if piece.strip():
                chunks.append(Chunk(page=page.number, index=len(chunks), text=piece.strip()))
    return chunks
