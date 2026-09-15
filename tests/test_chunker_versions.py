# -*- coding: utf-8 -*-
"""Riksdagen levererar både gällande och framtida lydelse av samma paragraf.

Upptäckt av invarianterna i PR #36, mot Riksdagens API — inte lokalt, eftersom
felet bara finns i den riktiga källtexten:

    2 kap. 6 §: "...annan trosuppfattning. Lag (2023:352).
                 6 § /Träder i kraft I:2028-07-01/ Förbudet i 5 § hindrar
                 inte 1. åtgärder som är ett..."

När en paragraf har en beslutad men ännu inte ikraftträdd ändring skriver
Riksdagen ut den två gånger: den gällande märkt `/Upphör att gälla I:<datum>/`
och den kommande märkt `/Träder i kraft I:<datum>/`. Dubbletthanteringen
hoppar över den andra — men dess text ligger kvar och hamnar inuti den
förstas innehåll.

Det är värre än en trasig chunk. Paragrafen ser komplett ut och innehåller en
regel som inte gäller förrän 2028, utan något som skiljer dem åt. Ett svar
byggt på den texten är fel utan att se fel ut.

Fem paragrafer var drabbade vid mätningen: Diskrimineringslagen 2 kap. 6 §,
Arbetsmiljölagen 1 kap. 4 § och 6 kap. 17 §, Föräldraledighetslagen 5 § och 7 §.
"""

import pytest

from src.chunking.law_chunker import LawChunker


def _chunk(text, statute_id="2008:567", short="DL"):
    return LawChunker.chunk_statute_text(statute_id=statute_id, statute_short=short, full_text=text)


def _by_number(sections):
    return {s.section_number: s for s in sections}


# Förkortad men strukturellt identisk med Riksdagens egen text för
# Diskrimineringslagen 2 kap.
DL_TWO_VERSIONS = """
5 § Den som utan att vara arbetstagare söker eller fullgör praktik ska anses
som arbetstagare. Lag (2023:352).

6 § /Upphör att gälla I:2028-07-01/ Förbudet i 5 § hindrar inte särbehandling
som föranleds av en egenskap som har samband med ålder. Lag (2014:958).

6 § /Träder i kraft I:2028-07-01/ Förbudet i 5 § hindrar inte 1. åtgärder som
är ett led i strävanden att främja jämställdhet.

7 § Den som omfattas av förbudet ska utreda omständigheterna.
"""


def test_the_version_in_force_today_is_the_one_stored():
    sections = _by_number(_chunk(DL_TWO_VERSIONS))
    assert "6" in sections
    sec6 = sections["6"]
    assert "särbehandling" in sec6.content, "den gällande lydelsen ska vara kvar"
    assert "åtgärder som" not in sec6.content, \
        f"2028 års lydelse ligger kvar i den gällande: {sec6.content!r}"


def test_the_marker_itself_never_reaches_the_stored_text():
    """"/Upphör att gälla I:2028-07-01/" är Riksdagens redaktionella märkning.

    Den är inte en del av lagtexten och ska inte citeras som sådan.
    """
    for s in _chunk(DL_TWO_VERSIONS):
        assert "Träder i kraft" not in s.content, f"{s.section_number} §: {s.content[:80]!r}"
        assert "Upphör att gälla" not in s.content, f"{s.section_number} §: {s.content[:80]!r}"
        assert "I:20" not in s.content


def test_the_future_version_does_not_leak_into_the_neighbours_either():
    """Den får inte heller hamna i 5 § eller 7 §, bara för att den klipps bort."""
    sections = _by_number(_chunk(DL_TWO_VERSIONS))
    assert "åtgärder som" not in sections["5"].content
    assert "åtgärder som" not in sections["7"].content
    assert "utreda omständigheterna" in sections["7"].content, \
        "7 § ska vara oskadd"


