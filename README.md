# MCP LAS 🇸🇪⚖️

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
Nederländerna: 9 centrala lagar från KOOP Basiswettenbestand, inklusive Burgerlijk
Wetboek Boek 7 (arbeidsovereenkomst), Arbeidstijdenwet, Arbeidsomstandighedenwet,
Wet arbeid en zorg och Wet op de ondernemingsraden. Senaste version som trätt i kraft
väljs ur lagens manifest. Källspråk `nl`, källa https://wetten.overheid.nl/.
Storbritannien: 10 centrala lagar och förordningar från legislation.gov.uk, inklusive
Employment Rights Act 1996 (avgränsad till sections 1–145 på grund av den atomiska
publiceringsgränsen), Equality Act 2010, Working Time Regulations 1998,
National Minimum Wage Act 1998, TUPE och Agency Workers Regulations 2010.
Källspråk `en`, källa https://www.legislation.gov.uk/ och licens OGL 3.0.
Båda katalogerna är avgränsade. Bilagor indexeras inte som egna bestämmelser.
Danmark och Finland använder avgränsade arbetsrättskataloger från
Beskæftigelsesministeriet/Retsinformation respektive Finlex; faktisk mängd och
senaste lyckade synk visas av `get_legal_coverage` och `/api/coverage`.
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

## 🛠️ MCP-Verktyg (Tools) & Promptexempel

Dessa 11 intelligenta verktyg anropas automatiskt i bakgrunden av Claude, ChatGPT, Gemini eller Cursor:

