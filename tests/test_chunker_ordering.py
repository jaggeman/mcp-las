# -*- coding: utf-8 -*-
"""Chunkern får inte hitta på paragrafer — och inte tappa bort riktiga.

Issue #6: flera paragrafer i databasen innehöll fel lagtext, började mitt i en
mening och tillhörde en annan del av lagen. LAS 8 § och 18 § hade 3 % likhet
mot facit. Orsaken är att lagtext är full av korsreferenser, och en referens
som råkar hamna först på en rad ser exakt ut som en paragrafrubrik.

Två invarianter fångar hela felklassen utan att någon behöver känna till
lagens paragrafuppsättning utantill:

* **En paragraf börjar aldrig med gemen bokstav.** Lagtext börjar med versal
  eller siffra. Fortsättningen efter en korsreferens gör det aldrig.
* **Paragrafnumren stiger genom lagen.** En referens till 8 § inne i 25 § går
  baklänges; en äkta rubrik gör det inte.

Den andra invarianten måste tillämpas så att en enstaka falsk träff inte
raderar allt efter sig. Att gå girigt framåt och kasta varje nummer som är
lägre än det senast accepterade skulle göra en falsk "38 §" inne i 4 § till
tyst bortfall av trettio paragrafer — värre än buggen den skulle laga.
"""

import pytest

from src.chunking.law_chunker import LawChunker


def _chunk(text, statute_id="1982:80", short="LAS"):
    return LawChunker.chunk_statute_text(statute_id=statute_id, statute_short=short, full_text=text)


def _by_number(sections):
    return {s.section_number: s for s in sections}


# Radbrytningen före "8 §" är hämtad ur den faktiska texten i LAS 25 § — det
# var precis den som skapade den falska LAS 8 § i databasen.
LAS_LIKE = """
Uppsägning från arbetsgivarens sida

7 § Uppsägning från arbetsgivarens sida ska grunda sig på sakliga skäl.

8 § Uppsägning från arbetsgivarens sida ska vara skriftlig.
I uppsägningsbeskedet ska arbetsgivaren ange vad arbetstagaren ska iaktta.

Företrädesrätt till återanställning

25 § Arbetstagare som har sagts upp på grund av arbetsbrist har företrädesrätt
till återanställning i den verksamhet där de tidigare har varit sysselsatta.
Har besked lämnats enligt
8 § andra stycket eller 16 § andra stycket, kan företrädesrätt inte göras
gällande innan frågan om giltigheten av uppsägningen slutligt har avgjorts.
"""


def test_a_line_broken_cross_reference_does_not_become_a_section():
    sections = _chunk(LAS_LIKE)
    numbers = [s.section_number for s in sections]
    assert numbers == ["7", "8", "25"], f"oväntad paragrafuppsättning: {numbers}"


def test_the_real_section_survives_the_false_one():
    """Det här är skarpare än att bara räkna paragrafer.

    Dubbletthanteringen låter den första träffen vinna, så en falsk 8 § som
    kommer tidigt i texten tränger undan den äkta. Räknar man bara antalet
    ser båda utfallen likadana ut.
    """
    sec8 = _by_number(_chunk(LAS_LIKE))["8"]
    assert "skriftlig" in sec8.content
    assert "andra stycket eller 16 §" not in sec8.content


def test_no_section_starts_mid_sentence():
    """Invarianten som avslöjade felet från början."""
    for s in _chunk(LAS_LIKE):
        first = s.content.lstrip()[:1]
        assert not first.islower(), (
            f"{s.section_number} § börjar med gemen bokstav — "
            f"sannolikt en korsreferens: {s.content[:80]!r}"
        )


def test_an_early_high_reference_does_not_swallow_everything_after_it():
    """Det girigt framåtgående alternativets värsta utfall.

    "38 §" nämns i 4 §. Accepteras den som rubrik, och kastas därefter varje
    lägre nummer, försvinner 5-8 § spårlöst.
    """
    text = """
4 § En anställning gäller tills vidare. Skadestånd enligt
38 § kan komma i fråga.

5 § Avtal om tidsbegränsad anställning får träffas.

6 § Avtal om provanställning får träffas.

7 § Uppsägning ska grunda sig på sakliga skäl.

8 § Uppsägning ska vara skriftlig.
"""
    numbers = [s.section_number for s in _chunk(text)]
    assert numbers == ["4", "5", "6", "7", "8"], f"paragrafer tappades: {numbers}"


def test_letter_suffixed_sections_keep_their_order():
    text = """
6 § Avtal om provanställning får träffas.

6 a § Arbetsgivaren ska lämna skriftlig information om anställningsvillkoren.

6 b § Vid övergång av verksamhet övergår rättigheter och skyldigheter.

7 § Uppsägning ska grunda sig på sakliga skäl.
"""
    numbers = [s.section_number for s in _chunk(text)]
    assert numbers == ["6", "6 a", "6 b", "7"]


