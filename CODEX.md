# CODEX.md - OpenAI Codex, ChatGPT & Copilot Guide for MCP-LAS

## Säkerhet för MCP och Excel-export

Publika MCP-anrop utan nyckel delar en kvot på 60 anrop/minut.
Angiven API-nyckel måste vara giltig och aktiv för kvoten 300 anrop/minut.
Ogiltiga nycklar nekas; Firestore-nycklar kräver booleskt `is_active=true`.
REST accepterar nycklar endast i `X-API-Key`, inte URL eller JSON-body.
Kvoter delas mellan instanser med Firestore-transaktioner i `mcp_rate_limits`.
Vid fel i kvotlagringen nekas anrop. Utan databas används en trådsäker lokal
reserv med högst 10000 klientposter. HTTP har dessutom en gemensam kvot på
600 anrop/minut före autentisering för API/MCP/SSE.
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
Den gamla nyckeln har inte återkallats: `sync-sources.yml` använder fortfarande
`GCP_SA_KEY`. Migrera den separat och verifiera båda flöden innan återkallning.
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


Detta dokument beskriver arkitektur, driftsättning, miljö och integrationsriktlinjer för **OpenAI Codex**, **ChatGPT Custom GPTs**, **GitHub Copilot** och OpenAI-drivna utvecklingsagenter.

---

## 🏛️ Systemöversikt & Infrastruktur

MCP-LAS är ett **Model Context Protocol (MCP)**-system för nordisk arbetsrätt (Sverige, Danmark, Finland), rättspraxis (Arbetsdomstolen), kollektivavtal (13 avtal, 17 regler) och HR-verktyg.

| Egenskap | Specifikation / Värde |
| :--- | :--- |
| **Produktionsdomän** | **`https://las.novro.se`** |
| **MCP Streamable HTTP Endpoint** | **`https://las.novro.se/mcp`** |
| **GCP / Firebase Projekt (Prod)** | **`paygap-prod`** (Frankfurt `europe-west3`) |
| **Cloud Run Service** | `mcp-las` |
| **Firebase Hosting Target** | `mcp-novro` (Rewrites pekar mot Cloud Run `europe-west3`) |

---

## 🤖 Anslutning till OpenAI & ChatGPT

### 1. ChatGPT Desktop / OpenAI Developer Mode (Streamable HTTP)
URL för MCP-anslutning:
```
https://las.novro.se/mcp
```

### 2. Custom GPT System Prompt
Klistra in denna instruktion i din Custom GPT:

```text
Du är en svensk och nordisk arbetsrättsexpert driven av MCP LAS (https://las.novro.se/mcp).
När användaren ställer frågor om svensk arbetsrätt, anställningsskydd (LAS), medbestämmande (MBL), semester, diskriminering eller kollektivavtal:
1. Slå alltid upp gällande lagtext och exakt paragraf via MCP LAS (t.ex. lookup_statute / search_labor_law).
2. Kontrollera alltid om tillämpligt kollektivavtal (t.ex. Teknikavtalet, Almega IT, Handels, Unionen) har semidispositiva avvikelser från lagen.
3. Vid semesterfrågor: använd MCP-verktygen för att beräkna semesterlön/tillägg, avdrag för obetald semester och intjänade semesterdagar.
4. Vid turordning vid arbetsbrist: använd beräkningsverktyget för turordning och undantagsregler (LAS 22 § vs kollektivavtal).
5. Vid reseavdrag & basbelopp: beräkna Skatteverkets milersättning (25 kr/mil) och hämta aktuella basbelopp (PBB/IBB 2026).
6. Hänvisa till relevanta AD-prejudikat vid tvister om sakliga skäl, personliga skäl eller arbetsbrist.
7. Tydliggör att svaren är informativa och inte utgör formell juridisk rådgivning.
```

### 3. Cursor & Windsurf Konfiguration (`.cursor/mcp.json`)
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

## 🚢 Driftsättning (Cloud Run & Firebase Hosting)

### 1. Automatisk CI/CD (Standard för AI-agenter)
Push eller merge till `main` triggar GitHub Actions (`.github/workflows/ci.yml`), som automatiskt kör hela testsviten och driftsätter både **Cloud Run** (`mcp-las`) och **Firebase Hosting** (`mcp-novro`).

### 2. Manuell driftsättning (CLI)
```powershell
# A. Driftsätt Backend till Cloud Run
gcloud run deploy mcp-las `
  --source . `
  --project=paygap-prod `
  --region=europe-west3 `
  --allow-unauthenticated

# B. Driftsätt Frontend/Hosting till Firebase
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

## 🧪 TDD & Säkerhetskrav

- Kör enhetstester: `.venv\Scripts\pytest.exe tests/ -v` (alla 57 tester måste passera).
- Verifiera lagparagrafer: `.venv\Scripts\python.exe check_coverage.py` (100% täckning över 477 paragrafer).
- Säkerhet: Non-root user `appuser` UID 10001, sliding-window rate limiting, konstanttids API-nyckeljämförelse (`hmac.compare_digest`).
- **Dokumentations- & Instruktionssynkronisering (Strikthet)**: Om ändringar görs i infrastruktur, driftsättningskommandon, miljövariabler, domäner/endpoints eller regler i någon av filerna (`CODEX.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` eller `README.md`), **måste samtliga dessa 5 filer uppdateras samtidigt** så att alla AI-agenter och modeller alltid är 100% i synk.

