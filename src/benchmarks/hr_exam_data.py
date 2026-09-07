"""
Autentiska tentamens- och HR-frågor från Personalvetarprogrammet och facklig/arbetsgivar-rådgivning.
Används för att deterministiskt benchmarka och poängsätta svensk arbetsrättslig AI-precision.
Totalt 50 validerade scenarier över 6 juridiska kategorier.
"""

from typing import List, Dict, Any

HR_EXAM_BENCHMARKS: List[Dict[str, Any]] = [
    # Kategori 1: Uppsägning, Avskedande & Sakliga Skäl (1-10)
    {
        "id": "HR_01_sakliga_skal",
        "category": "Uppsägning & Sakliga Skäl",
        "question": "Vad krävs för att en uppsägning av personliga skäl ska vara giltig enligt reformerade LAS (sakliga skäl) och vilken utredning måste arbetsgivaren göra?",
        "expected_statutes": ["LAS 7 §", "LAS 7 a §"],
        "expected_ad_cases": ["AD 2023 nr 45", "AD 2022 nr 34"],
        "expected_keywords": ["sakliga skäl", "omplacering", "varning"]
    },
    {
        "id": "HR_02_avskedande_illojalitet",
        "category": "Uppsägning & Sakliga Skäl",
        "question": "En anställd har förberett konkurrerande verksamhet och kontaktat kunder under anställningstiden. Föreligger grund för omedelbart avskedande eller uppsägning?",
        "expected_statutes": ["LAS 18 §", "LAS 7 §"],
        "expected_ad_cases": ["AD 2022 nr 12", "AD 2003 nr 24"],
        "expected_keywords": ["avskedande", "grovt", "lojalitetsplikt"]
    },
    {
        "id": "HR_03_provanstallning_avbrytande",
        "category": "Uppsägning & Sakliga Skäl",
        "question": "Vilka varsel- och underrättelsefrister gäller när en arbetsgivare vill avbryta en provanställning i förtid och krävs sakliga skäl?",
        "expected_statutes": ["LAS 6 §", "LAS 31 §"],
        "expected_ad_cases": ["AD 2024 nr 41", "AD 2015 nr 70"],
        "expected_keywords": ["två veckor", "underrättelse", "provanställning"]
    },
    {
        "id": "HR_04_olovlig_franvaro",
        "category": "Uppsägning & Sakliga Skäl",
        "question": "En medarbetare uteblir från arbetet i två veckor utan giltigt läkarintyg trots skriftliga påminnelser. Föreligger laglig grund för avskedande?",
        "expected_statutes": ["LAS 18 §", "LAS 7 §"],
        "expected_ad_cases": ["AD 2021 nr 55"],
        "expected_keywords": ["olovlig frånvaro", "avskedande", "förtroende"]
    },
    {
        "id": "HR_05_tvamanadersregeln",
        "category": "Uppsägning & Sakliga Skäl",
        "question": "Hur tillämpas tvåmånadersregeln i LAS om arbetsgivaren vill åberopa en händelse som inträffat för fyra månader sedan?",
        "expected_statutes": ["LAS 7 §", "LAS 18 §"],
        "expected_ad_cases": ["AD 2020 nr 68"],
        "expected_keywords": ["två månader", "kännedom", "underrättelse"]
    },
    {
        "id": "HR_26_sarskild_visstidsanstallning_inlasning",
        "category": "Uppsägning & Sakliga Skäl",
        "question": "När övergår en särskild visstidsanställning (SÄVA) automatiskt till en tillsvidareanställning enligt 5 a § LAS?",
        "expected_statutes": ["LAS 5 a §"],
        "expected_keywords": ["särskild visstidsanställning", "12 månader", "tillsvidareanställning", "femårsperiod"]
    },
    {
        "id": "HR_28_tvist_om_giltighet_34_las",
        "category": "Uppsägning & Sakliga Skäl",
        "question": "Vad gäller angående anställningens bestånd och löneutbetalning vid tvist om en uppsägnings giltighet enligt reformerade 34 § LAS?",
        "expected_statutes": ["LAS 34 §"],
        "expected_ad_cases": ["AD 2023 nr 45"],
        "expected_keywords": ["34 §", "upphör", "lön", "ogiltigförklaring"]
    },
    {
        "id": "HR_29_uppsagningstider_anstallningstid",
        "category": "Uppsägning & Sakliga Skäl",
        "question": "Hur lång är den lagstadgade uppsägningstiden från arbetsgivarens sida för en arbetstagare med sammanlagt 7 års anställningstid enligt 11 § LAS?",
        "expected_statutes": ["LAS 11 §"],
        "expected_keywords": ["fyra månader", "anställningstid", "11 §"]
    },
    {
        "id": "HR_42_fingerad_arbetsbrist",
        "category": "Uppsägning & Sakliga Skäl",
        "question": "Vad innebär begreppet fingerad arbetsbrist och hur fördelas bevisbördan enligt Arbetsdomstolens praxis?",
        "expected_statutes": ["LAS 7 §"],
        "expected_ad_cases": ["AD 2020 nr 30", "AD 2019 nr 32"],
        "expected_keywords": ["fingerad arbetsbrist", "personliga skäl", "bevisbörda", "verkliga skälet"]
    },
    {
        "id": "HR_49_skriftliga_villkor_6c_las",
        "category": "Uppsägning & Sakliga Skäl",
        "question": "Vilka tidsfrister gäller för arbetsgivaren att lämna skriftlig information om väsentliga anställningsvillkor enligt 6 c § LAS?",
        "expected_statutes": ["LAS 6 c §"],
        "expected_keywords": ["sju dagar", "skriftlig information", "villkor", "anställningsförhållande"]
    },

    # Kategori 2: Arbetsbrist, Turordning & Hyvling (11-18)
    {
        "id": "HR_06_hyvling_sysselsattning",
        "category": "Arbetsbrist & Turordning",
        "question": "Hur ska en arbetsgivare gå tillväga vid omreglering till lägre sysselsättningsgrad (hyvling) enligt 7 b § LAS och vilken turordning gäller?",
        "expected_statutes": ["LAS 7 b §", "LAS 22 §"],
        "expected_ad_cases": ["AD 2024 nr 28"],
        "expected_keywords": ["hyvling", "sysselsättningsgrad", "anställningstid"]
    },
    {
        "id": "HR_07_undantag_turordning_3pers",
        "category": "Arbetsbrist & Turordning",
        "question": "Hur många arbetstagare får en arbetsgivare med 85 anställda undanta från turordningen vid arbetsbrist enligt 22 § LAS?",
        "expected_statutes": ["LAS 22 §"],
        "expected_ad_cases": ["AD 2024 nr 14"],
        "expected_keywords": ["tre arbetstagare", "särskild betydelse", "undantag"]
    },
    {
        "id": "HR_08_tillrackliga_kvalifikationer",
        "category": "Arbetsbrist & Turordning",
        "question": "Vad innebär kravet på 'tillräckliga kvalifikationer' vid omplacering och turordning enligt LAS 22 §?",
        "expected_statutes": ["LAS 22 §", "LAS 7 §"],
        "expected_ad_cases": ["AD 2019 nr 32", "AD 2020 nr 30"],
        "expected_keywords": ["tillräckliga kvalifikationer", "upplärningstid", "omplacering"]
    },
    {
        "id": "HR_09_foretradesratt_ateranstallning",
        "category": "Arbetsbrist & Turordning",
        "question": "Vad krävs för att en uppsagd arbetstagare ska ha företrädesrätt till återanställning enligt 25 § LAS och hur lång är anmälningstiden?",
        "expected_statutes": ["LAS 25 §", "LAS 27 §"],
        "expected_ad_cases": ["AD 2014 nr 88", "AD 2017 nr 60"],
        "expected_keywords": ["företrädesrätt", "återanställning", "nio månader"]
    },
    {
        "id": "HR_10_driftsenheter_turordningskrets",
        "category": "Arbetsbrist & Turordning",
        "question": "Hur bestäms turordningskretsar om ett företag har flera arbetsställen på samma ort enligt 22 § LAS?",
        "expected_statutes": ["LAS 22 §"],
        "expected_ad_cases": ["AD 2016 nr 72", "AD 2005 nr 57"],
        "expected_keywords": ["driftsenhet", "samma ort", "turordningskrets"]
    },
    {
        "id": "HR_27_foretradesratt_heltid",
        "category": "Arbetsbrist & Turordning",
        "question": "Vilka förutsättningar gäller för att en deltidsanställd ska ha företrädesrätt till högre sysselsättningsgrad enligt 25 a § LAS?",
        "expected_statutes": ["LAS 25 a §"],
        "expected_keywords": ["företrädesrätt", "högre sysselsättningsgrad", "deltid", "tillräckliga kvalifikationer"]
    },
    {
        "id": "HR_30_foraldraledig_uppsagningstid_start",
        "category": "Arbetsbrist & Turordning",
        "question": "När börjar uppsägningstiden löpa för en arbetstagare som sägs upp på grund av arbetsbrist under pågående föräldraledighet enligt 11 § LAS?",
        "expected_statutes": ["LAS 11 §", "Föräldraledighetslagen 16 §"],
        "expected_keywords": ["återgår i arbete", "börjar löpa", "föräldraledighet", "arbetsbrist"]
    },
    {
        "id": "HR_38_verksamhetsovergang_villkor",
        "category": "Arbetsbrist & Turordning",
        "question": "Vilka rättigheter övergår på den nya arbetsgivaren vid en verksamhetsövergång enligt 6 b § LAS och vad gäller för kollektivavtalet?",
        "expected_statutes": ["LAS 6 b §", "MBL 28 §"],
        "expected_ad_cases": ["AD 2016 nr 72"],
        "expected_keywords": ["övergång av verksamhet", "rättigheter och skyldigheter", "oförändrade", "ett år"]
    },

    # Kategori 3: MBL, Förhandlingsskyldighet & Kollektivavtal (19-26)
    {
        "id": "HR_11_mbl_11_primar_forhandling",
        "category": "MBL & Kollektivavtal",
        "question": "När måste en arbetsgivare på eget initiativ påkalla förhandling enligt 11 § MBL vid organisationsförändring eller outsourcing?",
        "expected_statutes": ["MBL 11 §", "MBL 54 §"],
        "expected_ad_cases": ["AD 2022 nr 48", "AD 2015 nr 18"],
        "expected_keywords": ["viktigare förändring", "primär förhandlingsskyldighet", "skadestånd"]
    },
    {
        "id": "HR_12_kollektivavtals_foretrade",
        "category": "MBL & Kollektivavtal",
        "question": "Vad gäller om ett enskilt anställningsavtal innehåller sämre villkor än tillämpligt kollektivavtal enligt 27 § MBL?",
        "expected_statutes": ["MBL 27 §"],
        "expected_ad_cases": ["AD 2017 nr 24"],
        "expected_keywords": ["ogiltigt", "kollektivavtal", "förmånligare"]
    },
    {
        "id": "HR_13_29_29_principen",
        "category": "MBL & Kollektivavtal",
        "question": "Vad är 29/29-principen och vilka tre kriterier avgör arbetstagarens allmänna arbetsskyldighet?",
        "expected_statutes": ["MBL 4 §"],
        "expected_ad_cases": ["AD 1994 nr 101", "AD 2021 nr 41"],
        "expected_keywords": ["29/29", "arbetsskyldighet", "kollektivavtalets gränser", "allmänna yrkeskvalifikationer"]
    },
    {
        "id": "HR_14_mbl_19_informationsplikt",
        "category": "MBL & Kollektivavtal",
        "question": "Vilken skyldighet har en arbetsgivare att löpande informera facket om ekonomisk och produktionsmässig utveckling enligt 19 § MBL?",
        "expected_statutes": ["MBL 19 §"],
        "expected_keywords": ["ekonomiskt", "produktionsmässigt", "personalpolitik"]
    },
    {
        "id": "HR_37_fortroendemannalagen_ledighet",
        "category": "MBL & Kollektivavtal",
        "question": "Vilken rätt till ledighet och bibehållen lön har en facklig förtroendeman vid facklig verksamhet på arbetsplatsen?",
        "expected_statutes": ["MBL 11 §", "MBL 19 §"],
        "expected_keywords": ["förtroendeman", "facklig verksamhet", "ledighet", "lön"]
    },
    {
        "id": "HR_39_skadestand_allmant_och_ekonomiskt",
        "category": "MBL & Kollektivavtal",
        "question": "Vad är skillnaden mellan allmänt skadestånd och ekonomiskt skadestånd vid brott mot LAS eller MBL?",
        "expected_statutes": ["LAS 38 §", "MBL 54 §", "MBL 55 §"],
        "expected_keywords": ["allmänt skadestånd", "ekonomiskt skadestånd", "kränkning", "förlust"]
    },
    {
        "id": "HR_40_fredsplikt_och_stridsatgarder",
        "category": "MBL & Kollektivavtal",
        "question": "Vilka begränsningar i strejkrätten gäller under löpande kollektivavtalsperiod enligt 41 § MBL (fredsplikt)?",
        "expected_statutes": ["MBL 41 §"],
        "expected_keywords": ["fredsplikt", "stridsåtgärd", "kollektivavtal", "olovlig"]
    },
    {
        "id": "HR_41_lojalitetsplikt_och_bisyssla",
        "category": "MBL & Kollektivavtal",
        "question": "Hur bedömer Arbetsdomstolen gränserna för en anställds rätt att bedriva bisysslor i relation till lojalitetsplikten?",
        "expected_ad_cases": ["AD 2017 nr 24", "AD 2003 nr 24"],
        "expected_keywords": ["lojalitetsplikt", "bisyssla", "konkurrerande"]
    },

    # Kategori 4: Semester, Löneberäkning & Arbetstidslag (27-35)
    {
        "id": "HR_15_semesterratt_och_forlaggning",
        "category": "Semester & Arbetstid",
        "question": "Hur många semesterdagar har en arbetstagare rätt till per år och vilka regler gäller för huvudsemester under juni-augusti enligt semesterlagen?",
        "expected_statutes": ["Semesterlagen 4 §", "Semesterlagen 12 §"],
        "expected_ad_cases": ["AD 2018 nr 37", "AD 2011 nr 54"],
        "expected_keywords": ["tjugofem", "fyra sammanhängande veckor", "juni-augusti"]
    },
    {
        "id": "HR_16_semesterlon_procentregeln",
        "category": "Semester & Arbetstid",
        "question": "Hur beräknas semesterlön enligt semesterlagens procentregel (16 b §) respektive sammalöneregeln (16 a §)?",
        "expected_statutes": ["Semesterlagen 16 a §", "Semesterlagen 16 b §"],
        "expected_keywords": ["tolv procent", "sammalöneregeln", "semestertillägg", "0,43"]
    },
    {
        "id": "HR_17_dygnsvila_och_veckovila",
        "category": "Semester & Arbetstid",
        "question": "Vilka minimigränser gäller för dygnsvila och veckovila enligt Arbetstidslagen?",
        "expected_statutes": ["Arbetstidslagen 13 §", "Arbetstidslagen 14 §"],
        "expected_keywords": ["elva timmars sammanhängande", "trettiosex timmar", "arbetstidslag"]
    },
    {
        "id": "HR_18_maximal_overtid_per_ar",
        "category": "Semester & Arbetstid",
        "question": "Hur många timmar allmän övertid får en arbetsgivare maximalt ta ut per kalenderår enligt Arbetstidslagen?",
        "expected_statutes": ["Arbetstidslagen 8 §"],
        "expected_ad_cases": ["AD 2015 nr 46"],
        "expected_keywords": ["200 timmar", "allmän övertid", "sanktionsavgift"]
    },
    {
        "id": "HR_19_otillaten_kvittning_lon",
        "category": "Semester & Arbetstid",
        "question": "Får en arbetsgivare göra löneavdrag på slutlönen för skada på ett fordon utan medgivande eller Kronofogdens beslut?",
        "expected_statutes": ["SFS 1970:215 1 §"],
        "expected_ad_cases": ["AD 2012 nr 69", "AD 2010 nr 82"],
        "expected_keywords": ["kvittningslagen", "otillåten kvittning", "skadestånd"]
    },
    {
        "id": "HR_31_studieledighet_uppskjutande",
        "category": "Semester & Arbetstid",
        "question": "Vilka regler gäller för studieledighet och arbetsgivarens rätt att skjuta upp begärd ledighet för utbildning enligt Studieledighetslagen?",
        "expected_statutes": ["1974:981 4 §"],
        "expected_keywords": ["ledighet", "utbildning", "uppskjuta"]
    },
    {
        "id": "HR_32_karensavdrag_sjuklon_dag_1_14",
        "category": "Semester & Arbetstid",
        "question": "Hur beräknas karensavdraget och sjuklönen dag 1–14 enligt Lagen om sjuklön?",
        "expected_statutes": ["Sjuklönelagen 6 §", "Sjuklönelagen 7 §"],
        "expected_keywords": ["karensavdrag", "20 procent", "sjuklön", "80 procent"]
    },
    {
        "id": "HR_33_semesterersattning_slutlon",
        "category": "Semester & Arbetstid",
        "question": "När ska intjänad semesterersättning senast betalas ut efter att anställningen upphört enligt 28 § Semesterlagen?",
        "expected_statutes": ["Semesterlagen 28 §"],
        "expected_keywords": ["senast en månad", "semesterersättning", "anställningens upphörande"]
    },
    {
        "id": "HR_34_sparad_semester_regler",
        "category": "Semester & Arbetstid",
        "question": "Hur många semesterdagar får sparas och hur länge får de sparas enligt 18 § Semesterlagen?",
        "expected_statutes": ["Semesterlagen 18 §"],
        "expected_keywords": ["tjugo dagar", "fem år", "spara semesterdagar", "fem dagar per år"]
    },
    {
        "id": "HR_35_jourtid_maxgrans_arbetstid",
        "category": "Semester & Arbetstid",
        "question": "Hur mycket jourtid får tas ut per arbetstagare enligt 6 § Arbetstidslagen?",
        "expected_statutes": ["Arbetstidslagen 6 §"],
        "expected_keywords": ["48 timmar", "fyra veckor", "jourtid", "50 timmar"]
    },

    # Kategori 5: Rehabilitering, SGI & Myndigheter (36-42)
    {
        "id": "HR_20_rehabplan_fk7459",
        "category": "Rehabilitering & Myndigheter",
        "question": "När måste en arbetsgivare upprätta en plan för återgång i arbete enligt SFB och vilken blankett används till Försäkringskassan?",
        "expected_statutes": ["Socialförsäkringsbalken 30 kap. 6 §"],
        "expected_keywords": ["senast dag 30", "60 dagar", "FK 7459", "Försäkringskassan"]
    },
    {
        "id": "HR_21_arbetsgivarintyg_skyldighet",
        "category": "Rehabilitering & Myndigheter",
        "question": "Är arbetsgivaren enligt lag skyldig att utfärda arbetsgivarintyg för a-kassa och hur görs detta digitalt?",
        "expected_statutes": ["Lag (1997:238) om arbetslöshetsförsäkring 47 §"],
        "expected_ad_cases": ["AD 2006 nr 96"],
        "expected_keywords": ["47 § ALF", "arbetsgivarintyg.nu", "a-kassa"]
    },
    {
        "id": "HR_24_prisbasbelopp_och_sgi_tak",
        "category": "Rehabilitering & Myndigheter",
        "question": "Vilket är prisbasbeloppet (PBB) för 2024 respektive 2025 och vilket är taket för sjukpenninggrundande inkomst (SGI)?",
        "expected_keywords": ["57 300", "58 800", "10 PBB", "573 000", "588 000"]
    },
    {
        "id": "HR_25_skattefria_schabloner_milersattning",
        "category": "Rehabilitering & Myndigheter",
        "question": "Vilka skattefria schablonbelopp gäller för milersättning med egen bil samt inrikes traktamente enligt Skatteverket?",
        "expected_keywords": ["25 kr", "milersättning", "290 kr", "traktamente", "145 kr"]
    },
    {
        "id": "HR_44_rehabilitering_alkoholberoende",
        "category": "Rehabilitering & Myndigheter",
        "question": "Hur ser arbetsgivarens rehabiliteringsansvar ut vid alkoholberoende och när föreligger sakliga skäl för uppsägning enligt Arbetsdomstolen?",
        "expected_statutes": ["LAS 7 §"],
        "expected_ad_cases": ["AD 2018 nr 15"],
        "expected_keywords": ["rehabiliteringsansvar", "rehabilitering", "missbruk"]
    },
    {
        "id": "HR_48_arbetsgivarintyg_tidredovisning",
        "category": "Rehabilitering & Myndigheter",
        "question": "Vad ska redovisas på ett arbetsgivarintyg enligt 47 § lagen om arbetslöshetsförsäkring (ALF) vid deltidsarbete?",
        "expected_statutes": ["Lag (1997:238) om arbetslöshetsförsäkring 47 §"],
        "expected_keywords": ["arbetad tid", "frånvaro", "ersättning", "arbetsgivarintyg"]
    },

    # Kategori 6: Diskriminering, Arbetsmiljö & Integritet (43-50)
    {
        "id": "HR_22_diskriminering_graviditet",
        "category": "Diskriminering & Likabehandling",
        "question": "Vad gäller om en visstidsanställd inte får förlängd anställning i nära anslutning till att hon berättat om sin graviditet?",
        "expected_statutes": ["Diskrimineringslagen 1 kap. 4 §", "Föräldraledighetslagen 16 §"],
        "expected_ad_cases": ["AD 2023 nr 21", "AD 2015 nr 70"],
        "expected_keywords": ["diskrimineringsersättning", "bevisbörda", "missgynnande"]
    },
    {
        "id": "HR_23_aktiva_atgarder_lonekartlaggning",
        "category": "Diskriminering & Likabehandling",
        "question": "Vilka krav ställer Diskrimineringslagen och DO på arbetsgivarens årliga lönekartläggning och aktiva åtgärder?",
        "expected_statutes": ["Diskrimineringslagen 3 kap. 8 §"],
        "expected_keywords": ["aktiva åtgärder", "lönekartläggning", "årlig", "10 anställda"]
    },
    {
        "id": "HR_36_skyddsombudsstopp_arbetsmiljo",
        "category": "Diskriminering & Likabehandling",
        "question": "När har ett skyddsombud rätt att avbryta ett arbete (skyddsombudsstopp) enligt 6 kap. 7 § Arbetsmiljölagen (AML)?",
        "expected_statutes": ["Arbetsmiljölagen 6 kap. 7 §"],
        "expected_keywords": ["skyddsombudsstopp", "fara", "arbetsmiljöverket"]
    },
    {
        "id": "HR_43_drogtestning_arbetsplats",
        "category": "Diskriminering & Likabehandling",
        "question": "Under vilka förutsättningar är drogtestning och alkoholtester av personal tillåtna enligt Arbetsdomstolens praxis?",
        "expected_ad_cases": ["AD 2018 nr 15", "AD 2016 nr 33"],
        "expected_keywords": ["drogpåverkan", "säkerhetskänslig", "rehabilitering"]
    },
    {
        "id": "HR_45_tillganglighet_funktionsnedsattning",
        "category": "Diskriminering & Likabehandling",
        "question": "Vilka skyldigheter har en arbetsgivare att genomföra skäliga tillgänglighets- och anpassningsåtgärder för personer med funktionsnedsättning enligt Diskrimineringslagen?",
        "expected_statutes": ["Diskrimineringslagen 2 kap. 1 §"],
        "expected_ad_cases": ["AD 2023 nr 21"],
        "expected_keywords": ["bristande tillgänglighet", "skäliga åtgärder", "funktionsnedsättning", "anpassning"]
    },
    {
        "id": "HR_46_systematiskt_arbetsmiljoarbete_sam",
        "category": "Diskriminering & Likabehandling",
        "question": "Vad innebär kraven på Systematiskt arbetsmiljöarbete (SAM) enligt AFS 2001:1 och Arbetsmiljölagen?",
        "expected_statutes": ["Arbetsmiljölagen 3 kap. 2 a §"],
        "expected_keywords": ["systematiskt arbetsmiljöarbete", "undersöka", "riskbedömning", "åtgärda", "kontrollera"]
    },
    {
        "id": "HR_47_krankande_sarbehandling_osa",
        "category": "Diskriminering & Likabehandling",
        "question": "Vilka krav ställs på arbetsgivarens rutiner mot kränkande särbehandling och mobbning enligt Arbetsmiljölagen och AFS 2015:4 (OSA)?",
        "expected_statutes": ["Arbetsmiljölagen 2 kap. 1 §", "Arbetsmiljölagen 3 kap. 2 a §"],
        "expected_keywords": ["arbetsmiljö", "kränkande", "rutiner"]
    },
    {
        "id": "HR_50_konkurrensklausuler_skalighet",
        "category": "Diskriminering & Likabehandling",
        "question": "Vad krävs för att en konkurrensklausul i ett anställningsavtal ska bedömas som giltig i relation till lojalitetsplikten och konkurrerande verksamhet?",
        "expected_ad_cases": ["AD 2022 nr 12", "AD 2003 nr 24"],
        "expected_keywords": ["lojalitetsplikt", "konkurrerande", "verksamhet"]
    }
]
