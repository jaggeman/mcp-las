"""Core Finnish employment-law sources available from Finlex."""

_FINLEX_LISTING_URL = "https://opendata.finlex.fi/finlex/avoindata/v1/akn/fi/act/statute/list"

FINNISH_LABOR_LAW_CATALOG = [
    {"name": "Työsopimuslaki", "act_number": "55/2001", "jurisdiction": "FI", "language": "fi", "priority": "core", "category": "employment", "source": "Finlex", "source_listing_url": _FINLEX_LISTING_URL},
    {"name": "Vuosilomalaki", "act_number": "162/2005", "jurisdiction": "FI", "language": "fi", "priority": "core", "category": "holiday", "source": "Finlex", "source_listing_url": _FINLEX_LISTING_URL},
    {"name": "Työaikalaki", "act_number": "872/2019", "jurisdiction": "FI", "language": "fi", "priority": "core", "category": "working_time", "source": "Finlex", "source_listing_url": _FINLEX_LISTING_URL},
    {"name": "Työturvallisuuslaki", "act_number": "738/2002", "jurisdiction": "FI", "language": "fi", "priority": "core", "category": "work_environment", "source": "Finlex", "source_listing_url": _FINLEX_LISTING_URL},
    {"name": "Yhdenvertaisuuslaki", "act_number": "1325/2014", "jurisdiction": "FI", "language": "fi", "priority": "core", "category": "discrimination", "source": "Finlex", "source_listing_url": _FINLEX_LISTING_URL},
    {"name": "Laki naisten ja miesten välisestä tasa-arvosta", "act_number": "609/1986", "jurisdiction": "FI", "language": "fi", "priority": "core", "category": "equality", "source": "Finlex", "source_listing_url": _FINLEX_LISTING_URL},
    {"name": "Yhteistoimintalaki", "act_number": "1333/2021", "jurisdiction": "FI", "language": "fi", "priority": "core", "category": "cooperation", "source": "Finlex", "source_listing_url": _FINLEX_LISTING_URL},
    {"name": "Työehtosopimuslaki", "act_number": "436/1946", "jurisdiction": "FI", "language": "fi", "priority": "extended", "category": "collective_agreements", "source": "Finlex", "source_listing_url": _FINLEX_LISTING_URL},
]