def test_transitional_provisions_never_become_sections():
    """LAS 22 § och 6 g § innehöll ikraftträdandepunkter i databasen."""
    text = """
22 § Vid uppsägning på grund av arbetsbrist gäller turordningsregler.

Övergångsbestämmelser

2022:835
1. Denna lag träder i kraft den 30 juni 2022.
4. För anställningar som upphört före ikraftträdandet gäller 22 § i den äldre
lydelsen, om arbetsgivare före den 1 oktober 2022 har sagt upp arbetstagare.
"""
    sections = _chunk(text)
    assert [s.section_number for s in sections] == ["22"]
    assert "träder i kraft" not in sections[0].content
    assert "äldre lydelsen" not in sections[0].content


def test_chapter_numbering_restarts_without_dropping_the_chapter():
    """Flerkapitellagar räknar om från 1 § i varje kapitel.

    Ordningskravet gäller inom ett kapitel, inte tvärs över lagen — annars
    skulle allt utom första kapitlet försvinna.
    """
    text = """
1 kap. Inledande bestämmelser

1 § Denna lag har till ändamål att motverka diskriminering.

2 § Avtal som inskränker rättigheter enligt denna lag är utan verkan.

2 kap. Förbud mot diskriminering

1 § En arbetsgivare får inte diskriminera den som hos arbetsgivaren är
arbetstagare.

2 § Förbudet hindrar inte särbehandling som föranleds av egenskap som har
samband med ålder.
"""
    sections = _chunk(text, statute_id="2008:567", short="DL")
    assert [(s.chapter, s.section_number) for s in sections] == [
        ("1", "1"), ("1", "2"), ("2", "1"), ("2", "2")
    ]


def test_dropped_matches_are_reported_not_silent(caplog):
    """En tyst filtrering är samma sorts fel som den tysta ingestionen i #32.

    Släpper filtret igenom fel saker, eller för mycket, ska det gå att se i
    loggen i stället för att upptäckas som konstiga svar månader senare.
    """
    import logging

    with caplog.at_level(logging.DEBUG, logger="src.chunking.law_chunker"):
        _chunk(LAS_LIKE)
    # getMessage(), inte .message: det senare är mallen med %s kvar i sig.
    messages = [r.getMessage() for r in caplog.records]
    assert any("8 §" in m for m in messages), \
        f"den förkastade korsreferensen loggades inte: {messages}"


# ---------------------------------------------------------------------------
# Fallen som ordlistan missar. Filtret är i dag två handskrivna ordlistor —
# NON_START_PREV_WORDS och INVALID_POST_STARTS — och ordet "ogiltigförklarats"
# står i den senare för att det råkade dyka upp i LAS 18 §. En lista som växer
# med ett ord per upptäckt bugg fångar per definition bara de buggar någon
# redan hittat.
# ---------------------------------------------------------------------------

def test_a_cross_reference_followed_by_an_unlisted_word_is_still_rejected():
    """"vilket" står inte i ordlistan. Lagtext börjar ändå aldrig med gemen."""
    text = """
7 § Uppsägning ska grunda sig på sakliga skäl.

12 § Vid beräkningen av anställningstiden tillämpas
3 § vilket innebär att all tid hos arbetsgivaren räknas.

13 § Arbetstagaren behåller sina anställningsförmåner.
"""
    sections = _chunk(text)
    numbers = [s.section_number for s in sections]
    assert numbers == ["7", "12", "13"], f"påhittad paragraf: {numbers}"

    # 12 § slutade mitt i meningen "…tillämpas" och resten hamnade under en
    # påhittad 3 §. Hela meningen hör till 12 §.
    sec12 = _by_number(sections)["12"]
    assert "all tid hos arbetsgivaren räknas" in sec12.content


def test_a_backwards_reference_does_not_silently_eat_the_rest_of_a_section():
    """Dubbletthanteringen hoppar över träffen — och kastar dess innehåll.

    Den falska 19 §:n i slutet av 20 § får samma doc_id som den äkta, hoppas
    över, och texten efter den försvinner ur lagen utan att någonstans synas.
    """
    text = """
18 § Avskedande får ske om arbetstagaren grovt åsidosatt sina åligganden.

19 § Avskedande ska vara skriftligt.

20 § Vill arbetstagaren göra gällande att ett avskedande är ogiltigt gäller
19 § respektive vad som i övrigt följer av lagen.
"""
    sections = _chunk(text)
    assert [s.section_number for s in sections] == ["18", "19", "20"]
    sec20 = _by_number(sections)["20"]
    assert "vad som i övrigt följer av lagen" in sec20.content, \
        f"texten efter korsreferensen tappades: {sec20.content!r}"


