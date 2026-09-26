# AI Agent Guidelines for MCP-LAS

## Mätning av svarskvalitet

`src/benchmarks/quality.py` mäter exakt land/lag/kapitel/paragraf, hit@1,
recall@5/10 och reciprocal rank. Måtten avser hämtade referenser, inte sannolikheten
att ett juridiskt svar är korrekt. Offline-regressionstester körs utan credentials
i `tests/test_quality_evaluation.py`; åtta syntetiska landsfall testar motorn, inte
ländernas juridiska täckning. Produktions-smoke nekar tomma, felaktiga och
landblandade sökresultat. Den blockerande kvalitetskontrollen har 36 granskade
källspråksfall: 22 svenska och två per övrigt land (DK, FI, NO, DE, ES, NL, GB).
Facit anger land, exakt bestämmelse, officiell referens och granskningsdatum.
Frågan om utbetalning av semesterersättning ska träffa Semesterlagen 30 §;
28 § reglerar rätten till ersättning men inte betalningsfristen. Den dagliga
produktionsövervakningen kör både `--all-countries` och `--check-search-quality`.
Varje sökträff måste ha en HTTPS-källänk till respektive lands tillåtna officiella
rättskälla. Äldre svenska rader kompletteras vid läsning med Riksdagens stabila
Open Data-länk och kommande synkar lagrar källnamn och källadress i varje paragraf.

HR-benchmarken använder endast frågan vid sökning, aldrig facit för kompletterande
uppslag. Nyckelord rapporteras separat och påverkar inte godkännande.
Det äldre HR-facit är `legacy_unverified` och kräver oberoende juridisk granskning;
fall utan referensfacit markeras ej utvärderade/ej godkända. Sänk inte gränser för
att dölja brister efter att facitläckaget tagits bort.

Positiva hårdkodade `certainty.score_pct` har ersatts med null och
`measurement=not_calibrated`; klienter måste hantera null. Källtyp och tolkningsbehov
är beskrivningar, inte uppmätt säkerhet. Felstatus kan fortfarande ha score_pct=0.
MCP ser inte klientens slutliga AI-svar. End-to-end-bedömning, granskade testfall
för samtliga länder och kalibrerad AI-bedömare återstår. Langfuse är inte installerat.
Inga produktionsfrågor eller svar skickas till en extern utvärderingstjänst.

## Säkerhet för MCP och Excel-export


