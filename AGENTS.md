# AI Agent Guidelines for MCP-LAS

## Säkerhet för MCP och Excel-export

Publika MCP-anrop utan nyckel delar en kvot på 60 anrop/minut.
Angiven API-nyckel måste vara giltig och aktiv för kvoten 300 anrop/minut.
Ogiltiga nycklar nekas; Firestore-nycklar kräver booleskt `is_active=true`.
Giltiga nyckeluppslag cachelagras processlokalt i högst 30 sekunder och 1000 poster;
en återkallad nyckel kan därför fortsätta fungera i högst 30 sekunder på en varm instans.
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
Rapport: `.venv\\Scripts\\python.exe -m scripts.usage_report --days 7` läser Cloud Logging
via `gcloud` och kräver loggläsbehörighet. `--source firestore` finns endast för äldre data.
`STORE_USAGE_IN_FIRESTORE=false` är standard och sätts av CI för att undvika en extra
Firestore-skrivning per anrop; aktivera bara den duplicerade kopian när den uttryckligen behövs.
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
Jobbet synkar Sverige, Norge, Tyskland och Spanien måndagar 03:00 UTC, utan överlappande körningar.
Sverige synkas direkt på GitHub-runnern; Riksdagen-hämtning från Cloud Run misslyckades.
Norge, Tyskland och Spanien körs i Frankfurt. GitHub startar Cloud Run Job `mcp-las-source-sync` i europe-west3 och väntar på resultatet.
Direkt hämtning från GitHub fick anslutningstimeout till den tyska källan; Frankfurt fungerar.
Synkkontot har även `roles/run.jobsExecutor` och `roles/run.viewer` på endast detta jobb.
CI uppdaterar jobbets image till samma digest som backend och anger flaggorna --norwegian --german --spanish.
Jobbet använder mock-embeddings, 1 CPU/1 GiB, 1800 sekunders timeout och inga automatiska omförsök.
Ingen workflow använder längre `GCP_SA_KEY`; den gamla nyckeln har inte
återkallats eftersom eventuella användningar utanför repot inte har inventerats.
Excel-länkar är hemliga bearer-token med 256 bitars slump och högst 10 minuters
giltighet. Alla som har länken kan hämta filen; dela eller logga därför inte länkarna.
Filer rensas automatiskt. Cachen är processlokal: högst 32 filer, 32 MiB totalt
och 2 MiB per fil. Omstart eller kapacitetsrensning kan göra länkar ogiltiga tidigare;
vid flera instanser kan en annan instans sakna filen. Base64-exporten finns kvar.
Exporten tar inte emot anställda alls: den genererar en tom mall med 1-1000 rader
(`row_count`). Företags- och avtalsnamn får vara högst 200 tecken. Användarfält
sparas som text, medan serverns egen DATEDIF-formel behålls som formel.
Se avsnittet om separation mellan MCP-LAS och Novro.
Docker-kontexten exkluderar miljöfiler och vanliga nyckel-/credential-filer.
Cloud Run begränsas av CI till 5 instanser och concurrency 40. Uvicorns accesslogg är
avstängd eftersom Cloud Run redan skapar en requestlogg för varje HTTP-anrop.

## Separation mellan MCP-LAS och Novro

MCP-LAS är en **lässerver för arbetsrätt**. Novro (`app.novro.se`) är ett
HR-system med anställningsuppgifter, löner och lönekartläggningar. Det är två
olika system och ska förbli det. MCP-LAS ska aldrig ta emot, läsa eller skriva
Novros persondata.

**Verktygen tar inte emot personuppgifter.** Inget verktyg accepterar namn,
personnummer, födelsedatum eller listor över anställda.
`generate_turordningslista_excel` genererar en TOM mall som fylls i lokalt,
`calculate_redundancy_turnorder_and_exceptions` räknar på antal i stället för
på personer, och `get_hr_document_template` levererar platshållare.
`tests/test_no_personal_data.py` låser fast det: parametrarna får inte smyga
tillbaka. Beräkningarna är rena sorteringar som den anropande assistenten kan
göra lokalt på data som stannar hos användaren.

