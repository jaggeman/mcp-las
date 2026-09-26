"""The country registry is the single source of truth for all runtime consumers."""


def test_registry_drives_supported_languages_and_smoke_queries():
    from scripts.production_smoke import SMOKE_QUERIES
    from src.jurisdictions import JURISDICTION_CODES, JURISDICTION_LANGUAGES, JURISDICTIONS
    from src.mcp_tools.tools import SUPPORTED_JURISDICTIONS

    assert JURISDICTION_CODES == ("SE", "DK", "FI", "NO", "DE", "ES", "NL", "GB")
    assert SUPPORTED_JURISDICTIONS == JURISDICTION_LANGUAGES
    assert SMOKE_QUERIES == {code: details["smoke_query"] for code, details in JURISDICTIONS.items()}


def test_usage_logging_accepts_every_registered_country():
    from src.jurisdictions import JURISDICTION_CODES
    from src.services.usage_logging import country

    for code in JURISDICTION_CODES:
        assert country("search_labor_law", {"jurisdiction": code}) == code


def test_registry_preserves_country_specific_capabilities():
    from src.jurisdictions import JURISDICTIONS

    assert JURISDICTIONS["SE"]["case_law"] == "Arbetsdomstolen"
    assert JURISDICTIONS["SE"]["calculators"] == ["notice_period", "vacation", "turnorder", "travel"]
    assert all(not details["hr_templates"] for code, details in JURISDICTIONS.items() if code != "SE")