Publika MCP-anrop utan nyckel delar en kvot på 60 anrop/minut.
Angiven API-nyckel måste vara giltig och aktiv för kvoten 300 anrop/minut.
Ogiltiga nycklar nekas; Firestore-nycklar kräver booleskt `is_active=true`.
Giltiga nyckeluppslag cachelagras processlokalt i högst 30 sekunder och 1000 poster;
en återkallad nyckel kan därför fortsätta fungera i högst 30 sekunder på en varm instans.
REST accepterar nycklar endast i `X-API-Key`, inte URL eller JSON-body.
MCP använder samma `X-API-Key` på transportnivå; nyckeln exponeras inte som
verktygsargument för AI-modellen. Nya nycklar har 256 bitars slump, visas en
gång och lagras endast under ett HMAC-SHA-256-ID med en serverhemlig pepper i
Secret Manager. Rånycklar får
inte lagras, listas, loggas eller användas som dokument-ID.
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
aktiverats i paygap-prod 2026-09-19 och verifierats ACTIVE. `key_requests`
har 90 dagars retention och TTL aktiverades 2026-09-26.
TTL är asynkron och påverkar inte kvoternas giltighetskontroll.
Äldre loggar utan utgångstid kräver separat granskning/gallring; de raderas inte av koden.
CI använder Workload Identity Federation, inte `GCP_SA_KEY`.
GitHub OIDC konfigurerades 2026-09-19: pool `github-mcp-las`, provider
`github-main` i projekt 453511359123. Villkoren begränsar repository-ID
1359199704, ägar-ID 209946709, main, push och `.github/workflows/ci.yml`.
GitHub-variablerna `GCP_WORKLOAD_IDENTITY_PROVIDER` och `GCP_DEPLOY_SERVICE_ACCOUNT`
är satta. Det dedikerade `mcp-las-deployer@paygap-prod.iam.gserviceaccount.com`
används för LAS-deploy; byggkontot är `mcp-las-builder`.
Veckosynken använder separat OIDC-pool `github-mcp-sync`, provider `github-sync`,
och `mcp-source-sync@paygap-prod.iam.gserviceaccount.com` med endast
`roles/datastore.user` på projektet, utan deployroller. Villkoren tillåter endast
samma repository/ägare, main och `sync-sources.yml` vid schedule/workflow_dispatch.
GitHub-variabler: `GCP_SYNC_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SYNC_SERVICE_ACCOUNT`.
Jobbet synkar Sverige, Danmark, Finland, Norge, Tyskland, Spanien, Nederländerna och Storbritannien måndagar 03:00 UTC, utan överlappande körningar.
Sverige synkas direkt på GitHub-runnern; Riksdagen-hämtning från Cloud Run misslyckades.
Danmark, Finland, Norge, Tyskland, Spanien, Nederländerna och Storbritannien körs i Frankfurt. GitHub startar Cloud Run Job `mcp-las-source-sync` i europe-west3 och väntar på resultatet.
Direkt hämtning från GitHub fick anslutningstimeout till den tyska källan; Frankfurt fungerar.
Synkkontot har även `roles/run.jobsExecutor` och `roles/run.viewer` på endast detta jobb.
CI uppdaterar jobbets image till samma digest som backend och anger flaggorna --danish --finnish --norwegian --german --spanish --dutch --british.
Jobbet använder mock-embeddings, 1 CPU/1 GiB, 1800 sekunders timeout och inga automatiska omförsök.
Ingen workflow använder längre `GCP_SA_KEY`. GitHub-hemligheten och den sista
användarhanterade nyckeln för deploykontot återkallades 2026-09-26 efter kontroll
av revisionsloggar; endast Googles systemhanterade nyckel återstår.
Excel-länkar är hemliga bearer-token med 256 bitars slump och högst 10 minuters
giltighet. Alla som har länken kan hämta filen; dela eller logga därför inte länkarna.
Filer rensas automatiskt. Cachen är processlokal: högst 32 filer, 32 MiB totalt
och 2 MiB per fil. Omstart eller kapacitetsrensning kan göra länkar ogiltiga tidigare;
vid flera instanser kan en annan instans sakna filen. Base64-exporten finns kvar.
Export accepterar högst 1000 anställda, 32 fält per anställd och 2000 tecken per fält.
Användarfält sparas som text, medan serverns DATEDIF-formler behålls.
Docker-kontexten exkluderar miljöfiler och vanliga nyckel-/credential-filer.
Cloud Run använder det dedikerade kontot `mcp-las-runtime` med endast
`roles/datastore.user`; standardkontot med Editor används inte av tjänsten.
Produktionsberoenden installeras från hash-låsta `requirements.lock`.
GitHub Actions är SHA-pinnade; CodeQL kör v4, Google-auth/setup-gcloud v3 och
setup-node v7. Dependabot, pip-audit samt CodeQL är aktiverade.
Den äldre lokala service-account-nyckeln för `mcp-las-rules` återkallades och
raderades 2026-09-26.
Cloud Run begränsas av CI till 5 instanser och concurrency 40. Uvicorns accesslogg är
avstängd eftersom Cloud Run redan skapar en requestlogg för varje HTTP-anrop.

## Europeiska laguppslag och sökning
`lookup_statute` och `search_labor_law` stöder `SE`, `DK`, `FI`, `NO`, `DE`, `ES`, `NL` och `GB`.
Norge: 9 lagar (Arbeidsmiljøloven, Ferieloven, Likestillings- og diskrimineringsloven,
Arbeidstvistloven, Allmenngjøringsloven, Statsansatteloven, Permitteringslønnsloven, Lønnsgarantiloven och Yrkesskadeforsikringsloven). Tyskland: 11 lagar
(KSchG, BUrlG, ArbZG, TzBfG, AGG, ArbSchG, BetrVG, EntgFG, MuSchG, BEEG och NachwG).

