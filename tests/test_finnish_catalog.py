from src.data.finnish_labor_law_catalog import FINNISH_LABOR_LAW_CATALOG


def test_finnish_catalog_contains_core_employment_laws_without_duplicate_act_numbers():
    act_numbers = [item["act_number"] for item in FINNISH_LABOR_LAW_CATALOG]

    assert len(FINNISH_LABOR_LAW_CATALOG) >= 7
    assert len(act_numbers) == len(set(act_numbers))
    assert {"55/2001", "162/2005", "872/2019"}.issubset(act_numbers)
    assert all(item["jurisdiction"] == "FI" for item in FINNISH_LABOR_LAW_CATALOG)
    assert all(item["source"] == "Finlex" and item["source_listing_url"].startswith("https://") for item in FINNISH_LABOR_LAW_CATALOG)
