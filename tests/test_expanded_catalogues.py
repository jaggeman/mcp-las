from src.scrapers.european_labor_fetcher import GERMAN_LAWS, NORWEGIAN_LAWS
from src.scrapers.boe_fetcher import SPANISH_LAWS


def test_new_catalogue_entries_and_unique_identifiers():
    from src.services.sync_service import DEFAULT_STATUTES
    assert '1970:215' in DEFAULT_STATUTES
    assert {'MuSchG', 'BEEG', 'NachwG'} <= {name for _, name in GERMAN_LAWS}
    assert {'1988-05-06-22', '1973-12-14-61', '1989-06-16-65'} <= dict(NORWEGIAN_LAWS).keys()
    assert {'BOE-A-2023-5365', 'BOE-A-2015-8168'} <= dict(SPANISH_LAWS).keys()
    for catalogue in (GERMAN_LAWS, NORWEGIAN_LAWS, SPANISH_LAWS):
        assert len(dict(catalogue)) == len(catalogue)


def test_coverage_catalogue_counts_follow_fetchers(monkeypatch):
    from src.mcp_tools import tools
    monkeypatch.setattr(tools.db_client, 'count_sections_by_jurisdiction', lambda: {})
    coverage = tools.get_legal_coverage()['jurisdictions']
    for country, catalogue in [('NO', NORWEGIAN_LAWS), ('DE', GERMAN_LAWS), ('ES', SPANISH_LAWS)]:
        assert coverage[country]['catalog_statutes'] == len(catalogue)
        assert coverage[country]['statutes'] is False
