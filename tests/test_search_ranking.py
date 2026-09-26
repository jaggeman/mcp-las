import pytest
from src.db.firebase_client import FirebaseLaborLawDB, db_client
from src.mcp_tools.tools import search_labor_law


@pytest.fixture(autouse=True)
def _seed_las_7(monkeypatch):
    # Sås oberoende av testordning/andra filers fixtures — annars döljer
    # laddningsordningen (test_mcp_tools.py sås samma statute_id före denna
    # fil alfabetiskt) att testet inte klarar sig ensamt: körd isolerat
    # (`pytest tests/test_search_ranking.py`) misslyckas den annars på ett
    # tomt db_client._local_sections.
    monkeypatch.setattr(db_client, "db", None)
    db_client._local_sections = {}
    db_client._cached_statute_sections_by_country = {}
    db_client.save_statute_section({
        "id": "1982_80_s7",
        "statute_id": "1982:80",
        "statute_short": "LAS",
        "chapter": None,
        "section_number": "7",
        "section_title": "Uppsägning från arbetsgivarens sida",
        "content": "Uppsägning från arbetsgivarens sida ska grundas på sakliga skäl.",
        "raw_text": "7 § Uppsägning från arbetsgivarens sida ska grundas på sakliga skäl.",
        "keywords": ["las", "7 §", "uppsägning", "sakliga skäl"],
    })
    yield
    db_client._local_sections = {}
    db_client._cached_statute_sections_by_country = {}


def test_stemming_swedish_words():
    assert FirebaseLaborLawDB._stem_sv("uppsägningar") == "uppsägn"
    assert FirebaseLaborLawDB._stem_sv("kollektivavtalen") == "kollektivavtal"

def test_search_labor_law_precision():
    results = search_labor_law("Vad krävs för sakliga skäl vid uppsägning?")
    assert len(results) > 0
    top = results[0]
    assert "las" in str(top).lower() or "7" in str(top)


def test_search_labor_law_supports_jurisdiction_filter(monkeypatch):
    monkeypatch.setattr(db_client, "_local_sections", {
        "se-1": {
            "id": "se-1", "statute_short": "LAS", "statute_id": "1982:80",
            "section_number": "7", "content": "sakliga skäl för uppsägning",
            "keywords": ["uppsägning"], "embedding": [], "jurisdiction": "SE",
        },
        "dk-1": {
            "id": "dk-1", "statute_short": "Funktionærloven", "statute_id": "A202400001",
            "section_number": "1", "content": "opsigelse og funktionærer",
            "keywords": ["opsigelse"], "embedding": [], "jurisdiction": "DK",
        },
    })
    monkeypatch.setattr(db_client, "_cached_statute_sections", None)
    monkeypatch.setattr(db_client, "db", None)

    results = search_labor_law("opsigelse", filters={"jurisdiction": "DK"})

    assert results
    assert all(result["jurisdiction"] == "DK" for result in results)


def test_payment_deadline_ranks_semesterlagen_30_first(monkeypatch):
    monkeypatch.setattr(db_client, "_local_sections", {
        "semester-28": {
            "id": "semester-28", "statute_short": "Semesterlagen",
            "statute_id": "1977:480", "section_number": "28", "chapter": None,
            "section_title": "Semesterersättning",
            "content": "När anställningen upphör ska intjänad semesterlön bli semesterersättning.",
            "keywords": ["semesterersättning", "anställningen upphör"],
            "embedding": [], "jurisdiction": "SE",
        },
        "semester-30": {
            "id": "semester-30", "statute_short": "Semesterlagen",
            "statute_id": "1977:480", "section_number": "30", "chapter": None,
            "section_title": "Utbetalning av semesterersättning",
            "content": "Semesterersättning ska betalas ut senast en månad efter anställningens upphörande.",
            "keywords": ["semesterersättning", "betalas ut", "en månad"],
            "embedding": [], "jurisdiction": "SE",
        },
    })
    monkeypatch.setattr(db_client, "_cached_statute_sections", None)
    db_client._cached_statute_sections_by_country = {}

    result = search_labor_law(
        "När ska semesterersättning betalas efter att anställningen upphört?",
        jurisdiction="SE", limit=1,
    )

    assert result[0]["statute"] == "Semesterlagen"
    assert result[0]["section"] == "30"


@pytest.mark.parametrize("country,query,target", [
    ("DK", "Hvor meget ferie har en lønmodtager ret til?", ("Ferieloven", "2", "4")),
    ("FI", "Kuinka pitkä koeaika voi olla?", ("Työsopimuslaki", "1", "4")),
    ("FI", "Kuinka monta vuosilomapäivää työntekijä ansaitsee?", ("Vuosilomalaki", "2", "5")),
    ("NO", "Når kan en arbeidstaker sies opp på grunn av virksomhetens forhold?",
     ("Arbeidsmiljøloven", "15", "15-7")),
    ("NO", "Hvor mange virkedager ferie har en arbeidstaker rett til?", ("Ferieloven", None, "5")),
    ("DE", "Wann ist eine Kündigung sozial ungerechtfertigt?", ("KSchG", None, "1")),
    ("DE", "Wie hoch ist der gesetzliche Mindesturlaub?", ("BUrlG", None, "3")),
    ("ES", "¿Cuál es la duración máxima de la jornada ordinaria?",
     ("Estatuto de los Trabajadores", None, "34")),
    ("ES", "¿Cuántos días de vacaciones anuales corresponden?",
     ("Estatuto de los Trabajadores", None, "38")),
    ("NL", "Wanneer kan een werkgever een arbeidsovereenkomst opzeggen?",
     ("Burgerlijk Wetboek Boek 7 — arbeidsovereenkomst", None, "669")),
    ("NL", "Hoeveel wettelijke vakantiedagen heeft een werknemer?",
     ("Burgerlijk Wetboek Boek 7 — arbeidsovereenkomst", None, "634")),
    ("GB", "What is the right not to be unfairly dismissed?",
     ("Employment Rights Act 1996", "94", "94")),
    ("GB", "What is the basic annual leave entitlement under the Working Time Regulations?",
     ("Working Time Regulations 1998", "13", "13")),
])
def test_country_specific_core_question_ranks_governing_rule_first(
    monkeypatch, country, query, target,
):
    statute, chapter, section = target
    distractor = {
        "id": f"{country}-distractor", "statute_short": "Distractor Act",
        "statute_id": "distractor", "section_number": "999", "chapter": None,
        "section_title": query, "content": f"{query} {query} {query}",
        "keywords": query.lower().split(), "embedding": [], "jurisdiction": country,
    }
    governing = {
        "id": f"{country}-target", "statute_short": statute,
        "statute_id": "BWBR0005290" if country == "NL" else statute,
        "section_number": section, "chapter": chapter,
        "section_title": "Governing provision", "content": "The applicable core rule.",
        "keywords": [], "embedding": [], "jurisdiction": country,
    }
    monkeypatch.setattr(db_client, "_local_sections", {
        distractor["id"]: distractor, governing["id"]: governing,
    })
    db_client._cached_statute_sections_by_country = {}

    result = search_labor_law(query, jurisdiction=country, limit=1)

    assert (result[0]["statute"], result[0]["chapter"], result[0]["section"]) == target
