import pytest

from app.core.errors import InvalidFileError
from app.services.chunker import split_pages
from app.services.pdf_extractor import PageText, extract_pdf, page_count
from tests.fakes import make_pdf


def test_extract_pdf_keeps_page_numbers(sample_pdf):
    extracted = extract_pdf(sample_pdf)

    assert extracted.page_count == 2
    assert [p.number for p in extracted.pages] == [1, 2]
    assert "Ollama" in extracted.pages[0].text
    assert "ChromaDB" in extracted.pages[1].text
    assert extracted.has_text


def test_extract_pdf_without_text(tmp_path):
    extracted = extract_pdf(make_pdf(tmp_path / "vazio.pdf", [""]))

    assert extracted.page_count == 1
    assert not extracted.has_text


def test_page_count_rejects_corrupted_file(tmp_path):
    broken = tmp_path / "quebrado.pdf"
    broken.write_bytes(b"%PDF-1.7\nisto nao e um pdf")

    with pytest.raises(InvalidFileError):
        page_count(broken)


def test_split_pages_respects_size_and_overlap():
    text = " ".join(f"palavra{i}" for i in range(300))

    chunks = split_pages([PageText(1, text), PageText(2, "Texto curto da segunda página.")], 200, 50)

    assert all(len(c.text) <= 200 for c in chunks)
    assert chunks[-1].page == 2
    assert [c.index for c in chunks] == list(range(len(chunks)))
    first, second = chunks[0].text.split(), chunks[1].text.split()
    assert set(first) & set(second), "trechos vizinhos devem compartilhar texto (sobreposição)"


def test_split_pages_skips_empty_pages_and_normalizes_spaces():
    chunks = split_pages([PageText(1, "   \n\n "), PageText(2, "um    dois\n\n\n\ntrês")], 200, 20)

    assert len(chunks) == 1
    assert chunks[0].page == 2
    assert chunks[0].text == "um dois\n\ntrês"


def test_split_pages_rejects_overlap_bigger_than_chunk():
    with pytest.raises(ValueError):
        split_pages([PageText(1, "x")], 100, 100)
