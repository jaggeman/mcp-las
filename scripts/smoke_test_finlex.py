"""Read-only live smoke test for the Finlex adapter."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.finlex_fetcher import FinlexFetcher


def main() -> int:
    documents = FinlexFetcher.harvest_statutes(page=1, limit=1)
    if not documents:
        raise RuntimeError("Finlex returned no documents")

    document = documents[0]
    metadata, sections = FinlexFetcher.get_document(document)
    required = {
        "jurisdiction": "FI",
        "language": "fi",
        "source": "Finlex",
    }
    for key, expected in required.items():
        if metadata.get(key) != expected:
            raise AssertionError(f"Unexpected {key}: {metadata.get(key)!r}")
    if not metadata.get("title") or not sections:
        raise AssertionError("Finlex document did not produce title and sections")
    if any(not section.content.strip() for section in sections):
        raise AssertionError("Finlex produced an empty legal section")

    employment_law = {
        "akn_uri": (
            "https://opendata.finlex.fi/finlex/avoindata/v1/"
            "akn/fi/act/statute/2001/55/fin@"
        ),
        "title": "Työsopimuslaki",
    }
    employment_metadata, employment_sections = FinlexFetcher.get_document(employment_law)
    if employment_metadata["document_id"].endswith("/2001/55/fin@") is False:
        raise AssertionError(f"Unexpected employment law id: {employment_metadata['document_id']}")
    if not employment_sections or not any(section.section_number == "1" for section in employment_sections):
        raise AssertionError("Työsopimuslaki did not produce section 1")

    print("Finlex live smoke test: PASS")
    print(f"document_id={metadata['document_id']}")
    print(f"title={metadata['title']}")
    print(f"language={metadata['language']}")
    print(f"sections={len(sections)}")
    print(f"first_section={sections[0].section_number}")
    print(f"employment_law={employment_metadata['title']}")
    print(f"employment_sections={len(employment_sections)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
