"""Canonical metadata for every supported legal jurisdiction."""

JURISDICTIONS = {
    "SE": {
        "country": "Sverige",
        "language": "sv",
        "source": "Riksdagen",
        "smoke_query": "provanställning",
        "case_law": "Arbetsdomstolen",
        "collective_agreements": True,
        "calculators": ["notice_period", "vacation", "turnorder", "travel"],
        "hr_templates": True,
    },
    "DK": {
        "country": "Danmark", "language": "da", "source": "Retsinformation",
        "smoke_query": "ferie", "case_law": False, "collective_agreements": False,
        "calculators": [], "hr_templates": False,
    },
    "FI": {
        "country": "Finland", "language": "fi", "source": "Finlex",
        "smoke_query": "työsopimus", "case_law": False, "collective_agreements": False,
        "calculators": [], "hr_templates": False,
    },
    "NO": {
        "country": "Norge", "language": "nb", "source": "Lovdata",
        "smoke_query": "arbeidsmiljø", "case_law": False, "collective_agreements": False,
        "calculators": [], "hr_templates": False,
    },
    "DE": {
        "country": "Tyskland", "language": "de", "source": "Gesetze im Internet",
        "smoke_query": "Kündigung", "case_law": False, "collective_agreements": False,
        "calculators": [], "hr_templates": False,
    },
    "ES": {
        "country": "Spanien", "language": "es", "source": "BOE",
        "smoke_query": "vacaciones", "case_law": False, "collective_agreements": False,
        "calculators": [], "hr_templates": False,
    },
    "NL": {
        "country": "Nederländerna", "language": "nl", "source": "KOOP Basiswettenbestand",
        "smoke_query": "arbeidsovereenkomst", "case_law": False, "collective_agreements": False,
        "calculators": [], "hr_templates": False,
    },
    "GB": {
        "country": "Storbritannien", "language": "en", "source": "legislation.gov.uk",
        "smoke_query": "unfair dismissal", "case_law": False, "collective_agreements": False,
        "calculators": [], "hr_templates": False,
    },
}

JURISDICTION_CODES = tuple(JURISDICTIONS)
JURISDICTION_LANGUAGES = {
    code: details["language"] for code, details in JURISDICTIONS.items()
}
SMOKE_QUERIES = {
    code: details["smoke_query"] for code, details in JURISDICTIONS.items()
}

