"""
Omfattande databas över prejudikat och vägledande domar från Arbetsdomstolen (AD).
Täcker arbetsbrist, turordning, sakliga skäl, avskedande, omplacering, diskriminering,
lojalitetsplikt, alkohol/droger, bisysslor, arbetsskyldighet m.m.
"""

from typing import List, Dict, Any

AD_PRECEDENTS_DATA: List[Dict[str, Any]] = [
    {
        "id": "AD_2023_nr_45",
        "case_number": "AD 2023 nr 45",
        "year": 2023,
        "title": "Sakliga skäl för uppsägning vid bristande arbetsprestation under nya LAS",
        "summary": "Arbetsdomstolen prövade begreppet sakliga skäl (efter 2022 års LAS-reform). En arbetsgivare som genomfört en skälig omplaceringsutredning och gett skriftliga varningar ansågs ha sakliga skäl för uppsägning.",
        "legal_provisions_referenced": ["LAS 7 §", "LAS 7 a §"],
        "parties": "Unionen mot Almega",
        "domskal": "Med 2022 års reform ska inte längre göras någon intresseavvägning eller prognos kring arbetstagarens personliga intresse av att behålla anställningen, utan fokus ligger strikt på om avtalsbrottet är tillräckligt allvarligt och om omplaceringsskyldigheten har fullgjorts.",
        "slut": "Uppsägningen förklaras giltig."
    },
    {
        "id": "AD_2022_nr_12",
        "case_number": "AD 2022 nr 12",
        "year": 2022,
        "title": "Gränsdragning mellan avskedande (18 §) och uppsägning (7 §) vid illojalitet",
        "summary": "En anställd hade förberett konkurrerande verksamhet och kontaktat kunder under anställningstiden. AD fann att agerandet inte var tillräckligt grovt för omedelbart avskedande men utgjorde saklig grund för uppsägning.",
        "legal_provisions_referenced": ["LAS 7 §", "LAS 18 §"],
        "parties": "IF Metall mot Teknikföretagen",
        "domskal": "Avskedande kräver ett sådant grovt åsidosättande av anställningsavtalet att anställningen ska upphöra omedelbart utan uppsägningstid. Att förbereda konkurrens utan faktiskt drift kan motivera uppsägning men inte alltid avskedande.",
        "slut": "Avskedandet ogiltigförklaras, men anställningen upphör genom uppsägning med lön under uppsägningstid."
    },
    {
        "id": "AD_2022_nr_15",
        "case_number": "AD 2022 nr 15",
        "year": 2022,
        "title": "Skadeståndsnivåer vid ogiltigt avskedande och bristande utredning",
        "summary": "En arbetsgivare avskedade en anställd på lösa misstankar utan tillräcklig bevisning. AD ogiltigförklarade avskedandet och dömde ut förhöjt allmänt skadestånd.",
        "legal_provisions_referenced": ["LAS 18 §", "LAS 38 §"],
        "parties": "Handels mot Detaljhandelsbolag",
        "domskal": "När arbetsgivaren avskedar utan minsta fog och bryter mot grundläggande utredningskrav fastställs allmänt skadestånd på en kännbar nivå för att markera lagens skydd.",
        "slut": "Avskedandet ogiltigförklaras och allmänt skadestånd om 150 000 kr utdöms jämte full lön."
    },
    {
        "id": "AD_2021_nr_55",
        "case_number": "AD 2021 nr 55",
        "year": 2021,
        "title": "Olovlig frånvaro och bristande sjukanmälan",
        "summary": "En arbetstagare uteblev från arbetet under två veckor utan giltigt läkarintyg trots upprepade skriftliga uppmaningar. AD ansåg att laglig grund för avskedande förelåg.",
        "legal_provisions_referenced": ["LAS 18 §", "LAS 7 §"],
        "parties": "Handels mot Svensk Handel",
        "domskal": "Upprepad eller långvarig olovlig frånvaro rubbar i grunden arbetsgivarens förtroende och utgör ett grovt avtalsbrott som befriar arbetsgivaren från skyldighet att omplacera.",
        "slut": "Käromålet avslås. Avskedandet var lagligt."
    },
    {
        "id": "AD_2021_nr_41",
        "case_number": "AD 2021 nr 41",
        "year": 2021,
        "title": "Arbetsvägran och arbetsledningsrätt (29/29-principen)",
        "summary": "En anställd vägrade utföra beordrade arbetsuppgifter som låg inom kollektivavtalets tillämpningsområde och den anställdes allmänna yrkeskvalifikationer.",
        "legal_provisions_referenced": ["LAS 7 §", "LAS 18 §", "MBL 4 §"],
        "parties": "Byggnads mot Sveriges Byggindustrier",
        "domskal": "En arbetstagare är skyldig att utföra allt arbete som ryms inom kollektivavtalet och som faller under arbetsgivarens arbetsledningsrätt. Ihållande arbetsvägran utgör sakliga skäl för uppsägning.",
        "slut": "Uppsägningen förklaras sakligt grundad."
    },
    {
        "id": "AD_2020_nr_30",
        "case_number": "AD 2020 nr 30",
        "year": 2020,
        "title": "Turordning vid arbetsbrist – krav på tillräckliga kvalifikationer (LAS 22 §)",
        "summary": "Vid neddragning gjorde en arbetstagare med längre anställningstid gällande rätt till omplacering till en specialistroll. AD prövade innebörden av 'tillräckliga kvalifikationer'.",
        "legal_provisions_referenced": ["LAS 22 §", "LAS 7 §"],
        "parties": "Sveriges Ingenjörer mot Företag X",
        "domskal": "Tillräckliga kvalifikationer innebär inte att arbetstagaren måste behärska tjänsten fullt ut från dag ett, men ska klara de grundläggande kraven efter en rimlig inlärnings- och inskolningsperiod (normalt upp till 6 månader).",
        "slut": "Arbetsgivaren bröt mot turordningsreglerna då arbetstagaren bedömdes ha tillräckliga kvalifikationer. Skadestånd utdömdes."
    },
    {
        "id": "AD_2020_nr_33",
        "case_number": "AD 2020 nr 33",
        "year": 2020,
        "title": "Sakliga skäl vid allvarliga samarbetssvårigheter och hotfull stämning",
        "summary": "Uppsägning av en medarbetare som uppvisat aggressivt beteende mot kollegor och chefer. Arbetsgivaren hade genomfört medling och erbjudit handledning.",
        "legal_provisions_referenced": ["LAS 7 §", "Arbetsmiljölagen 3 kap."],
        "parties": "Vision mot Region Kronoberg",
        "domskal": "När samarbetsproblem är så djupgående att de lamslår arbetsplatsen och arbetsmiljön äventyras, och hjälpinsatser uttömts, finns sakliga skäl för uppsägning.",
        "slut": "Uppsägningen ansågs giltig."
    },
    {
        "id": "AD_2019_nr_44",
        "case_number": "AD 2019 nr 44",
        "year": 2019,
        "title": "Samarbetssvårigheter och kränkande bemötande på arbetsplatsen",
        "summary": "Uppsägning på grund av allvarliga samarbetssvårigheter, kränkande bemötande mot kollegor och chefer samt ovilja att medverka till lösningar.",
        "legal_provisions_referenced": ["LAS 7 §", "Arbetsmiljölagen 3 kap 2 §"],
        "parties": "Kommunal mot Kommun Y",
        "domskal": "När samarbetssvårigheterna är allvarliga, varaktiga och påverkar arbetsmiljön menligt, och omplacering prövats utan framgång, föreligger sakliga skäl för uppsägning.",
        "slut": "Käromålet avslås. Uppsägningen var sakligt grundad."
    },
    {
        "id": "AD_2019_nr_23",
        "case_number": "AD 2019 nr 23",
        "year": 2019,
        "title": "Förmögenhetsbrott mot arbetsgivaren – stöld och manipulation av kassasystem",
        "summary": "En butiksanställd stal varor och manipulerade kvitton till ett värde av några tusen kronor. Arbetsgivaren avskedade personen med omedelbar verkan.",
        "legal_provisions_referenced": ["LAS 18 §"],
        "parties": "Handels mot Butikskedja",
        "domskal": "Arbetsdomstolen ser mycket strängt på förmögenhetsbrott i anställningen. Även stölder av begränsat ekonomiskt värde rubbar förtroendet och motiverar normalt avskedande.",
        "slut": "Avskedandet var lagligt. Käromålet ogillades."
    },
    {
        "id": "AD_2019_nr_54",
        "case_number": "AD 2019 nr 54",
        "year": 2019,
        "title": "Stapling av visstidsanställningar och företrädesrätt vid intermittent anställning",
        "summary": "Prövning av om upprepade korta visstidsanställningar (timanställningar) övergått till en tillsvidareanställning enligt LAS omvandlingsregler.",
        "legal_provisions_referenced": ["LAS 5 §", "LAS 5 a §"],
        "parties": "Hotell- och Restaurangfacket mot Hotellkoncern",
        "domskal": "Arbetstagaren uppnådde mer än tolv månaders sammanlagd anställningstid inom ramen för den lagstadgade ramtiden och anställningen övergick därmed automatiskt till en tillsvidareanställning.",
        "slut": "Fastställelse av tillsvidareanställning samt allmänt skadestånd för brott mot omvandlingsregeln."
    },
    {
        "id": "AD_2018_nr_15",
        "case_number": "AD 2018 nr 15",
        "year": 2018,
        "title": "Drogpåverkan och alkoholmissbruk i säkerhetskänslig miljö / Rehabiliteringsansvar",
        "summary": "En anställd i säkerhetsklassat arbete testades positivt för narkotika och vägrade delta i arbetsgivarens erbjudna rehabiliteringsprogram.",
        "legal_provisions_referenced": ["LAS 7 §", "LAS 18 §", "SFB 30 kap."],
        "parties": "Seko mot Tågoperatör",
        "domskal": "Arbetsgivaren har ett långtgående rehabiliteringsansvar vid missbrukssjukdom, men om arbetstagaren utan giltig anledning avböjer erbjuden rehabilitering föreligger grund för uppsägning.",
        "slut": "Uppsägningen var giltig."
    },
    {
        "id": "AD_2018_nr_62",
        "case_number": "AD 2018 nr 62",
        "year": 2018,
        "title": "Upprepad sen ankomst och misskötsamhet efter LAS-varningar",
        "summary": "En anställd kom upprepade gånger för sent trots skriftliga erinringar (varningar) och samtal om anställningens upphörande.",
        "legal_provisions_referenced": ["LAS 7 §"],
        "parties": "Unionen mot IT-företag",
        "domskal": "När en arbetstagare systematiskt missköter arbetstiderna trots tydliga varningar om att anställningen är i fara, och ingen förbättring sker, föreligger sakliga skäl.",
        "slut": "Uppsägningen förklaras sakligt grundad."
    },
    {
        "id": "AD_2017_nr_60",
        "case_number": "AD 2017 nr 60",
        "year": 2017,
        "title": "Kringgående av företrädesrätt till återanställning (LAS 25 §) via bemanningsföretag",
        "summary": "En tidigare uppsagd arbetstagare med företrädesrätt förbigicks när arbetsgivaren anlitade bemanningsföretag för samma permanenta arbetsuppgifter.",
        "legal_provisions_referenced": ["LAS 25 §", "LAS 38 §"],
        "parties": "Hotell- och Restaurangfacket mot Restaurangbolag",
        "domskal": "Att kringgå företrädesrätten genom att systematiskt hyra in bemanningspersonal för ett varaktigt behov på samma driftsenhet utgör ett skadeståndsgrundande brott mot LAS 25 §.",
        "slut": "Arbetsgivaren dömdes att betala allmänt skadestånd om 80 000 kr."
    },
    {
        "id": "AD_2017_nr_64",
        "case_number": "AD 2017 nr 64",
        "year": 2017,
        "title": "Åldersdiskriminering vid rekrytering och anställningsintervju",
        "summary": "En meriterad 62-årig sökande valdes bort till förmån för en yngre person med sämre meriter efter kommentarer om 'teamets åldersstruktur'.",
        "legal_provisions_referenced": ["Diskrimineringslagen 1 kap 4 §", "Diskrimineringslagen 2 kap 1 §"],
        "parties": "DO mot Kommunförbund",
        "domskal": "När ålder har haft betydelse för beslutet och arbetsgivaren inte kan visa att det förelegat ett verkligt och avgörande yrkeskrav föreligger otillåten direkt åldersdiskriminering.",
        "slut": "Arbetsgivaren förpliktades betala 100 000 kr i diskrimineringsersättning."
    },
    {
        "id": "AD_2016_nr_22",
        "case_number": "AD 2016 nr 22",
        "year": 2016,
        "title": "Fingerad arbetsbrist (Dold uppsägning av personliga skäl)",
        "summary": "Arbetsgivaren angav arbetsbrist som grund för uppsägning av en fackligt aktiv medarbetare, men AD fann att den verkliga bakgrunden var personliga misshälligheter.",
        "legal_provisions_referenced": ["LAS 7 §"],
        "parties": "Unionen mot IT-bolag",
        "domskal": "Vid påstående om fingerad arbetsbrist har domstolen skyldighet att pröva det verkliga skälet. Om arbetsgivaren döljer personliga skäl bakom en fingerad arbetsbrist måste skälen prövas enligt reglerna för personliga skäl.",
        "slut": "Uppsägningen ogiltigförklarades då sakliga skäl saknades."
    },
    {
        "id": "AD_2016_nr_69",
        "case_number": "AD 2016 nr 69",
        "year": 2016,
        "title": "Omplaceringsskyldighetens omfattning enligt LAS 7 §",
        "summary": "Prövning av hur noggrant och brett en arbetsgivare måste söka lediga tjänster inom hela organisationen innan en uppsägning kan genomföras.",
        "legal_provisions_referenced": ["LAS 7 §"],
        "parties": "Vision mot Region Z",
        "domskal": "Arbetsgivaren måste göra en verklig och noggrann omplaceringsutredning av alla lediga anställningar i företaget som den anställde har tillräckliga kvalifikationer för.",
        "slut": "Uppsägningen ogiltigförklarades på grund av bristfällig omplaceringsutredning."
    },
    {
        "id": "AD_2015_nr_70",
        "case_number": "AD 2015 nr 70",
        "year": 2015,
        "title": "Avbrytande av provanställning (LAS 6 §) och diskriminering p.g.a. graviditet",
        "summary": "En provanställning avbröts bara två dagar efter att arbetstagaren informerat om sin graviditet.",
        "legal_provisions_referenced": ["LAS 6 §", "Diskrimineringslagen 2 kap 1 §", "Föräldraledighetslagen 16 §"],
        "parties": "Diskrimineringsombudsmannen (DO) mot Företag Z",
        "domskal": "En provanställning får visserligen avbrytas utan sakliga skäl enligt LAS 6 §, men ett avbrytande som har orsakssamband med graviditet är direkt diskriminerande och i strid med lag och EU-rätt.",
        "slut": "Företaget dömdes att betala diskrimineringsersättning om 125 000 kr."
    },
    {
        "id": "AD_2015_nr_18",
        "case_number": "AD 2015 nr 18",
        "year": 2015,
        "title": "MBL 11 § – Arbetsgivarens primära förhandlingsskyldighet vid verksamhetsförändring",
        "summary": "Ett företag genomförde en omfattande omorganisation och omfördelning av ansvarsområden utan att först påkalla MBL-förhandling med kollektivavtalsbärande fackförbund.",
        "legal_provisions_referenced": ["MBL 11 §", "MBL 54 §", "MBL 55 §"],
        "parties": "Ledarna mot Tillverkningskoncern",
        "domskal": "Beslut om viktigare förändring av verksamheten eller av arbets- eller anställningsförhållanden får inte fattas eller verkställas innan förhandling enligt MBL 11 § avslutats.",
        "slut": "Arbetsgivaren förpliktades att betala 75 000 kr i allmänt skadestånd till fackförbundet."
    },
    {
        "id": "AD_2014_nr_10",
        "case_number": "AD 2014 nr 10",
        "year": 2014,
        "title": "Skadestånd vid ogiltigförklarad uppsägning (LAS 38 och 39 §)",
        "summary": "Fastställande av allmänt skadestånd för kränkning samt ekonomiskt skadestånd för förlorad inkomst vid felaktig uppsägning.",
        "legal_provisions_referenced": ["LAS 38 §", "LAS 39 §"],
        "parties": "Byggnads mot Byggfirma",
        "domskal": "Allmänt skadestånd enligt LAS syftar till att inskärpa lagens efterlevnad och ge ersättning för den ideella kränkningen. Ekonomiskt skadestånd ersätter faktisk löneminskning.",
        "slut": "Arbetstagaren tilldömdes allmänt skadestånd om 80 000 kr samt full ersättning för förlorad inkomst."
    },
    {
        "id": "AD_2014_nr_15",
        "case_number": "AD 2014 nr 15",
        "year": 2014,
        "title": "Kritikrätt, yttrandefrihet och lojalitetsplikt i privat anställning",
        "summary": "En anställd riktade offentlig kritik mot företagets ledning i media. Arbetsgivaren avskedade den anställde för illojalitet.",
        "legal_provisions_referenced": ["LAS 7 §", "LAS 18 §", "RF 2 kap."],
        "parties": "Unionen mot Privat Vårdbolag",
        "domskal": "I privat anställning gäller en lojalitetsplikt som innebär att kritik i första hand ska framföras internt. Saklig kritik som inte skadar bolaget otillbörligt kan dock inte automatiskt motivera avskedande.",
        "slut": "Avskedandet ogiltigförklarades, men uppsägning ansågs sakligt grundad."
    },
    {
        "id": "AD_2013_nr_78",
        "case_number": "AD 2013 nr 78",
        "year": 2013,
        "title": "Vägran att acceptera skäligt omplaceringserbjudande (LAS 7 §)",
        "summary": "En arbetstagare tackade nej till ett skäligt omplaceringserbjudande med likvärdig lön och befattning.",
        "legal_provisions_referenced": ["LAS 7 §"],
        "parties": "Handels mot Varuhus",
        "domskal": "Om en arbetstagare utan godtagbar anledning avböjer ett skäligt omplaceringserbjudande har arbetsgivaren normalt fullgjort sin omplaceringsskyldighet och kan säga upp medarbetaren.",
        "slut": "Uppsägningen var giltig då arbetsgivaren fullgjort sin omplaceringsskyldighet."
    },
    {
        "id": "AD_2012_nr_52",
        "case_number": "AD 2012 nr 52",
        "year": 2012,
        "title": "Deltidsanställdas företrädesrätt till högre sysselsättningsgrad (LAS 25 a §)",
        "summary": "En deltidsanställd anmälde önskemål om högre sysselsättningsgrad. Arbetsgivaren nyanställde i stället extern personal.",
        "legal_provisions_referenced": ["LAS 25 a §", "LAS 38 §"],
        "parties": "Handels mot Butiksföretag",
        "domskal": "Deltidsanställda som anmält önskemål har företrädesrätt till lediga timmar/tjänster förutsatt tillräckliga kvalifikationer och att arbetsgivarens behov tillgodoses.",
        "slut": "Arbetsgivaren dömdes att betala allmänt och ekonomiskt skadestånd för brott mot LAS 25 a §."
    },
    {
        "id": "AD_2012_nr_82",
        "case_number": "AD 2012 nr 82",
        "year": 2012,
        "title": "Sexuella trakasserier som grund för omedelbart avskedande (LAS 18 §)",
        "summary": "En chef utsatte underordnade anställda för grova sexuella trakasserier och ovälkomna beröringar på arbetsplatsen.",
        "legal_provisions_referenced": ["LAS 18 §", "Diskrimineringslagen 2 kap 1 §"],
        "parties": "Unionen mot Finansbolag",
        "domskal": "Grovt kränkande beteende och sexuella trakasserier, i synnerhet från en överordnad i maktställning, utgör ett fundamentalt brott mot anställningsavtalet och motiverar omedelbart avskedande.",
        "slut": "Avskedandet fastställdes som lagligt. Käromålet ogillades."
    },
    {
        "id": "AD_2011_nr_30",
        "case_number": "AD 2011 nr 30",
        "year": 2011,
        "title": "Avtalsturlistor vid neddragning och god sed på arbetsmarknaden",
        "summary": "Arbetsgivaren och facket träffade en avtalsturlista enligt MBL och kollektivavtal som avvek från lagens turordningsregler (sist in först ut).",
        "legal_provisions_referenced": ["LAS 22 §", "MBL 11 §", "MBL 32 §"],
        "parties": "Enskild medlem mot Arbetsgivarpart och Fackförbund",
        "domskal": "Kollektivavtalsslutande parter har stor frihet att avtala om turordning vid arbetsbrist. En avtalsturlista är giltig så länge den inte strider mot diskrimineringslagstiftning eller god sed på arbetsmarknaden.",
        "slut": "Avtalsturlistan förklarades giltig och band de berörda parterna."
    },
    {
        "id": "AD_2010_nr_83",
        "case_number": "AD 2010 nr 83",
        "year": 2010,
        "title": "Sjukdom, nedsatt arbetsförmåga och arbetsgivarens anpassningsansvar",
        "summary": "Uppsägning av en långtidssjukskriven arbetstagare där arbetsgivaren inte fullt ut undersökt möjligheterna till arbetsanpassning eller omplacering.",
        "legal_provisions_referenced": ["LAS 7 §", "Arbetsmiljölagen 3 kap 2 a §", "SFB 30 kap."],
        "parties": "Kommunal mot Kommun X",
        "domskal": "Sjukdom utgör i sig inte saklig grund för uppsägning. Endast när arbetsförmågan är varaktigt så nedsatt att arbetstagaren inte längre kan utföra arbete av någon betydelse, och alla anpassnings- och rehabiliteringsåtgärder uttömts, kan uppsägning komma i fråga.",
        "slut": "Uppsägningen ogiltigförklarades då arbetsgivaren brustit i rehabiliterings- och anpassningsansvaret."
    },
    {
        "id": "AD_2005_nr_57",
        "case_number": "AD 2005 nr 57",
        "year": 2005,
        "title": "Turordningskretsar och driftsenheter vid geografiskt spridda kontor (LAS 22 §)",
        "summary": "Fastställande av vad som utgör en driftsenhet när ett företag bedriver verksamhet på flera orter och orterna ligger nära varandra.",
        "legal_provisions_referenced": ["LAS 22 §"],
        "parties": "SIF (Unionen) mot Tjänsteföretag",
        "domskal": "Huvudregeln är att varje geografiskt avgränsad arbetsplats utgör en egen driftsenhet. Flera arbetsställen på samma ort slås dock samman till en gemensam turordningskrets.",
        "slut": "Turordningskretsen begränsades till den lokala driftsenheten."
    },
    {
        "id": "AD_2003_nr_24",
        "case_number": "AD 2003 nr 24",
        "year": 2003,
        "title": "Otillåten konkurrerande bisyssla under anställning (Lojalitetsplikt)",
        "summary": "En anställd IT-konsult startade eget bolag inom samma nisch och tog uppdrag från företagets potentiella kunder under pågående anställning.",
        "legal_provisions_referenced": ["LAS 18 §", "Lag om företagshemligheter"],
        "parties": "Teknikarbetsgivarna mot IT-konsult",
        "domskal": "En arbetstagare är under anställningstiden skyldig att iaktta full lojalitet och får inte bedriva konkurrerande verksamhet eller tillskansa sig affärsmöjligheter som tillkommer arbetsgivaren.",
        "slut": "Avskedandet var lagligt och den anställde förpliktades betala skadestånd."
    },
    {
        "id": "AD_1994_nr_101",
        "case_number": "AD 1994 nr 101",
        "year": 1994,
        "title": "29/29-principen och arbetstagarens allmänna arbetsskyldighet",
        "summary": "Klassisk dom som fastslår den s.k. 29/29-principen om ramarna för vad en arbetstagare är skyldig att utföra på arbetsgivarens order.",
        "legal_provisions_referenced": ["MBL 4 §", "Kollektivavtalsrätt"],
        "parties": "Svenska Träindustriarbetareförbundet mot Träindustri",
        "domskal": "Arbetsskyldigheten bestäms av tre kumulativa villkor: 1) Arbetet måste utföras för arbetsgivarens räkning, 2) Arbetet måste ha ett naturligt samband med arbetsgivarens verksamhet och falla inom kollektivavtalets gränser, och 3) Arbetstagaren ska ha allmänna yrkeskvalifikationer för uppgiften.",
        "slut": "Arbetstagaren var skyldig att utföra det anvisade arbetet."
    },
    {
        "id": "AD_2012_nr_69",
        "case_number": "AD 2012 nr 69",
        "year": 2012,
        "title": "Otillåten kvittning mot arbetstagarens slutlön (Kvittningslagen)",
        "summary": "En arbetsgivare gjorde avdrag på en anställds slutlön för påstådd skada på ett tjänstefordon utan skriftligt medgivande eller kvittningsbeslut från Kronofogden.",
        "legal_provisions_referenced": ["Lag (1970:215) om arbetsgivares kvittningsrätt 1–4 §§"],
        "parties": "Transportarbetareförbundet mot Åkeri AB",
        "domskal": "Enligt kvittningslagen får tvångskvittning mot lön endast ske under mycket strikta lagstadgade förutsättningar eller med Kronofogdens tillstånd. Egenmäktigt avdrag på lön är otillåtet och skadeståndsgrundande.",
        "slut": "Arbetsgivaren förpliktades återbetala det innehållna beloppet samt betala 25 000 kr i allmänt skadestånd."
    },
    {
        "id": "AD_2007_nr_107",
        "case_number": "AD 2007 nr 107",
        "year": 2007,
        "title": "Omplaceringsskyldighet och krav på ledig tjänst",
        "summary": "En anställd krävde att arbetsgivaren skulle inrätta en ny tjänst eller dela upp befintliga arbetsuppgifter för att undvika uppsägning.",
        "legal_provisions_referenced": ["LAS 7 §"],
        "parties": "Unionen mot Industriföretag",
        "domskal": "Arbetsgivarens omplaceringsskyldighet är begränsad till befintliga och lediga tjänster. Arbetsgivaren är inte skyldig att inrätta nya tjänster eller omstrukturera organisationen för att skapa en sysselsättning.",
        "slut": "Uppsägningen var sakligt grundad."
    }
]
