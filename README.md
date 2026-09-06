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