| Funktion (Icke-tekniskt namn) | MCP Identifier | Vad verktyget gör | Exempel på prompt för din AI |
| :--- | :--- | :--- | :--- |
| **Exakt Lagparagraf** | `lookup_statute` | Hämtar ordagrann gällande lagtext och förarbetesnoter för specifik lag och paragraf. | *"Vad säger LAS 7 § om sakliga skäl för uppsägning?"* |
| **Lagtextsökning** | `search_labor_law` | Semantisk AI-sökning och nyckelordssökning över hela den svenska arbetsrättslagstiftningen. | *"Vilka regler gäller för dygnsvila och raster enligt Arbetstidslagen?"* |
| **Domstolspraxis & Prejudikat** | `search_case_law` | Söker bland vägledande domar från Arbetsdomstolen (AD) vid tvister, personliga skäl eller arbetsbrist. | *"Finns det några AD-domar om uppsägning p.g.a. personliga skäl och samarbetssvårigheter?"* |
| **Jämför Lag vs Avtal** | `compare_statute_vs_cba` | Ställer lagens grundregel (t.ex. LAS) sida vid sida mot tillämpligt kollektivavtals förmånligare regler. | *"Jämför uppsägningstiderna i LAS med Teknikavtalet för tjänstemän."* |
| **Avtalsundantag & Särregler** | `get_cba_exception` | Kontrollerar specifika semidispositiva avtalsundantag för uppsägningstid, övertid och semester. | *"Har Almega IT något undantag från LAS gällande uppsägningstid vid 5 års anställning?"* |
| **Räkna ut Semesterlön** | `calculate_vacation_pay` | Beräknar semesterlön & tillägg enligt Semesterlagen (16 a–b §§) vs Unionens kollektivavtal (0,8% fast / 0,5% rörlig). | *"Räkna ut mitt semestertillägg för 25 dagar med 45 000 kr i månadslön och 20 000 kr i bonus."* |
| **Avdrag för Obetald Semester** | `calculate_unpaid_vacation_deduction` | Beräknar löneavdrag vid obetalda semesterdagar (4,6% per dag) samt skuldavräkning vid förskottssemester (29 a §). | *"Hur stort löneavdrag får jag om jag tar ut 5 obetalda semesterdagar med 40 000 kr i månadslön?"* |
| **Betalda & Obetalda Dagar** | `calculate_earned_vacation_days` | Beräknar intjänade betalda vs obetalda semesterdagar baserat på anställningstid och frånvaro (SemL 7 § uppåtavrundning). | *"Jag började jobba 1 november. Hur många betalda semesterdagar har jag tjänat in till 1 april?"* |
| **Arbetsgivarintyg & A-kassa** | `get_employer_certificate_info` | Visar lagstadgad skyldighet enligt 47 § ALF och hänvisar till Sveriges a-kassors e-tjänst www.arbetsgivarintyg.nu. | *"Är min arbetsgivare skyldig att ge mig arbetsgivarintyg för a-kassa och hur görs det digitalt?"* |
| **Plan för återgång i arbete** | `get_rehabilitation_plan_info` | Rehabiliteringsplan enligt 30 kap. 6 § SFB (senast dag 30 vid &ge; 60 dgr sjukdom) samt länk till Försäkringskassans blankett FK 7459 (PDF). | *"När måste en arbetsgivare upprätta en plan för återgång i arbete och var finns blanketten (FK 7459)?"* |
| **Diskrimineringslagen & DO** | `get_discrimination_act_guide` | DO:s vägledning (do.se) om de 7 diskrimineringsgrunderna, aktiva åtgärder (årlig lönekartläggning), utredningsplikt och repressalieförbud. | *"Vilka krav ställer Diskrimineringslagen och DO på arbetsgivarens årliga lönekartläggning och aktiva åtgärder?"* |
| **Bankdagar & Löneutbetalning** | `check_bank_days_and_deadlines` | Riksbankens officiella helgdagar 2026, löneutbetalning (föregående bankdag om 25:e är helg) och fristberäkning (Lag 1930:173). | *"Vilken dag betalas lönen ut i april och december 2026 om den 25:e infaller på en helgdag?"* |
| **Turordning & Undantagsberäkning** | `calculate_redundancy_turnorder_and_exceptions` | Turordning vid arbetsbrist (LAS 22 § vs Unionens kollektivavtal), undantagsregler 1–4 inkl. procentregeln (15% / 10%), omplaceringsutredning (7 §) och sorterad turordningslista. | *"Hur många personer får arbetsgivaren undanta från turordningslistan enligt Unionens kollektivavtal vid en arbetsbrist där 20 av 100 anställda berörs?"* |
| **Skapa Turordningslista (Excel .xlsx)** | `generate_turordningslista_excel` | Genererar och laddar ner en komplett formaterad Excel-fil (.xlsx) med ID-kolumn, DATEDIF-formel för anställningsdagar, sortering och färgkodad status. | *"Skapa en turordningslista i Excel för vårt företag med följande anställda och ladda ner den."* |
| **HR-Dokumentmallar & Blanketter** | `get_hr_document_template` | Officiella svenska HR-mallar (SKR / LAS): omplaceringsutredning (7 § LAS), omplaceringserbjudande (Ja/Nej), varsel till fack (30 § LAS), underrättelse och uppsägningsbesked. | *"Ge mig en färdig mall för omplaceringsutredning enligt 7 § LAS som jag kan ladda ner och fylla i."* |

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
# Firebase-konfiguration (paygap-prod för drift)
FIREBASE_PROJECT_ID=paygap-prod
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
USE_FIRESTORE_EMULATOR=false

# Port och miljö
PORT=8080

# Tom = master-admin-vägen avstängd (rekommenderat)
MASTER_ADMIN_KEY=


# Embeddings: 'mock' (standard), 'openai' eller 'gemini'
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

### Dansk lagstiftning

Danska lagar kan synkroniseras från Retsinformations officiella öppna API med:

```powershell
python scripts/sync_sources.py --danish
```

Synkroniseringen hämtar ändrade danska lagdokument, parser `Kapitel`/`§`, sparar jurisdiktion `DK` och språk `da`, samt återanvänder hash- och versionskontrollen i Firestore. Danska träffar kan begränsas med `filters={"jurisdiction": "DK"}` i `search_labor_law`.

---

## 🔌 Anslut till MCP-klienter (Claude Desktop / Cursor)

