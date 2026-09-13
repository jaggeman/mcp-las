# Novro Subdomän & Loopia DNS Setup (`las.novro.se`)

Denna dokumentation beskriver den fullständiga konfigurationen för att driva MCP LAS under Novro-varumärket med subdomänen **`las.novro.se`**.

---

## 🏛️ Infrastrukturöversikt

| Egenskap | Konfiguration |
| :--- | :--- |
| **GCP / Firebase Projekt** | `paygap-prod` (Novro Prod, nummer `453511359123`) |
| **Cloud Run Service** | `mcp-las` i region `europe-west3` |
| **Firebase Hosting Site** | `mcp-novro` (`https://mcp-novro.web.app`) |
| **Anpassad Subdomän** | `las.novro.se` |
| **MCP Endpoint** | `https://las.novro.se/mcp` |
| **DNS-leverantör** | **Loopia** (`novro.se`) |

---

## 🛠️ Loopia DNS Konfigurationsguide (Steg-för-steg)

Följ dessa steg i **Loopia Kundzon** för att koppla `las.novro.se` till Firebase Hosting:

### Steg 1: Skapa subdomänen i Loopia
1. Logga in på **[Loopia Kundzon](https://customerzone.loopia.se)**.
2. Gå till **Domän och Webb** $\to$ klicka på huvuddomänen **`novro.se`**.
3. Under sektionen **Subdomäner**, klicka på **"Lägg till subdomän"**.
4. Skriv in **`las`** och spara (detta skapar `las.novro.se`).

### Steg 2: Konfigurera DNS-posten (CNAME)
1. Klicka på den nyskapade subdomänen **`las.novro.se`** i listan.
2. Välj **"DNS-editor"** (eller *Avancerade DNS-inställningar*).
3. Om det finns befintliga `A`-poster på `las.novro.se` (t.ex. Loopias standardparkerings-IP), ta bort dem.
4. Klicka på **"Lägg till post"**:
   - **Typ**: `CNAME`
   - **TTL**: `3600` (eller standard)
   - **Data / Värde**: `mcp-novro.web.app.` *(notera punkten i slutet om Loopia kräver FQDN)*
5. Spara DNS-inställningarna.

---

## 🔒 SSL & Verifiering i Firebase

1. Öppna **[Firebase Console $\to$ paygap-prod $\to$ Hosting $\to$ mcp-novro](https://console.firebase.google.com/project/paygap-prod/hosting/sites/mcp-novro)**.
2. Klicka på **"Verify"** i dialogen för `las.novro.se`.
3. Firebase kontrollerar CNAME-posten mot Loopia.
4. SSL-certifikatet (HTTPS) genereras automatiskt av Google Trust Services och förnyas löpande utan manuell handpåläggning.

---

## 🚢 Driftsättningskommandon framöver

När du gör ändringar i källkoden och vill driftsätta till Novro-miljöerna:

### 1. Bygg & Driftsätt Cloud Run (Backend & MCP)
```powershell
gcloud run deploy mcp-las --source . --project=paygap-prod --region=europe-west3 --allow-unauthenticated
```

### 2. Driftsätt Hosting (Webbplats & UI)
```powershell
firebase deploy --only hosting:mcp-novro --project=paygap-prod
```

---

## 🌍 Miljööversikt

| Miljö | Projekt | Cloud Run URL | Hosting URL / Subdomän |
| :--- | :--- | :--- | :--- |
| **Test** | `paygap-jaggeman` | `https://mcp-las-639268366595.europe-west3.run.app` | `https://paygap-jaggeman.web.app` |
| **Demo** | `paygap-demo` | `https://mcp-las-1078891371328.europe-west3.run.app` | `https://paygap-demo.web.app` |
| **Prod** | `paygap-prod` | `https://mcp-las-453511359123.europe-west3.run.app` | **`https://las.novro.se`** / `https://mcp-novro.web.app` |