**Ingen kodväg rör Novros data.** MCP-LAS använder enbart sina egna
collections: `statutes`, `statute_sections`, `agreement_rules`, `precedents`,
`source_sync_state`, `api_keys`, `key_requests`, `access_logs`,
`cache_versions` och `mcp_rate_limits`. Lägg aldrig till en läsning av
`organizations/`, `users/` eller någon annan Novro-collection.

**Ingen loggning av innehåll.** `src/services/usage_logging.py` skriver bara
allowlistad metadata (verktyg, transport, land, status, svarstid) — aldrig
argument, aldrig resultat.

**Dedikerat runtime-konto.** Cloud Run-tjänsten körs som
`mcp-las-runtime@paygap-prod.iam.gserviceaccount.com` via `--service-account`
i `ci.yml`. Utan den flaggan kör tjänsten som projektets default
compute-konto, som i GCP:s standarduppsättning har Editor på hela projektet —
alltså full åtkomst till Novros data. **Ta aldrig bort flaggan.** Kontot
skapas med `scripts/setup_runtime_service_account.sh`.

**Detta är ännu inte fullständig separation.** Båda systemen ligger i
GCP-projektet `paygap-prod` och delar Firestores `(default)`-databas.
`roles/datastore.user` gäller hela databasen — Firestore har ingen IAM på
collection-nivå — så runtime-kontot *kan* fortfarande läsa Novros collections
även om ingen kod gör det. Det dedikerade kontot tar bort Editor-behörigheten,
inte databasgränsen. Full separation kräver ett av två steg:

1. **Egen Firestore-databas** för LAS i samma projekt, med IAM-villkor som
   binder kontot till just den databasen. Kräver datamigrering.
2. **Eget GCP-projekt** för MCP-LAS. Renast, men störst arbete.

**Checklista innan något nytt byggs här:** Tar ändringen emot en
personuppgift? Läser den en collection som inte står i listan ovan? Loggar den
något annat än metadata? Behöver den en bredare IAM-roll? Är svaret ja på
någon av frågorna hör funktionen inte hemma i MCP-LAS.

## Norge, Tyskland och Spanien – laguppslag och sökning
`lookup_statute` och `search_labor_law` stöder `jurisdiction="NO"` respektive `"DE"`, samt `"ES"` för Spanien.
Norge: 9 lagar (Arbeidsmiljøloven, Ferieloven, Likestillings- og diskrimineringsloven,
Arbeidstvistloven, Allmenngjøringsloven, Statsansatteloven, Permitteringslønnsloven, Lønnsgarantiloven och Yrkesskadeforsikringsloven). Tyskland: 11 lagar
(KSchG, BUrlG, ArbZG, TzBfG, AGG, ArbSchG, BetrVG, EntgFG, MuSchG, BEEG och NachwG).

