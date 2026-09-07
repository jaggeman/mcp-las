import pytest
from src.chunking.law_chunker import LawChunker

def test_chunker_does_not_split_on_inline_cross_references():
    sample = "7 § Uppsägning från arbetsgivarens sida ska grunda sig på sakliga skäl.\nSakliga skäl föreligger inte om det är skäligt att kräva att arbetsgivaren i stället omplacerar.\nVid bedömningen enligt 7 a § ska särskilt beaktas.\nEnligt 4 a § får avvikelse göras."
    chunks = LawChunker.chunk_statute_text("SFS 1982:80", "LAS", sample)
    assert len(chunks) == 1
    assert chunks[0].section_number == "7"
    assert "7 a §" in chunks[0].content

def test_chunker_correctly_identifies_true_section_boundaries():
    sample = "6 § Avtal om provanställning får träffas.\n\n7 § Uppsägning från arbetsgivaren kräver sakliga skäl."
    chunks = LawChunker.chunk_statute_text("SFS 1982:80", "LAS", sample)
    assert len(chunks) == 2
    assert chunks[0].section_number == "6"
    assert chunks[1].section_number == "7"

def test_chunker_detects_headings_with_mm():
    sample = "Lön under uppsägningstid m.m.\n12 § Arbetstagare har rätt att behålla sin lön."
    chunks = LawChunker.chunk_statute_text("SFS 1982:80", "LAS", sample)
    assert len(chunks) == 1
    assert chunks[0].section_number == "12"
    assert "Lön under uppsägningstid" in (chunks[0].section_title or "")

def test_chunker_strips_transitional_provisions():
    sample = "38 § Arbetsgivare ska betala skadestånd.\n\nÖvergångsbestämmelser\nDenna lag träder i kraft 1983."
    chunks = LawChunker.chunk_statute_text("SFS 1982:80", "LAS", sample)
    assert len(chunks) == 1
    assert chunks[0].section_number == "38"
    assert "Övergångsbestämmelser" not in chunks[0].content
