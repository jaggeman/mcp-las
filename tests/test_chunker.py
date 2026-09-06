import pytest
from src.chunking.law_chunker import LawChunker

SAMPLE_LAS_TEXT = """
Lag (1982:80) om anställningsskydd

Allmänna bestämmelser

1 § Denna lag gäller arbetstagare i allmän eller enskild tjänst.
Från lagens tillämpning undantas dock:
1. arbetstagare som med hänsyn till arbetsuppgifter och anställningsvillkor får anses ha företagsledande eller därmed jämförlig ställning,

Uppsägning från arbetsgivarens sida

7 § Uppsägning från arbetsgivarens sida ska vara sakligt grundad.
Sakliga skäl föreligger vid arbetsbrist eller personliga skäl.
En uppsägning är inte sakligt grundad om det är skäligt att kräva att arbetsgivaren bereder arbetstagaren annat arbete hos sig.

7 a § En arbetsgivare som avser att säga upp en arbetstagare på grund av personliga skäl ska underrätta arbetstagaren om detta i förväg.
"""

def test_law_chunker_basic():
    sections = LawChunker.chunk_statute_text(
        statute_id="1982:80",
        statute_short="LAS",
        full_text=SAMPLE_LAS_TEXT
    )
    
    assert len(sections) >= 3
    
    # Check section 1
    sec1 = next((s for s in sections if s.section_number == "1"), None)
    assert sec1 is not None
    assert "företagsledande" in sec1.content
    
    # Check section 7
    sec7 = next((s for s in sections if s.section_number == "7"), None)
    assert sec7 is not None
    assert "sakligt grundad" in sec7.content or "sakliga skäl" in sec7.content.lower()
    assert sec7.section_title == "Uppsägning från arbetsgivarens sida"
    assert "uppsägning" in sec7.keywords
    
    # Check section 7 a
    sec7a = next((s for s in sections if s.section_number == "7 a"), None)
    assert sec7a is not None
    assert "underrätta arbetstagaren" in sec7a.content
