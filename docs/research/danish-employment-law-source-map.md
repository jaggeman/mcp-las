# Dansk arbejdsrätt: källkarta och täckningsplan

## Slutsats

Dansk arbetsrätt kan inte modelleras som en kopia av svensk LAS. Beskæftigelsesministeriet beskriver ett system där flera lagar ger minimirättigheter, medan många konkreta villkor regleras genom kollektivavtal. Ministeriet nämner bland annat ansættelsesbeviser, ferie, barsel, föreningsfrihet och arbetstid som allmänna lagområden, men även Funktionærloven och regler om diskriminering, vikarier, tidsbegränsad anställning och verksamhetsövergång. [Beskæftigelsesministeriet – arbetsrättsliga lagar](https://www.bm.dk/arbejdsomraader/arbejdsvilkaar/arbejdsretlige-love)

Det betyder att systemet bör ha separata källtyper och alltid märka om ett svar kommer från lag, myndighetsvägledning, rättspraxis eller kollektivavtal.

## Källhierarki

| Nivå | Källa | Användning | Synkning |
|---|---|---|---|
| 1 | [Retsinformation](https://www.retsinformation.dk/static/api.html) och [Retsinformation REST API](https://api.retsinformation.dk/) | Gällande och historiska lagar, förordningar och officiella dokument | Daglig ändringshämtning |
| 2 | [Beskæftigelsesministeriets lagöversikt](https://www.bm.dk/arbejdsomraader/arbejdsvilkaar/arbejdsretlige-love/oversigt-over-arbejdsretlige-love) | Kontrollista för arbetsrättslig täckning och ämneskategorier | Versionskontrollerad katalog |
| 2 | [Arbejdstilsynet](https://at.dk/) | Arbetstid, vila, fridagar, arbetsmiljö och tillsynsvägledning | Veckovis + förändringsdetektion |
| 2 | [STAR](https://star.dk/) och [Virk](https://virk.dk/) | Barsel, sjukdom, dagpenning, arbetsgivarprocesser och ersättning | Veckovis |
| 3 | [Arbejdsretten](https://arbejdsretten.dk/) | Arbetsrättsliga domar, fagliga voldgiftsretter och avskedigelsesnævn | Daglig/veckovis |
| 3 | [Medarbejder- og Kompetencestyrelsen/PAV](https://medst.dk/) | Statliga anställningsvillkor, cirkulär och överenskomster | Veckovis |
| 3 | [KL](https://www.kl.dk/overenskomster/) och [Danske Regioner](https://www.regioner.dk/aftaler-og-oekonomi/arbejdsgiver/aftaler-og-overenskomster/) | Kommunala och regionala avtal, personalregler och OK-material | Veckovis/vid OK-förhandling |
| 3 | [DA](https://www.da.dk/) och relevanta fackförbund | Privat sektors huvudavtal och kollektivavtal | Veckovis/avtalsbevakning |

Retsinformation erbjuder REST-hösteservice och ELI-kanaler. API:t är uttryckligen avsett för att hålla externa system uppdaterade med nya och ändrade dokument, medan ELI ger sitemap/Atom Feed för kompletterande upptäckt. [Retsinformation API-villkor](https://www.retsinformation.dk/static/api.html)

## Lagkatalog

Projektet har nu en maskinläsbar katalog i `src/data/danish_labor_law_catalog.py`. Den bygger på ministeriets officiella översikt och innehåller 30 unika områden efter att dubbletten Deltidsloven tagits bort.

### Kärna

- Funktionærloven
- Ferieloven
- Lov om ansættelsesbeviser og visse arbejdsvilkår
- Arbejdstidsloven
- Barselsloven
- Ligebehandlingsloven
- Ligelønsloven
- Forskelsbehandlingsloven
- Foreningsfrihedsloven
- Lov om tidsbegrænset ansættelse
- Virksomhedsoverdragelsesloven
- Lov om udstationering af lønmodtagere
- Lov om information og høring af lønmodtagere
- Lov om Arbejdsretten og faglige voldgiftsretter
- Lov om ligebehandlingsnævnet

### Utökad täckning

- Deltidsloven
- Vikarloven
- Barselsudligningsloven
- Helbredsoplysningsloven
- LG-loven
- Lov om mægling i arbejdsstridigheder
- Lov om lønmodtagers rätt till frånvaro av särskilda familjeskäl

### Specialiserade områden

- Europeiska företagsråd
- SE- och SCE-medarbejderinflytande
- Aktie- och teckningsrätter i anställning
- Värnplikts- och utlandsorlov
- Medhjælperloven
- reglerna efter avskaffelsen av Store Bededag
- mobil arbetskraft inom väg/järnväg

## Viktiga aktuella ämnen att indexera

1. Anställningsbevis: skriftlig information om väsentliga villkor.
2. Funktionär: uppsägning, sjuklön och avgångsersättning.
3. Ferie: 5 veckor, 2,08 dagar per månad, semesterår 1 september–31 augusti och semesterfrister. [Ferieloven](https://www.retsinformation.dk/eli/lta/2024/152)
4. Arbetstid: tidsregistrering från 1 juli 2024, 48-timmarsregeln, vila och fridagar. [Arbejdstilsynet](https://at.dk/nyheder/2024/07/regler-om-arbejdstid-og-hvileperiode/)
5. Diskriminering: kön, graviditet, ålder, funktionsnedsättning, religion, etnicitet, sexuell orientering och könsidentitet. [Forskelsbehandlingsloven](https://www.retsinformation.dk/eli/retsinfo/2024/9223) och [Ligebehandlingsloven](https://www.retsinformation.dk/eli/lta/2024/942)
6. Verksamhetsövergång: kollektivavtal och individuella villkor följer i grunden med till förvärvaren. [Virksomhedsoverdragelsesloven](https://www.retsinformation.dk/eli/lta/2002/710)
7. Barsel, sjukdom och omsorgsorlov.
8. Kollektivavtal: lön, pension, övertid, tillägg, extra ledighet och lön under barsel/sjukdom.

## Kollektivavtal är en separat datamodell

DA beskriver att ungefär tre av fyra privatanställda omfattas av kollektivavtal och att överenskomster ofta reglerar lön, pension, extra ferie, övertid och lön under barsel. För hela arbetsmarknaden anges över 80 procent täckning. [DA – överenskomster](https://www.da.dk/politik-og-analyser/overenskomst-og-arbejdsret/2024/spoergsmaal-og-svar-om-overenskomstforhandlingerne/)

Därför bör kollektivavtal inte läggas in som om de vore lagtext. Varje avtalsdokument behöver metadata för part, sektor, avtalsperiod, yrkesområde, version och avtalsstatus.

Prioriterad avtalskällor:

- Privat: DA/DI, Dansk Erhverv, HK, 3F, CO-industri och relevanta branschparter.
- Kommuner: KL:s avtalsbibliotek och OK-material.
- Regioner: Danske Regioner/RLTN och OK-portalen.
- Staten: Medarbejder- og Kompetencestyrelsen, PAV, CFU och organisationsavtal.

KL publicerar överenskommelser per yrkesområde, och Danske Regioner anger att RLTN förhandlar och tolkar regionala avtal. [KL:s avtalsportal](https://www.kl.dk/overenskomster/) [Danske Regioner](https://www.regioner.dk/aftaler-og-oekonomi/arbejdsgiver/aftaler-og-overenskomster/)

## Rättspraxis

Arbejdsretten publicerar domar och beslut från Arbejdsretten, faglige voldgiftsretter och Afskedigelsesnævnet. Den bör få en separat adapter och datamodell, inte återanvända svenska AD-fält rakt av. [Arbejdsretten](https://arbejdsretten.dk/)

Retsinformation innehåller lagar och myndighetsdokument, men inte domstolsavgöranden. Därför måste rättspraxis hämtas från Arbejdsretten och kompletterande officiella instanser.

## Teknisk rekommendation

- Behåll `RetsinformationFetcher` för lagar och ändringshöstning.
- Använd katalogen för täckningskontroll, alias och ämnesfilter.
- Lägg till `source_type`: `statute`, `guidance`, `case_law`, `collective_agreement`.
- Lägg till `valid_from`, `valid_to`, `current`, `document_type`, `authority` och `agreement_parties` i indexmetadata.
- Kör Retsinformation dagligen eftersom API:t är byggt för dagliga ändringar; kör vägledning och avtal veckovis.
- Kräv käll-URL och versions-ID i varje svar.
- Håll svensk och dansk rätt separerad genom `jurisdiction=SE|DK` och `language=sv|da`.

## Begränsningar

- Dansk lag ger inte alltid svaret på lön, pension, övertid eller fulla uppsägningsvillkor; kollektivavtal och anställningsavtal kan vara avgörande.
- Ett dokument som finns på en arbetsgivar- eller facklig webbplats är inte automatiskt en officiell rättskälla.
- Juridisk status måste lagras separat från sökrelevans.
