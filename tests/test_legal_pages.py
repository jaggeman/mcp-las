from pathlib import Path


PUBLIC = Path("public")


def _read(name: str) -> str:
    return (PUBLIC / name).read_text(encoding="utf-8")


def test_privacy_and_cookie_policy_describes_actual_processing():
    content = _read("privacy.html")

    for required in (
        "Novro Sweden AB",
        "jagge@novro.se",
        "mcp_lang",
        "mcp_theme",
        "90 dagar",
        "Google Cloud",
        "e-postleverantör",
        "IMY",
        "rättslig grund",
        "automatiserat beslutsfattande",
    ):
        assert required in content

    assert "analyscookies" in content
    assert "säljer inte" in content


def test_terms_cover_service_specific_risks_and_rules():
    content = _read("terms.html")

    for required in (
        "inte juridisk rådgivning",
        "officiella källan",
        "API-nyckel",
        "personuppgifter",
        "känsliga personuppgifter",
        "tillgänglighet",
        "svensk lag",
        "jagge@novro.se",
    ):
        assert required in content


def test_homepage_links_legal_pages_and_requires_acknowledgement():
    content = _read("index.html")

    assert 'href="/privacy.html"' in content
    assert 'href="/terms.html"' in content
    assert 'id="legalAccept"' in content
    assert 'type="checkbox"' in content
    assert 'id="legalAccept" required' in content
    assert "integritetspolicyn" in content


def test_public_pages_do_not_load_third_party_fonts_or_stylesheets():
    for name in ("index.html", "privacy.html", "terms.html"):
        content = _read(name)
        assert "fonts.googleapis.com" not in content
        assert "fonts.gstatic.com" not in content
        assert "cdnjs.cloudflare.com" not in content

    assert (PUBLIC / "vendor/fontawesome/css/all.min.css").exists()
    assert list((PUBLIC / "vendor/fontawesome/webfonts").glob("*.woff2"))