Synkronisera med `.venv\Scripts\python.exe scripts/sync_sources.py --norwegian --german --spanish`.
Kommandot skriver till konfigurerad Firestore och kräver skrivbehörighet.
Källor: https://api.lovdata.no/om-api-tjenesten/ (Stiftelsen Lovdata, NLOD 2.0)
och https://www.gesetze-im-internet.de/ (XML-paket per lag).
Norska paragrafnummer behålls, t.ex. `section="15-7"`; tyska t.ex. `section="1a"`.
Källspråk är `nb` respektive `de`. Sök på källspråket; översättning garanteras inte.
Prod synkroniserades 2026-09-19: 425 norska och 405 tyska paragrafer,
20 lagar totalt, inga rapporterade synkfel. Antalen kan ändras vid senare synk.
Katalogen är avgränsad, inte fullständig nationell arbetsrätt. Norska traktatbilagor
med artikelnummer och tyska bilagor ingår inte i paragrafindexet.
Spanien: 7 BOE-lagar – Estatuto de los Trabajadores, Prevención de Riesgos Laborales,
Libertad Sindical, Igualdad efectiva de mujeres y hombres, Trabajo a distancia,
Ley de Empleo samt Inspección de Trabajo y Seguridad Social.
370 artiklar importerades 2026-09-19. Källspråk `es`, källa https://www.boe.es/datosabiertos/.
Ange BOE-ID (t.ex. BOE-A-2015-11430), `jurisdiction="ES"` och artikelnummer (t.ex. `38`).
Senaste publicerade version som trätt i kraft väljs per numrerad artikel. Framtida
versioner, upphävda artiklar, bilagor och kompletterande/övergångsbestämmelser ingår inte.
Konsoliderade BOE-texter är informativa, utan officiell rättslig giltighet; kontrollera originalet.
Danmark och Finland har adaptrar men inga indexerade paragrafer vid denna verifiering.
Webbgränssnittet är svenska/engelska; lagarnas källspråk är inte gränssnittsöversättningar.
Beräkningar, praxis, kollektivavtal och HR-mallar stöds fortfarande endast för Sverige.
`get_legal_coverage` anger faktisk paragrafmängd och tillgänglighet per land,
utifrån databasen. Källfel rapporteras som driftfel, inte som en tom lagdatabas.
Cacheuppdateringar samordnas inom varje process för att undvika dubbla inläsningar.
Efter extern synk uppdateras serverns lagcache inom 60 sekunder utan omstart.
Laguppslag läser och cachelagrar endast efterfrågat land; täckningsantal hämtas med
Firestore-aggregat i stället för att läsa hela lagkorpusen.
Synken publicerar varje lag atomiskt: paragrafer, inaktivering, metadata, synkstatus och
cache_versions/statutes ingår i samma Firestore-transaktion. Vid fel behålls tidigare lagtext.
Högst 447 nya paragrafer, 450 skrivningar totalt och 7 MB JSON för nya rader tillåts per lag;
större lagar nekas utan delpublicering och kräver en separat versionslagringslösning.
Cacheversionen kontrolleras efter 60 sekunder. Oförändrad version återanvänder cachen;
full inläsning sker senast efter 300 sekunder även för äldre skrivvägar utan versionsmarkör.
Sökindex förberäknas per land/språk och cachesnapshot (högst 16 kombinationer).
Lagtextsökning accepterar 1–2000 tecken och limit 1–50; ogiltiga värden nekas före databasanrop.
Tyska paragrafer med enbart (weggefallen)/(aufgehoben) indexeras inte. Fyra tidigare
poster är inaktiverade, inte raderade; Tyskland omfattar därefter 405 indexerade paragrafer.
Synken kontrollerar alla skrivningar, fortsätter med nästa lag vid källfel och markerar
borttagna paragrafer som inaktiva (återställningsbara), inte som gällande sökträffar.
Embedding-provider och modell ingår i synkhashen; providerbyte kräver omindexering av
hela korpusen. `EMBEDDING_PROVIDER=mock` använder alltid lokal beräkning även om API-nycklar
finns. OpenAI/Gemini ger fel vid saknad nyckel eller API-fel, utan tyst byte till mock.


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
   - Säkerställ att hela den svenska kärnkatalogen behåller 100% integritet utan trunkering eller dubbletter; antalet följer aktuell källversion.

3. **Säkerhetsstandarder**:
   - Använd konstanttidsjämförelse (`hmac.compare_digest`) vid validering av API-nycklar.
   - Tillämpa sliding window rate limiting.
   - Logga strukturerade JSON-händelser via Cloud Logging.
   - Behåll icke-root användare (`appuser` UID 10001) i Dockerfile.

4. **Officiella Källor & Prejudikat**:
   - Håll domstolspraxis synkroniserad med Arbetsdomstolen (AD) och officiella portaler (Riksdagen, Retsinformation, Finlex, Försäkringskassan, DO, SCB).

5. **Dokumentations- & Instruktionssynkronisering (Strikthet)**:
   - Om ändringar görs i infrastruktur, driftsättningskommandon, miljövariabler, domäner/endpoints eller regler i någon av filerna (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `CODEX.md` eller `README.md`), **måste samtliga dessa 5 filer uppdateras samtidigt** så att alla AI-agenter och modeller alltid är 100% i synk.

