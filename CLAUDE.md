# CLAUDE.md - AI Agent & Assistant Guide for MCP-LAS

Detta dokument beskriver arkitektur, driftsättning, miljövariabler och MCP-konfiguration för **MCP-LAS** under Novro (`las.novro.se`).

---

## 🏛️ Systemöversikt & Arkitektur

MCP-LAS är en **Model Context Protocol (MCP)**-server för nordisk arbetsrätt (Sverige, Danmark, Finland), rättspraxis (Arbetsdomstolen), kollektivavtal (13 avtal, 17 kurerade regler) och praktiska HR-beräkningsverktyg (turordning enligt LAS 22 §, semesterlöner, avdrag, m.m.).

| Egenskap | Specifikation / Värde |
| :--- | :--- |
| **Huvuddomän & Subdomän** | **`https://las.novro.se`** |
| **MCP Streamable HTTP Endpoint** | **`https://las.novro.se/mcp`** |
| **GCP / Firebase Projekt (Prod)** | **`paygap-prod`** (Projektnummer: `453511359123`) |
| **Cloud Run Region** | **`europe-west3`** (Frankfurt) |
| **Cloud Run Service** | `mcp-las` |
| **Firebase Hosting Target** | `mcp-novro` (Rewrites pekar mot Cloud Run `europe-west3`) |
| **Alternativa miljöer** | Test: `paygap-jaggeman` \| Demo: `paygap-demo` |

---

## 🔌 Anslutning till Claude & AI-Klienter

### 1. Claude Web / Claude Custom Connector (Streamable HTTP)
Använd URL:
```
https://las.novro.se/mcp
```

### 2. Claude Desktop (`claude_desktop_config.json`)
```json
{
  "mcpServers": {
    "mcp-las": {
      "url": "https://las.novro.se/mcp"
    }
  }
}
```

### 3. Cursor / Windsurf (`.cursor/mcp.json`)
```json
{
  "mcpServers": {
    "mcp-las": {
      "url": "https://las.novro.se/mcp"
    }
  }
}
```

---

## 🚢 Driftsättning & Deploy-kommandon

Driftsättning görs mot **`paygap-prod`** i **`europe-west3`**:

### 1. Driftsätt Backend & MCP Server (Cloud Run)
```powershell
gcloud run deploy mcp-las `
  --source . `
  --project=paygap-prod `
  --region=europe-west3 `
  --allow-unauthenticated
```

### 2. Driftsätt Web UI & Hosting (Firebase Hosting)
```powershell
firebase deploy --only hosting:mcp-novro --project=paygap-prod
```

---

## ⚙️ Miljövariabler & Konfiguration (`.env`)

Kopiera `.env.example` till `.env` för lokal utveckling:

```ini
# GCP / Firebase
FIREBASE_PROJECT_ID=paygap-prod
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
USE_FIRESTORE_EMULATOR=false
FIRESTORE_EMULATOR_HOST=localhost:8080

# Port och Server
PORT=8080
MCP_SERVER_NAME=mcp-las
MCP_SERVER_PORT=8000

# Embeddings (mock, openai, gemini)
EMBEDDING_PROVIDER=mock
OPENAI_API_KEY=
GEMINI_API_KEY=
```

---

## 🧪 Test-Driven Development (TDD) & Verifiering

Följ strikt projektets utvecklingsregler ([AGENTS.md](file:///c:/LAS/AGENTS.md)):

1. **Kör tester före commit/deploy**:
   ```powershell
   .venv\Scripts\pytest.exe tests/ -v
   ```
2. **Verifiera lagparagraftäckning (100% determinism)**:
   ```powershell
   .venv\Scripts\python.exe check_coverage.py
   ```
3. **Säkerhetskrav**:
   - Docker körs med icke-root användare `appuser` (UID `10001`).
   - API-nycklar valideras med konstanttidsjämförelse (`hmac.compare_digest`).
   - Rate limiting via sliding window.

4. **Dokumentations- & Instruktionssynkronisering (Strikthet)**:
   - Om ändringar görs i infrastruktur, driftsättningskommandon, miljövariabler, domäner/endpoints eller regler i någon av filerna (`CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `CODEX.md` eller `README.md`), **måste samtliga dessa 5 filer uppdateras samtidigt** så att alla AI-agenter och modeller alltid är 100% i synk.

