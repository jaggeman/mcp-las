from pathlib import Path

def test_website_contains_60_ad_cases_and_no_legacy_30_ad():
    html_path = Path("public/index.html")
    assert html_path.exists(), "public/index.html must exist"
    content = html_path.read_text(encoding="utf-8")
    
    # Verify 60 AD cases are referenced
    assert "60 AD-Domar" in content or "60 AD-prejudikat" in content
    assert "30 AD-Domar" not in content, "Legacy '30 AD-Domar' still found in index.html"
    assert "30 AD-prejudikat" not in content, "Legacy '30 AD-prejudikat' still found in index.html"
    assert "30 Labour Court precedents" not in content, "Legacy '30 Labour Court precedents' still found in index.html"

def test_website_contains_all_official_sources_and_master_table():
    html_path = Path("public/index.html")
    content = html_path.read_text(encoding="utf-8")
    
    required_sources = [
        "data.riksdagen.se",
        "arbetsdomstolen.se",
        "mi.se",
        "forsakringskassan.se",
        "scb.se",
        "skatteverket.se",
        "do.se",
        "arbetsgivarintyg.nu"
    ]
    for src in required_sources:
        assert src in content, f"Source '{src}' missing from public/index.html"

def test_website_navbar_does_not_contain_unauthenticated_rest_api_link():
    html_path = Path("public/index.html")
    content = html_path.read_text(encoding="utf-8")
    nav_section = content[content.find("<nav>"):content.find("</nav>")]
    assert "REST API" not in nav_section, "'REST API' link still present in navigation bar"

def test_website_documents_automated_source_sync_and_danish_roadmap():
    html_path = Path("public/index.html")
    content = html_path.read_text(encoding="utf-8")
    assert "Automatisk källsynkronisering" in content
    assert "Cloud Run Job" in content
    assert "Danska lagar" in content
    assert "DA-001" in content
