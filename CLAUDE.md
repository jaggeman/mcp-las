# CLAUDE.md - AI Agent & Assistant Guide for MCP-LAS

## Säkerhet för MCP och Excel-export

Publika MCP-anrop utan nyckel delar en kvot på 60 anrop/minut.
Angiven API-nyckel måste vara giltig och aktiv för kvoten 300 anrop/minut.
Ogiltiga nycklar nekas; Firestore-nycklar kräver booleskt `is_active=true`.
REST accepterar nycklar endast i `X-API-Key`, inte URL eller JSON-body.
Kvoter delas mellan instanser med Firestore-transaktioner i `mcp_rate_limits`.
Vid fel i kvotlagringen nekas anrop. Utan databas används en trådsäker lokal
reserv med högst 10000 klientposter. HTTP har dessutom en gemensam kvot på
600 anrop/minut före autentisering för API/MCP/SSE. I Firestore fördelas
HTTP-kvoten över 16 servervalda slumpmässiga delkvoter (37 eller 38 anrop),
vars summa är 600. Full delkvot nekas utan lån från andra delar; vid ojämn
fördelning kan 429 komma innan det gemensamma taket nåtts. Detta undviker
att alla HTTP-anrop konkurrerar om ett enda dokument. Under byte från äldre
revision kan gamla/nya kvoter samexistera i högst ett kvotfönster.
HTTP-body begränsas före parsning till 1 MiB (ansökningsformulär: 16 KiB)
och högst 10 sekunders inläsning. Proxyheaders betros inte; formulärets kvot
baseras på anslutande nätverksadress, som bakom proxy kan delas av flera användare.
Användningsloggar (`event=las_tool_usage`) sparar verktyg, MCP/REST, land,
status, svarstid, tidsstämpel och slumpmässigt event-ID. Inga frågor, resultat,
personuppgifter, API-nycklar, IP-adresser eller klientidentifierare loggas här.
Varje anrop som når verktygswrappern loggas en gång, även vid nekad åtkomst/fel.
MCP-schemafel före wrappern räknas inte som verktygsanrop. HTTP-fel loggas separat
som `las_http_rejected` och ska inte adderas till verktygsantalet.
Loggar skrivs som JSON till stdout (Cloud Logging); Firestore `access_logs` skrivs
via en begränsad bakgrundskö (1000 poster) utan att hålla kvar verktygssvaret.
Kön är best effort: full kö, instansavslut eller fryst bakgrunds-CPU kan ge
fördröjda/saknade Firestore-poster. Cloud Logging är den primära loggkällan.
Svarstiden avser verktygswrappern, inte transporttid eller bakgrundsskrivning.
Firestore-fel påverkar inte verktygssvaret; stdout finns kvar men rapporten kan då
underskatta användningen. Händelser samlas först efter deploy, ingen historik återskapas.
Nya Firestore-loggar får `expires_at` efter 30 dagar. Cloud Logging har separat retention.
Rapport: `.venv\\Scripts\\python.exe -m scripts.usage_report --days 7` (Firestore-läsbehörighet).
Rapporten visar antal per dag/verktyg/land/transport/status och medel/p95-svarstid.
Högst 10000 poster sammanställs; `truncated=true` betyder ofullständig rapport.
Äldre loggformat exkluderas. Antal anrop är inte antal unika användare eller AI-tokenkostnad.
Cloud Logs Explorer-filter: `resource.type="cloud_run_revision" resource.labels.service_name="mcp-las" jsonPayload.event="las_tool_usage"`.
Firestore TTL på `expires_at` för `access_logs` och `mcp_rate_limits` har
aktiverats i paygap-prod 2026-09-19 och verifierats ACTIVE.
TTL är asynkron och påverkar inte kvoternas giltighetskontroll.
Äldre loggar utan utgångstid kräver separat granskning/gallring; de raderas inte av koden.
CI använder Workload Identity Federation, inte `GCP_SA_KEY`.
GitHub OIDC konfigurerades 2026-09-19: pool `github-mcp-las`, provider
`github-main` i projekt 453511359123. Villkoren begränsar repository-ID
1359199704, ägar-ID 209946709, main, push och `.github/workflows/ci.yml`.
GitHub-variablerna `GCP_WORKLOAD_IDENTITY_PROVIDER` och `GCP_DEPLOY_SERVICE_ACCOUNT`
är satta. Befintliga `github-deployer@paygap-prod.iam.gserviceaccount.com`
återanvänds utan utökade projektroller. OIDC verifierades vid deploy av ddec5ca.
Veckosynken använder separat OIDC-pool `github-mcp-sync`, provider `github-sync`,
och `mcp-source-sync@paygap-prod.iam.gserviceaccount.com` med endast
`roles/datastore.user` på projektet, utan deployroller. Villkoren tillåter endast
samma repository/ägare, main och `sync-sources.yml` vid schedule/workflow_dispatch.
GitHub-variabler: `GCP_SYNC_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SYNC_SERVICE_ACCOUNT`.
Jobbet synkar Sverige, Norge och Tyskland måndagar 03:00 UTC, utan överlappande körningar.
Ingen workflow använder längre `GCP_SA_KEY`; den gamla nyckeln har inte
återkallats eftersom eventuella användningar utanför repot inte har inventerats.
Excel-länkar är hemliga bearer-token med 256 bitars slump och högst 10 minuters
giltighet. Alla som har länken kan hämta filen; dela eller logga därför inte länkarna.
Filer rensas automatiskt. Cachen är processlokal: högst 32 filer, 32 MiB totalt
och 2 MiB per fil. Omstart eller kapacitetsrensning kan göra länkar ogiltiga tidigare;
vid flera instanser kan en annan instans sakna filen. Base64-exporten finns kvar.
Export accepterar högst 1000 anställda, 32 fält per anställd och 2000 tecken per fält.
Användarfält sparas som text, medan serverns DATEDIF-formler behålls.
Docker-kontexten exkluderar miljöfiler och vanliga nyckel-/credential-filer.

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
Prod synkroniserades 2026-09-19: 385 norska och 330 tyska paragrafer,
14 lagar totalt, inga rapporterade synkfel. Antalen kan ändras vid senare synk.
Katalogen är avgränsad, inte fullständig nationell arbetsrätt. Norska traktatbilagor
med artikelnummer och tyska bilagor ingår inte i paragrafindexet.
Beräkningar, praxis, kollektivavtal och HR-mallar stöds fortfarande endast för Sverige.
`get_legal_coverage` anger faktisk paragrafmängd och tillgänglighet per land,
utifrån databasen. Källfel rapporteras som driftfel, inte som en tom lagdatabas.
Cacheuppdateringar samordnas inom varje process för att undvika dubbla inläsningar.
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

