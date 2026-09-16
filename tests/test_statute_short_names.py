# -*- coding: utf-8 -*-
"""Varje lag som ingesteras måste ha ett kortnamn att slå upp den på.

Studieledighetslagen saknades i RiksdagenFetcher.KNOWN_LABOR_LAWS och lagrades
därför som "SFS 1974:981". Paragraferna fanns i databasen, men
`lookup_statute(law="Studieledighetslagen", section="1")` svarade "ej funnen" —
den enda formen en användare skulle skriva.

Det är samma listglidning som redan träffat projektet en gång: DEFAULT_STATUTES
växte till nio lagar medan en annan lista stannade på åtta. Ett test som jämför
listorna kostar ingenting och stänger hela klassen.
"""

import pytest

from src.scrapers.riksdagen_fetcher import RiksdagenFetcher
from src.services.sync_service import DEFAULT_STATUTES


def test_every_ingested_statute_has_a_known_short_name():
    saknas = [sfs for sfs in DEFAULT_STATUTES if sfs not in RiksdagenFetcher.KNOWN_LABOR_LAWS]
    assert not saknas, (
        f"ingesteras men saknar kortnamn i KNOWN_LABOR_LAWS: {saknas}. "
        "Utan det lagras lagen som 'SFS <nummer>' och går inte att slå upp på namn."
    )


def test_no_short_name_is_just_the_sfs_number():
    """"SFS 1974:981" är reservvärdet, inte ett kortnamn."""
    for sfs, info in RiksdagenFetcher.KNOWN_LABOR_LAWS.items():
        assert not info["short_name"].upper().startswith("SFS "), \
            f"{sfs} har reservnamnet {info['short_name']!r} inlagt som riktigt kortnamn"


def test_short_names_are_unique():
    """Två lagar med samma kortnamn gör uppslagningen tvetydig."""
    namn = [i["short_name"].lower() for i in RiksdagenFetcher.KNOWN_LABOR_LAWS.values()]
    assert len(namn) == len(set(namn)), f"dubblerade kortnamn: {namn}"


def test_business_leave_statute_is_in_default_catalog():
    assert "1997:1293" in DEFAULT_STATUTES
    assert RiksdagenFetcher.KNOWN_LABOR_LAWS["1997:1293"]["short_name"] == "Näringsverksamhetsledighetslagen"