Synkronisera med `.venv\Scripts\python.exe scripts/sync_sources.py --danish --finnish --norwegian --german --spanish --dutch --british`.
Kommandot skriver till konfigurerad Firestore och kräver skrivbehörighet.
Källor: https://api.lovdata.no/om-api-tjenesten/ (Stiftelsen Lovdata, NLOD 2.0)
och https://www.gesetze-im-internet.de/ (XML-paket per lag).
Norska paragrafnummer behålls, t.ex. `section="15-7"`; tyska t.ex. `section="1a"`.
Källspråk är `nb` respektive `de`. Sök på källspråket; översättning garanteras inte.
Prod verifierades och synkroniserades 2026-09-26: 425 norska och 405 tyska paragrafer,
20 lagar totalt, inga rapporterade synkfel. Antalen kan ändras vid senare synk.
Katalogen är avgränsad, inte fullständig nationell arbetsrätt. Norska traktatbilagor
med artikelnummer och tyska bilagor ingår inte i paragrafindexet.
Spanien: 7 BOE-lagar – Estatuto de los Trabajadores, Prevención de Riesgos Laborales,
Libertad Sindical, Igualdad efectiva de mujeres y hombres, Trabajo a distancia,
Ley de Empleo samt Inspección de Trabajo y Seguridad Social.
370 artiklar verifierades i prod 2026-09-26. Källspråk `es`, källa https://www.boe.es/datosabiertos/.
Ange BOE-ID (t.ex. BOE-A-2015-11430), `jurisdiction="ES"` och artikelnummer (t.ex. `38`).
Senaste publicerade version som trätt i kraft väljs per numrerad artikel. Framtida
versioner, upphävda artiklar, bilagor och kompletterande/övergångsbestämmelser ingår inte.
Konsoliderade BOE-texter är informativa, utan officiell rättslig giltighet; kontrollera originalet.
Nederländerna: 9 centrala lagar från KOOP Basiswettenbestand, inklusive Burgerlijk
Wetboek Boek 7 (arbeidsovereenkomst), Arbeidstijdenwet, Arbeidsomstandighedenwet,
Wet arbeid en zorg och Wet op de ondernemingsraden. Senaste version som trätt i kraft
väljs ur lagens manifest. Källspråk `nl`, källa https://wetten.overheid.nl/.
Prod verifierades 2026-09-26 med 703 indexerade nederländska bestämmelser.
Storbritannien: 10 centrala lagar och förordningar från legislation.gov.uk, inklusive
Employment Rights Act 1996 (avgränsad till sections 1–145 på grund av den atomiska
publiceringsgränsen), Equality Act 2010, Working Time Regulations 1998,
National Minimum Wage Act 1998, TUPE och Agency Workers Regulations 2010.
Källspråk `en`, källa https://www.legislation.gov.uk/ och licens OGL 3.0.
Prod verifierades 2026-09-26 med 919 indexerade brittiska bestämmelser.
Båda katalogerna är avgränsade. Bilagor indexeras inte som egna bestämmelser.
Danmark och Finland använder avgränsade arbetsrättskataloger från
Beskæftigelsesministeriet/Retsinformation respektive Finlex; faktisk mängd och
senaste lyckade synk visas av `get_legal_coverage` och `/api/coverage`.
Finland hämtas från Finlex aktuella konsoliderade lagvy på `data.finlex.fi`;
ändringshistorikens ursprungliga `act/statute`-text får inte användas som gällande
lydelse. Adaptern läser den finska dokumentvyn och ignorerar parallell svensk text.
Webbgränssnittet är svenska/engelska; lagarnas källspråk är inte gränssnittsöversättningar.
Beräkningar, praxis, kollektivavtal och HR-mallar stöds fortfarande endast för Sverige.
`get_legal_coverage` anger faktisk paragrafmängd och tillgänglighet per land,
utifrån databasen. Källfel rapporteras som driftfel, inte som en tom lagdatabas.
Cacheuppdateringar samordnas inom varje process för att undvika dubbla inläsningar.
Efter extern synk uppdateras serverns lagcache inom 60 sekunder utan omstart.
Laguppslag läser och cachelagrar endast efterfrågat land; högst tre landskorpusar
hålls samtidigt i processminnet och tillhörande sökindex rensas vid avhysning.
Täckningsantal hämtas med Firestore-aggregat i stället för att läsa hela lagkorpusen.
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

