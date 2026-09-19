# CLAUDE.md - AI Agent & Assistant Guide for MCP-LAS

## Norge och Tyskland – laguppslag och sökning

`lookup_statute` och `search_labor_law` stöder `jurisdiction="NO"` respektive `"DE"`.
Norge: 6 lagar (Arbeidsmiljøloven, Ferieloven, Likestillings- og diskrimineringsloven,
Arbeidstvistloven, Allmenngjøringsloven och Statsansatteloven). Tyskland: 8 lagar
(KSchG, BUrlG, ArbZG, TzBfG, AGG, ArbSchG, BetrVG och EntgFG).

Synkronisera med `.venv\Scripts\python.exe scripts/sync_sources.py --norwegian --german`.
Kommandot skriver till konfigurerad Firestore och kräver skrivbehörighet.
Källor: https://api.lovdata.no/om-api-tjenesten/ (Stiftelsen Lovdata, NLOD 2.0)
och https://www.gesetze-im-internet.de/ (XML-paket per lag).
Norska paragrafnummer behålls, t.ex. `section="15-7"`; tyska t.ex. `section="1a"`.
Källspråk är `nb` respektive `de`. Sök på källspråket; översättning garanteras inte.
Katalogen är avgränsad, inte fullständig nationell arbetsrätt. Norska traktatbilagor
med artikelnummer och tyska bilagor ingår inte i paragrafindexet.
Beräkningar, praxis, kollektivavtal och HR-mallar stöds fortfarande endast för Sverige.
`get_legal_coverage` beskriver adapterstöd, inte verifierad produktionsinläsning.
Efter extern synk uppdateras serverns lagcache inom 60 sekunder utan omstart.
Synken kontrollerar alla skrivningar, fortsätter med nästa lag vid källfel och markerar
borttagna paragrafer som inaktiva (återställningsbara), inte som gällande sökträffar.
Embedding-provider och modell ingår i synkhashen; providerbyte kräver omindexering av
hela korpusen. `EMBEDDING_PROVIDER=mock` använder alltid lokal beräkning även om API-nycklar
finns. OpenAI/Gemini ger fel vid saknad nyckel eller API-fel, utan tyst byte till mock.


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

### 1. Automatisk CI/CD (Standard för AI-agenter)
Push eller merge till `main` triggar GitHub Actions (`.github/workflows/ci.yml`), som automatiskt kör hela testsviten och driftsätter både **Cloud Run** (`mcp-las`) och **Firebase Hosting** (`mcp-novro`).

### 2. Manuell driftsättning (CLI)
Driftsättning görs mot **`paygap-prod`** i **`europe-west3`**:

#### A. Driftsätt Backend & MCP Server (Cloud Run)
```powershell
gcloud run deploy mcp-las `
  --source . `
  --project=paygap-prod `
  --region=europe-west3 `
  --allow-unauthenticated
```

#### B. Driftsätt Web UI & Hosting (Firebase Hosting)
```powershell
firebase deploy --only hosting:mcp-novro --project=paygap-prod
```

---

### 3. Verifiera vilken kod som faktiskt kör

`gcloud run deploy` rapporterar lyckad driftsättning även när trafiken ligger
kvar på en äldre revision, och säger ingenting alls om en andra driftsättning
av samma tjänst i ett annat projekt. `/health` svarar med det commit som kör:

```powershell
curl.exe -s https://las.novro.se/health
```

```json
{"status":"ok","build_sha":"98b9878...","build_ref":"main","database_connected":true,"tool_count":21}
```

`build_sha` ska vara samma som `git rev-parse origin/main`. Är den äldre, eller
`unknown`, svarar domänen från något annat än det CI driftsätter. CI stämplar
`BUILD_SHA` vid deploy och bryter bygget om tjänsten inte svarar med det.

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

# Master-admin-nyckel. Tom = master-vagen avstangd (rekommenderat).
# Sätts via Secret Manager i prod, aldrig i koden.
MASTER_ADMIN_KEY=

# Embeddings (mock, openai, gemini)
EMBEDDING_PROVIDER=mock
OPENAI_API_KEY=
GEMINI_API_KEY=
```

---

## 🧪 Test-Driven Development (TDD) & Verifiering

Följ strikt projektets utvecklingsregler ([AGENTS.md](AGENTS.md)):

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

