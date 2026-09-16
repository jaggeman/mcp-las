# AI Agent Guidelines for MCP-LAS

Detta dokument utgör standardriktlinjerna för alla autonoma AI-agenter och kodassistenter som arbetar i projektet.

---

## 🏛️ Infrastruktur & Miljö (Novro Prod)

| Egenskap | Konfiguration |
| :--- | :--- |
| **Produktionsdomän** | **`https://las.novro.se`** |
| **MCP Endpoint** | **`https://las.novro.se/mcp`** |
| **GCP / Firebase Projekt** | **`paygap-prod`** (Frankfurt `europe-west3`) |
| **Cloud Run Service** | `mcp-las` |
| **Firebase Hosting Target** | `mcp-novro` (Rewrites till Cloud Run `europe-west3`) |

---

## 🚢 Driftsättningskommandon

### 1. Automatisk CI/CD (Standard för AI-agenter)
Push eller merge till `main` triggar GitHub Actions (`.github/workflows/ci.yml`), som automatiskt kör hela testsviten och driftsätter både **Cloud Run** (`mcp-las`) och **Firebase Hosting** (`mcp-novro`).

### 2. Manuell driftsättning (CLI)
```powershell
# 1. Cloud Run (Backend & MCP Server)
gcloud run deploy mcp-las --source . --project=paygap-prod --region=europe-west3 --allow-unauthenticated

# 2. Firebase Hosting (Webb & Dokumentation)
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

## 🔒 Kärnregler & Arkitektur

1. **Test-Driven Development (TDD) Obligatoriskt**:
   - Skriv alltid enhetstester i `tests/` innan nya funktioner implementeras eller buggar åtgärdas.
   - Kör hela testsviten (`.venv\Scripts\pytest.exe tests/ -v`) före commits och driftsättningar.
   - Noll testfel accepteras.

2. **Legal & Chunker Determinism**:
   - Ändra aldrig gränser för lagparagrafer utan att köra `python check_coverage.py`.
   - Säkerställ att samtliga 477 paragrafer över de 8 svenska kärnlagarna behåller 100% integritet utan trunkering eller dubbletter.

3. **Säkerhetsstandarder**:
   - Använd konstanttidsjämförelse (`hmac.compare_digest`) vid validering av API-nycklar.
   - Tillämpa sliding window rate limiting.
   - Logga strukturerade JSON-händelser via Cloud Logging.
   - Behåll icke-root användare (`appuser` UID 10001) i Dockerfile.

4. **Officiella Källor & Prejudikat**:
   - Håll domstolspraxis synkroniserad med Arbetsdomstolen (AD) och officiella portaler (Riksdagen, Retsinformation, Finlex, Försäkringskassan, DO, SCB).

5. **Dokumentations- & Instruktionssynkronisering (Strikthet)**:
   - Om ändringar görs i infrastruktur, driftsättningskommandon, miljövariabler, domäner/endpoints eller regler i någon av filerna (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `CODEX.md` eller `README.md`), **måste samtliga dessa 5 filer uppdateras samtidigt** så att alla AI-agenter och modeller alltid är 100% i synk.

