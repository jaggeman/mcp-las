# GEMINI.md - Google Gemini & Agent Guide for MCP-LAS

Detta dokument beskriver arkitektur, driftsättning, miljö och integrationsriktlinjer för **Google Gemini**, **Gemini Gems**, **Google AI Studio** och Gemini-drivna kodagenter.

---

## 🏛️ Systemöversikt & Infrastruktur

MCP-LAS är en **Model Context Protocol (MCP)**-tjänst för nordisk arbetsrätt (Sverige, Danmark, Finland), rättspraxis från Arbetsdomstolen (AD), 13 centrala kollektivavtal (CBA) och HR-beräkningar (turordning LAS 22 §, semesterlöner, avdrag m.m.).

| Egenskap | Specifikation / Värde |
| :--- | :--- |
| **Produktionsdomän** | **`https://las.novro.se`** |
| **MCP Streamable HTTP Endpoint** | **`https://las.novro.se/mcp`** |
| **GCP / Firebase Projekt (Prod)** | **`paygap-prod`** (Projektnummer: `453511359123`) |
| **Cloud Run Region** | **`europe-west3`** (Frankfurt) |
| **Cloud Run Service** | `mcp-las` |
| **Firebase Hosting Target** | `mcp-novro` (Pekar på Cloud Run `europe-west3`) |
| **Test & Demo-miljöer** | Test: `paygap-jaggeman` \| Demo: `paygap-demo` |

---

## 💎 Integrera MCP-LAS med Google Gemini

### 1. Gemini Gem / AI Studio System Prompt
Klistra in denna instruktion i din Gemini Gem, Custom Agent eller Vertex AI Prompt:

```text
Du är en specialiserad rådgivare inom svensk och nordisk arbetsrätt och den svenska partsmodellen.
Använd MCP LAS (https://las.novro.se/mcp) för att hämta gällande lagstiftning från Riksdagen, 13 centrala kollektivavtal, vägledande domar från Arbetsdomstolen (AD) samt genomföra beräkningar av semester, avdrag och turordningslistor.

Strukturera alltid svaren med:
1. Lagens grundregel (med exakt kapitel- och paragrafhänvisning §).
2. Eventuella avvikelser i tillämpligt kollektivavtal (semidispositiv rätt).
3. Relevanta AD-domar och rättspraxis.
4. Vid arbetsgivarintyg för a-kassa: hänvisa till 47 § ALF och https://www.arbetsgivarintyg.nu.
5. Tydliggör att informationen är informativ och inte ersätter formell juridisk rådgivning.
```

---

## 🚢 Driftsättning & Deploy (GCP & Firebase)

### 1. Automatisk CI/CD (Standard för AI-agenter)
Push eller merge till `main` triggar GitHub Actions (`.github/workflows/ci.yml`), som automatiskt kör hela testsviten och driftsätter både **Cloud Run** (`mcp-las`) och **Firebase Hosting** (`mcp-novro`).

### 2. Manuell driftsättning (CLI)
```powershell
# A. Bygg och driftsätt backend till Cloud Run (paygap-prod)
gcloud run deploy mcp-las `
  --source . `
  --project=paygap-prod `
  --region=europe-west3 `
  --allow-unauthenticated

# B. Driftsätt frontend & hosting till Firebase (mcp-novro)
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
{"status":"ok","build_sha":"98b9878...","build_ref":"main","database_connected":true,"tool_count":20}
```

`build_sha` ska vara samma som `git rev-parse origin/main`. Är den äldre, eller
`unknown`, svarar domänen från något annat än det CI driftsätter. CI stämplar
`BUILD_SHA` vid deploy och bryter bygget om tjänsten inte svarar med det.

---

## ⚙️ Miljövariabler (`.env`)

```ini
FIREBASE_PROJECT_ID=paygap-prod
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
USE_FIRESTORE_EMULATOR=false
PORT=8080

# Tom = master-admin-vägen avstängd (rekommenderat)
MASTER_ADMIN_KEY=

EMBEDDING_PROVIDER=mock
OPENAI_API_KEY=
GEMINI_API_KEY=
```

---

## 🧪 Kvalitetssäkring & TDD-regler

1. **Strikt TDD**: Kör alltid `.venv\Scripts\pytest.exe tests/ -v` före commits/deploy (57+ tester, noll tolerans för fel).
2. **Legal Determinism**: Verifiera att alla 477 lagparagrafer är intakta utan trunkering via `.venv\Scripts\python.exe check_coverage.py`.
3. **Säkerhet**: Container körs som `appuser` (UID 10001), API-nycklar jämförs i konstant tid (`hmac.compare_digest`).
4. **Dokumentations- & Instruktionssynkronisering (Strikthet)**: Om ändringar görs i infrastruktur, driftsättningskommandon, miljövariabler, domäner/endpoints eller regler i någon av filerna (`GEMINI.md`, `AGENTS.md`, `CLAUDE.md`, `CODEX.md` eller `README.md`), **måste samtliga dessa 5 filer uppdateras samtidigt** så att alla AI-agenter och modeller alltid är 100% i synk.

