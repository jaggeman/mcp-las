# MCP LAS 🇸🇪⚖️

Ett specialiserat **Model Context Protocol (MCP)**-system och server för svensk arbetsrätt, rättspraxis (Arbetsdomstolen) och kollektivavtal, byggt med **Python FastMCP** och **Google Firebase Firestore**.

---

## 🌟 Funktioner

- 📜 **Deterministisk Legal Law-Chunking**: Indexerar och delar upp lagtext strikt efter **Kapitel** och **Paragraf (§)** med bevarad juridisk kontext.
- 🔍 **Hybrid Semantisk + Lexikal Sökning**: Sök i lagar med naturligt språk eller specifika lagtermer.
- ⚖️ **Exakt Paragrafuppslagning**: Hämta omedelbart gällande lydelse för t.ex. `LAS 7 §`, `Semesterlagen 12 §` eller `MBL 11 §`.
- 🏛️ **Rättspraxis (Arbetsdomstolen - AD)**: Sök i vägledande domar och se tillämpning av lagregler.
- 🤝 **Kollektivavtalsjämförelse (CBA)**: Undersök avvikelser från semidispositiv rätt (t.ex. *Teknikavtalet*, *Almega*) mot lagens grundregler.
- ☁️ **Google Firebase Firestore**: Skalbar dokument- och vektordatabas för lagmetadata, sektioner, domar och avtalsregler.

---

## 🛠️ MCP-Verktyg (Tools)

| Verktyg | Beskrivning | Exempelanrop |
| :--- | :--- | :--- |
| `lookup_statute` | Exakt hämtning av specifik paragraf och rubrik | `law="LAS", section="7"` |
| `search_labor_law` | Hybrid semantisk sökning i svensk arbetsrätt | `query="sakliga skäl uppsägning personliga skäl"` |
| `search_case_law` | Sökning i Arbetsdomstolens (AD) domar | `query="avskedande illojalitet", year_from=2020` |
| `get_cba_exception` | Kontrollera avvikelse i kollektivavtal från lag | `statute="LAS", section="11", agreement_name="Teknikavtalet"` |
| `compare_statute_vs_cba` | Jämför lagens grundregel mot kollektivavtal | `topic="Uppsägningstid", agreement_name="Teknikavtalet"` |

---

## 🚀 Snabbstart

### 1. Klona och installera beroenden

```powershell
git clone https://github.com/jaggeman/mcp-las.git
cd mcp-las

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Konfiguration (`.env`)

Skapa en `.env`-fil från `.env.example`:

```ini
# Firebase-konfiguration (valfritt för offline/lokalt läge)
FIREBASE_PROJECT_ID=ditt-firebase-projekt
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
USE_FIRESTORE_EMULATOR=false

# Embeddings: 'openai', 'gemini' eller 'mock'
EMBEDDING_PROVIDER=mock
OPENAI_API_KEY=
```

### 3. Ladda ner och indexera lagar från Riksdagens API

```powershell
python scripts/ingest_statutes.py
```
Detta hämtar och indexerar automatiskt:
- **LAS** (SFS 1982:80)
- **Semesterlagen** (SFS 1977:480)
- **MBL** (SFS 1976:580)
- **Arbetstidslagen** (SFS 1982:673)
- **Diskrimineringslagen** (SFS 2008:567)

---

## 🔌 Anslut till MCP-klienter (Claude Desktop / Cursor)

### Alternativ A: Anslut via Molnet (Streamable HTTP — Ny modern standard)
Ingen lokal installation krävs. Använd den publika Streamable HTTP-endpointen i Claude Connector / Claude Desktop / ChatGPT:
```
https://mcp-las-rules.web.app/mcp
```

### Alternativ B: Lokal körning i `claude_desktop_config.json`
```json
{
  "mcpServers": {
    "mcp-las": {
      "command": "C:\\LAS\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\LAS\\src\\server.py"
      ],
      "env": {
        "PYTHONPATH": "C:\\LAS"
      }
    }
  }
}
```

---

## ⚖️ Ansvarsfriskrivning (Legal Disclaimer)

> **Viktigt:** Denna MCP-server är ett öppen källkodsprojekt (Open Source) utvecklat för informations- och AI-integrationsändamål. Svar och information som tillhandahålls utgör **inte juridisk rådgivning** och ersätter inte professionell juridisk expertis, advokat eller facklig rådgivare. Skaparen friskriver sig från allt ansvar för beslut eller tolkningar som fattas med stöd av tjänsten.

---

## 📄 Licens

Öppen källkod licensierad under **[MIT License](LICENSE)**.

---

## 🧪 Kör tester

```powershell
pytest -v
```