def test_a_version_whose_date_has_passed_is_the_one_that_applies():
    """Samma struktur, men ikraftträdandet har redan skett.

    Då är det den märkta "Träder i kraft" som gäller, och den gamla — märkt
    "Upphör att gälla" med ett datum som passerat — som ska bort. Regeln är
    "vilken lydelse gäller i dag", inte "ta alltid den första".
    """
    text = """
5 § Den som söker praktik ska anses som arbetstagare.

6 § /Upphör att gälla I:2020-01-01/ Den gamla lydelsen som slutade gälla 2020.

6 § /Träder i kraft I:2020-01-01/ Den lydelse som gäller sedan 2020.

7 § Den som omfattas av förbudet ska utreda omständigheterna.
"""
    sec6 = _by_number(_chunk(text))["6"]
    assert "gäller sedan 2020" in sec6.content
    assert "slutade gälla 2020" not in sec6.content


def test_an_ordinary_statute_without_pending_amendments_is_untouched():
    text = """
5 § Avtal om tidsbegränsad anställning får träffas.

6 § Avtal om provanställning får träffas.

7 § Uppsägning ska grunda sig på sakliga skäl.
"""
    sections = _chunk(text, statute_id="1982:80", short="LAS")
    assert [s.section_number for s in sections] == ["5", "6", "7"]
    assert "provanställning" in _by_number(sections)["6"].content


# ---------------------------------------------------------------------------
# Riksdagen skriver INTE "I:" i båda markeringarna. Den utgående lydelsen är
# märkt med U (upphör), den kommande med I (ikraftträdande):
#
#     /Upphör att gälla U:2028-07-01/
#     /Träder i kraft   I:2028-07-01/
#
# Fixturerna ovan använde "I:" i båda, så testet för att markeringen inte når
# lagtexten passerade utan att pröva det som faktiskt förekommer. Upptäckt
# först när paragraferna lästes ur den fyllda databasen: innehållet i
# Diskrimineringslagen 2 kap. 6 §, Arbetsmiljölagen 6 kap. 17 § och
# Föräldraledighetslagen 5 § börjar med markeringsraden.
# ---------------------------------------------------------------------------

DL_REAL_NOTATION = """
5 § Den som söker praktik ska anses som arbetstagare. Lag (2023:352).

6 § /Upphör att gälla U:2028-07-01/
Förbudet i 5 § hindrar inte särbehandling som föranleds av ålder.
Lag (2014:958).

6 § /Träder i kraft I:2028-07-01/
Förbudet i 5 § hindrar inte åtgärder som främjar jämställdhet.

7 § Den som omfattas av förbudet ska utreda omständigheterna.
"""


def test_the_upphor_marker_uses_U_and_is_stripped_too():
    sec6 = _by_number(_chunk(DL_REAL_NOTATION))["6"]
    assert not sec6.content.lstrip().startswith("/"),         f"markeringsraden står kvar i lagtexten: {sec6.content[:60]!r}"
    assert "Upphör att gälla" not in sec6.content
    assert "U:2028" not in sec6.content
    # Rätt lydelse ska ändå ha valts.
    assert "särbehandling som föranleds av ålder" in sec6.content
    assert "främjar jämställdhet" not in sec6.content


def test_the_outgoing_version_is_recognised_as_such_not_as_unmarked():
    """Skillnaden syns när ikraftträdandet redan passerat.

    Läses "U:" inte alls blir den utgående lydelsen "omarkerad", och faller
    tillbaka på regeln "ta den första" — vilket ger rätt svar före datumet av
    ren tur, och fel svar efter det.
    """
    text = """
5 § Den som söker praktik ska anses som arbetstagare.

6 § /Upphör att gälla U:2020-01-01/
Den gamla lydelsen som slutade gälla 2020.

6 § /Träder i kraft I:2020-01-01/
Den lydelse som gäller sedan 2020.

7 § Den som omfattas av förbudet ska utreda omständigheterna.
"""
    sec6 = _by_number(_chunk(text))["6"]
    assert "gäller sedan 2020" in sec6.content
    assert "slutade gälla 2020" not in sec6.content