### Alternativ A: Anslut via Molnet (Streamable HTTP — Ny modern standard)
Ingen lokal installation krävs. Använd den publika Streamable HTTP-endpointen i Claude Connector / Claude Desktop / ChatGPT:
```
https://las.novro.se/mcp
```

Konfiguration för `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "mcp-las": {
      "url": "https://las.novro.se/mcp"
    }
  }
}
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

## 🧪 Test-Driven Development (TDD) & Tester

Projektet utvecklas strikt enligt **Test-Driven Development (TDD)**:
1. **Skriv test först**: Vid varje ny funktion, beräkningsverktyg eller buggfix ska enhetstester och integrationstester skrivas i `tests/` innan implementationen påbörjas.
2. **Kör hela testsviten**: Samtliga tester måste köras och passera (`pytest tests/ -v`) före commit och deploy.
3. **Deterministisk integritet**: Chunker och laguppslagningar verifieras med `python check_coverage.py` för att säkerställa 100% täckning över den aktuella svenska kärnkatalogen.

### Kör tester
```powershell
.venv\Scripts\pytest.exe tests/ -v
.venv\Scripts\python.exe check_coverage.py
```

---

## ⚖️ Ansvarsfriskrivning (Legal Disclaimer)

> **Viktigt:** Denna MCP-server är ett öppen källkodsprojekt (Open Source) utvecklat för informations- och AI-integrationsändamål. Svar och information som tillhandahålls utgör **inte juridisk rådgivning** och ersätter inte professionell juridisk expertis, advokat eller facklig rådgivare. Skaparen friskriver sig från allt ansvar för beslut eller tolkningar som fattas med stöd av tjänsten.

---

## 🚀 Drift & Driftsättning (`las.novro.se`)

Projektet är integrerat och driftsatt mot **Novro Prod (`paygap-prod`)** i `europe-west3`.

- **Live Subdomän**: `https://las.novro.se` (Hosting-site: `mcp-novro`)
- **MCP Endpoint**: `https://las.novro.se/mcp`
- **DNS Setup Guide**: Fullständig guide för konfigurering i Loopia Kundzon finns i [`docs/deployment/novro-dns-and-subdomain-setup.md`](docs/deployment/novro-dns-and-subdomain-setup.md).

### Driftsättning

#### 1. Automatisk CI/CD (Standard för AI-agenter)
Push eller merge till `main` triggar GitHub Actions (`.github/workflows/ci.yml`), som automatiskt kör hela testsviten och driftsätter både **Cloud Run** (`mcp-las`) och **Firebase Hosting** (`mcp-novro`).

#### 2. Manuell driftsättning (CLI)

##### A. Driftsätt Backend & MCP Server (Cloud Run)
```powershell
gcloud run deploy mcp-las --source . --project=paygap-prod --region=europe-west3 --allow-unauthenticated
```

##### B. Driftsätt Webbplats & UI (Firebase Hosting)
```powershell
firebase deploy --only hosting:mcp-novro --project=paygap-prod
```

---

### Verifiera vilken kod som faktiskt kör

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

## 🤖 AI-Agenter & Synkroniseringskrav

Projektet innehåller dedikerade instruktionsfiler anpassade för olika AI-assistenter:
- **`AGENTS.md`**: Universella riktlinjer för autonoma agenter.
- **`CLAUDE.md`**: Claude Code / Claude Desktop / Anthropic.
- **`GEMINI.md`**: Google Gemini / Gems / AI Studio / Vertex AI.
- **`CODEX.md`**: OpenAI Codex / Custom GPTs / Copilot / Cursor.

> 🔄 **Viktigt (Synkroniseringskrav)**: Om ändringar görs i infrastruktur, driftsättningskommandon, miljövariabler, domäner/endpoints eller regler i någon av filerna (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `CODEX.md` eller `README.md`), **måste samtliga dessa 5 filer uppdateras samtidigt** så att alla AI-agenter och modeller alltid är 100% i synk.

---

## 📄 Licens

Öppen källkod licensierad under **[MIT License](LICENSE)**.



