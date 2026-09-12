from src.data.danish_labor_law_catalog import DANISH_LABOR_LAW_CATALOG


def test_danish_catalog_covers_core_employment_law_domains():
    names = {entry["name"] for entry in DANISH_LABOR_LAW_CATALOG}

    assert len(DANISH_LABOR_LAW_CATALOG) >= 30
    assert "Funktionærloven" in names
    assert "Ferieloven" in names
    assert "Lov om ansættelsesbeviser og visse arbejdsvilkår" in names
    assert any("Virksomhedsoverdragelsesloven" in name for name in names)
    assert "Lov om gennemførelse af dele af arbejdstidsdirektivet (arbejdstidsloven)" in names


def test_catalog_entries_are_explicitly_danish_and_have_source_metadata():
    assert all(entry["jurisdiction"] == "DK" for entry in DANISH_LABOR_LAW_CATALOG)
    assert all(entry["language"] == "da" for entry in DANISH_LABOR_LAW_CATALOG)
    assert all(entry["source"] == "Beskæftigelsesministeriet/Retsinformation" for entry in DANISH_LABOR_LAW_CATALOG)
    assert all(entry["priority"] in {"core", "extended", "specialized"} for entry in DANISH_LABOR_LAW_CATALOG)
