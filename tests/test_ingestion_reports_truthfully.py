"""Ingestionen får aldrig rapportera rader den inte sparat.

save_statute_section skrev till ett minnesdict, hoppade över Firestore när
klienten saknades och svalde skrivfel med `except: pass`. Skriptet räknade
varje försök, inte varje lyckad skrivning, och avslutade med
"Total sections indexed: 492" med noll rader i databasen. Kvittot var alltså
självsäkert och falskt — vilket är värre än ett fel, för ingen går tillbaka
och kontrollerar.
"""

import pytest

from src.db.firebase_client import db_client


def test_skrivning_utan_databas_rapporterar_falskt(monkeypatch):
    monkeypatch.setattr(db_client, "db", None)
    resultat = db_client.save_statute_section(
        {"id": "test-1", "raw_text": "text", "embedding": [0.0]}
    )
    assert resultat is False, "utan databas får en skrivning inte rapportera framgång"


def test_svalt_skrivfel_rapporterar_falskt(monkeypatch):
    """Ett fel från Firestore ska inte längre försvinna i ett tyst `pass`."""

    class TrasigDb:
        def collection(self, _namn):
            raise RuntimeError("behörighet saknas")

    monkeypatch.setattr(db_client, "db", TrasigDb())
    resultat = db_client.save_statute_section(
        {"id": "test-2", "raw_text": "text", "embedding": [0.0]}
    )
    assert resultat is False, "ett misslyckat skrivförsök får inte räknas som sparat"


def test_lyckad_skrivning_rapporterar_sant(monkeypatch):
    skrivet = {}

    class Doc:
        def __init__(self, id_): self.id = id_
        def set(self, data): skrivet[self.id] = data

    class Koll:
        def document(self, id_): return Doc(id_)

    class OkDb:
        def collection(self, _namn): return Koll()

    monkeypatch.setattr(db_client, "db", OkDb())
    assert db_client.save_statute_section(
        {"id": "test-3", "raw_text": "text", "embedding": [0.0]}
    ) is True
    assert "test-3" in skrivet


def test_ingestionen_avbryter_utan_databas(monkeypatch, capsys):
    """Skriptet ska stanna innan arbetet, inte köra klart och ljuga om det."""
    from scripts.ingest_statutes import run_ingestion

    monkeypatch.setattr(db_client, "db", None)
    resultat = run_ingestion(["1982:80"])

    assert resultat is None
    utskrift = capsys.readouterr().out
    assert "AVBRUTET" in utskrift
    # Det gamla, falska kvittot får inte förekomma
    assert "sections indexed" not in utskrift
