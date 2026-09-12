# DA-001: Lägg till automatiskt stöd för danska lagar

## Mål

Utöka MCP LAS så att danska arbetsrättsliga lagar kan hämtas, versionshanteras, indexeras och sökas på samma sätt som de svenska lagarna.

## Föreslagen omfattning

- Lägg till en separat dansk källadapter, exempelvis `DanishLawFetcher`.
- Använd en officiell dansk källa, i första hand Retsinformation eller annan myndighetskälla med stabilt API/exportformat.
- Modellera land och språk i lagmetadata:
  - `jurisdiction: SE|DK`
  - `language: sv|da`
  - `source_url`
  - `source_version`
  - `content_hash`
- Återanvänd den deterministiska chunkern, men skapa danska regler för kapitel, paragraf (`§`), stycken och övergångsbestämmelser.
- Indexera danska paragrafer i Firestore med separata dokument-ID:n, exempelvis `dk-...`.
- Skapa danska sökord, stoppord, stemming/synonymer och språkmedveten ranking.
- Lägg till MCP-filter för jurisdiktion och språk, exempelvis `country="DK"` eller `language="da"`.
- Inkludera danska källor i den veckovisa synkroniseringen med hash-baserad förändringskontroll.

## Första lagpaket

Börja med arbetsrättsliga kärnlagar, till exempel:

- Funktionærloven
- Ferieloven
- Lov om retsforholdet mellem arbejdsgivere og funktionærer
- Arbejdsmiljøloven
- Ligebehandlingsloven
- Lov om lønmodtageres ret til fravær fra arbejdet af særlige familiemæssige årsager

Den exakta listan ska verifieras mot aktuell officiell dansk källa innan implementation.

## Acceptanskriterier

- En dansk lag kan hämtas från en officiell källa och delas upp korrekt i paragrafer.
- Uppslag på dansk lag och paragraf fungerar, exempelvis `Ferieloven § 15`.
- Sökning kan begränsas till Danmark utan att svenska träffar blandas in.
- Synkronisering är idempotent och indexerar endast ändrade dokument.
- Tidigare versioner och käll-URL sparas för spårbarhet.
- Tester täcker chunking, språkfilter, hash-jämförelse, fel i källan och dubblettskydd.
- Svenska 477 kärnsektioner påverkas inte; `check_coverage.py` och hela testsviten passerar.
- Resultat märks tydligt som dansk rätt och innehåller ansvarsfriskrivning om jurisdiktion.

## Risker och beslut

- Källformatet kan skilja sig från svenska SFS-dokument.
- Danska lagar kan ha ändringsbekendtgørelser och historiska lydelser som kräver separat versionsmodell.
- Kollektivavtal och rättspraxis ska inte blandas in i första versionen.
- Automatisk publicering bör först ske med ändringsrapport och manuell godkännandegrind.

## Tekniska deluppgifter

1. Verifiera officiell dansk API-/exportkälla och licensvillkor.
2. Skriva tester för dansk text och gränsfall i paragrafidentifiering.
3. Implementera `DanishLawFetcher`.
4. Utöka metadata, Firestore-index och sökfilter.
5. Lägga till dansk synkronisering i veckojobbet.
6. Lägga till benchmarkfrågor på danska.
7. Dokumentera driftsättning och ändringsgranskning.