Webbens juridiska information finns i `public/privacy.html` och `public/terms.html`.
Sajten använder inga analys- eller annonscookies; `mcp_lang` och `mcp_theme` lagras
endast lokalt i webbläsaren. API-ansökningar gallras efter 90 dagar. Aktiva
API-kontoposter behålls medan nyckeln är aktiv och får `expires_at` 90 dagar efter
avaktivering; Firestore TTL ska vara aktivt för `api_keys.expires_at`. Externa typsnitt
eller ikon-CDN får inte införas utan att integritetspolicyn och samtyckesbehovet granskas.


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
API_KEY_PEPPER= # krävs; sätts från Secret Manager i prod, aldrig i kod/repo

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

## Prestanda och kostnad

Firestore-versionen för lagkorpusen kontrolleras högst en gång per 60 sekunder.
En oförändrad, befintlig versionsmarkör återanvänder landets cache utan periodisk
full omläsning. Äldre data utan versionsmarkör läses om efter högst 300 sekunder.
Högst tre landskorpusar och sexton sökindex hålls per process. Embeddings
komprimeras till float32 och semantiska poäng beräknas vektoriserat per sökning.
Riksdagens dokumentcache är en trådsäker LRU-cache med högst 256 poster.

Produktions-smoketest efter backenddeploy söker som standard bara i Sverige;
den dagliga övervakningen 04:17 UTC använder `--all-countries`. CI avgör från
ändrade sökvägar om Cloud Run respektive Firebase Hosting behöver driftsättas,
så webb-, test- och dokumentationsändringar bygger inte backend i onödan.
Firebase Hosting skickar endast `/mcp`, `/mcp/**`, `/sse`, `/sse/**`,
`/api`, `/api/**` och `/health` till Cloud Run; okända skanner-URL:er
stannar i Hosting. Artifact Registry-policyn i
`.github/artifact-cleanup-policy.json` tar bort `mcp-las`-images äldre än
14 dagar men behåller alltid minst de tio senaste versionerna.

## Säkerhet efter angreppsgranskning 2026-09-26

HTTP-MCP kör stateless; OPTIONS besvaras före MCP så inga sessioner allokeras.
Webborigins begränsas till https://las.novro.se och https://mcp.novro.se.
Klienter utan Origin-header (vanliga MCP-klienter) stöds fortsatt.
API-nycklar krävs fortfarande för REST; publikt MCP behåller sin delade anonyma kvot.
Den globala kvoten skyddar kostnader men ger inte isolering mellan anonyma användare.
Formulärets proxybaserade kvot har samma begränsning; godtyckliga X-Forwarded-For
får aldrig betros. Fullständig anonym rättvisa kräver verifierad klientidentitet
eller separat edge-/botskydd, inte en klientstyrd header.
SMTP använder ssl.create_default_context() för certifikat- och värdnamnskontroll.
Riksdagens liveuppslag validerar frågelängd, dokument-ID, limit och sidnummer före nätverk.
Webbens script ligger i public/app.js; CSP tillåter inte unsafe-inline för JavaScript.
Inline CSS stöds fortfarande. /health behåller publik build_sha för deployverifiering;
commit-ID är offentlig metadata, inte en autentiseringsuppgift.
Dockerbasen är digest-pinnad och övervakas av Dependabot veckovis.

GitHub main kräver PR och godkänd Tester-kontroll, blockerar force-push/radering och
har inga bypass-aktörer. Antalet obligatoriska personliga godkännanden är noll eftersom
repot bara har en behörig användare; skyddet ersätter inte en oberoende kodgranskare.
GitHub kräver SHA-pinning och tillåter endast projektets använda Actions.
LAS använder mcp-las-deployer och mcp-las-builder i paygap-prod. Deployern får actAs
endast på runtime-, synk- och byggkontot, Run-behörighet endast på LAS-tjänsten/jobbet,
och inga Firestore-rättigheter. Firebase Hosting-admin och Cloud Build editor är
fortfarande projektroller. LAS OIDC-bindning på det äldre github-deployer har tagits
bort; andra tjänsters befintliga roller ändras inte.
CI anger --build-service-account=projects/paygap-prod/serviceAccounts/mcp-las-builder@paygap-prod.iam.gserviceaccount.com.
Firestore (default) i paygap-prod har raderingsskydd och PITR med sju dagars retention;
PITR-historiken byggs upp från aktiveringen och medför extra lagringskostnad.