def test_a_reference_with_a_capitalised_continuation_is_caught_by_the_order():
    """Gemen-regeln räcker inte ensam — ordningen fångar resten.

    Radbrytningen kan hamna så att nästa ord är versalt. Då är det numret som
    avslöjar referensen: 15 kommer inte efter 31 i en lag.
    """
    text = """
30 § En arbetsgivare som vill avskeda ska underrätta arbetstagaren.

31 § En arbetsgivare som vill ge besked enligt
15 § Ska underrätta arbetstagaren om detta.
"""
    sections = _chunk(text)
    assert [s.section_number for s in sections] == ["30", "31"]
    assert "Ska underrätta arbetstagaren om detta" in _by_number(sections)["31"].content


# ---------------------------------------------------------------------------
# INVALID_POST_STARTS matchades skiftlägesokänsligt mot fortsättningen, och
# listan innehåller hela ord: 'har ', 'kan ', 'ska ', 'som ', 'och ', 'eller '.
# Svensk lagtext inleder paragrafer med precis de orden, med versal.
#
# Hittat i den fyllda databasen, inte i testerna: LAS 34 § innehöll hela
# 35 § inuti sig, och lookup_statute("LAS", "35") fanns inte alls.
#
# Sedan den generella gemen-regeln finns är ordlistan överflödig för sitt
# syfte — en äkta fortsättning mitt i en mening är gemen och fångas där —
# och aktivt skadlig för allt som börjar med versal.
# ---------------------------------------------------------------------------

def test_a_section_may_begin_with_a_word_from_the_blocklist():
    """LAS 35 § börjar med "Har". Den ska finnas."""
    text = """
34 § Om en arbetstagare sägs upp utan sakliga skäl, ska uppsägningen
förklaras ogiltig på yrkande av arbetstagaren. Lag (2022:835).

35 § Har en arbetstagare blivit avskedad under omständigheter som inte ens
skulle ha räckt till för en giltig uppsägning, ska avskedandet förklaras
ogiltigt. Lag (2022:835).

36 § Ett beslut enligt 34 eller 35 § får verkställas.
"""
    sections = _chunk(text)
    assert [s.section_number for s in sections] == ["34", "35", "36"]

    sec34 = _by_number(sections)["34"]
    assert "35 §" not in sec34.content, \
        f"34 § svalde 35 §: {sec34.content!r}"
    assert "blivit avskedad" in _by_number(sections)["35"].content


@pytest.mark.parametrize("ord_", ["Har", "Kan", "Ska", "Som", "Hade", "Skall"])
def test_every_blocklisted_word_still_works_capitalised(ord_):
    """Hela klassen, inte bara det ord som råkade upptäckas."""
    text = f"""
10 § Första paragrafen med eget innehåll.

11 § {ord_} arbetstagaren rätt till detta gäller vad som följer av lagen.

12 § Tredje paragrafen med eget innehåll.
"""
    numbers = [s.section_number for s in _chunk(text)]
    assert numbers == ["10", "11", "12"], f"{ord_!r} fällde paragrafen: {numbers}"


def test_a_genuine_lowercase_continuation_is_still_rejected():
    """Skyddet får inte försvinna på kuppen — gemen fortsättning är fortfarande en referens."""
    text = """
10 § Första paragrafen.

11 § Bestämmelserna tillämpas på det sätt som anges i
12 § har arbetstagaren rätt till detta gäller vad som följer av lagen.

13 § Tredje paragrafen.
"""
    numbers = [s.section_number for s in _chunk(text)]
    assert "12" not in numbers, f"gemen fortsättning blev en paragraf: {numbers}"


def test_completed_citation_before_real_suffix_section_is_not_rejected():
    """MBL 25 a § får inte sväljas efter ``23 och 24 §§.``."""
    text = """
25 § Avtal saknar verkan som kollektivavtal i den mån det har annat
innehåll än sådant som avses i 23 och 24 §§.

25 a § Ett kollektivavtal som är ogiltigt enligt utländsk rätt är trots
detta giltigt här i landet om stridsåtgärden var tillåten enligt denna lag.
"""
    sections = _chunk(text, statute_id="1976:580", short="MBL")
    assert [s.section_number for s in sections] == ["25", "25 a"]
    assert "Ett kollektivavtal" in _by_number(sections)["25 a"].content


def test_completed_citation_before_real_chapter_section_is_not_rejected():
    """Diskrimineringslagen 4 kap. 15 § får inte sväljas efter 9 och 10 §§."""
    text = """
14 § Vid handläggningen av ett överklagat beslut om vitesföreläggande
tillämpas 9 och 10 §§.

15 § Till en förhandling ska Nämnden mot diskriminering kalla den som har
överklagat beslutet.
"""
    sections = LawChunker.chunk_statute_text(
        statute_id="2008:567", statute_short="DL", full_text=text, default_chapter="4"
    )
    assert [(s.chapter, s.section_number) for s in sections] == [("4", "14"), ("4", "15")]
