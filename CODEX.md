# CODEX.md - OpenAI Codex, ChatGPT & Copilot Guide for MCP-LAS

Detta dokument beskriver arkitektur, driftsättning, miljö och integrationsriktlinjer för **OpenAI Codex**, **ChatGPT Custom GPTs**, **GitHub Copilot** och OpenAI-drivna utvecklingsagenter.

---

## 🏛️ Systemöversikt & Infrastruktur

MCP-LAS är ett **Model Context Protocol (MCP)**-system för nordisk arbetsrätt (Sverige, Danmark, Finland), rättspraxis (Arbetsdomstolen), kollektivavtal (17 CBA:er) och HR-verktyg.

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

```powershell
# Driftsätt Backend till Cloud Run
gcloud run deploy mcp-las `
  --source . `
  --project=paygap-prod `
  --region=europe-west3 `
  --allow-unauthenticated

# Driftsätt Frontend/Hosting till Firebase
firebase deploy --only hosting:mcp-novro --project=paygap-prod
```

---

## ⚙️ Miljövariabler (`.env`)

```ini
FIREBASE_PROJECT_ID=paygap-prod
FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
USE_FIRESTORE_EMULATOR=false
PORT=8080
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

