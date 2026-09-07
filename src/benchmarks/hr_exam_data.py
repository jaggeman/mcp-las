"""
Autentiska tentamens- och HR-frågor från Personalvetarprogrammet och facklig/arbetsgivar-rådgivning.
Används för att deterministiskt benchmarka och poängsätta svensk arbetsrättslig AI-precision.
"""

from typing import List, Dict, Any

HR_EXAM_BENCHMARKS: List[Dict[str, Any]] = [
    # Kategori 1: Uppsägning, Avskedande & Sakliga Skäl
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

    # Kategori 2: Arbetsbrist, Turordning & Hyvling
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

    # Kategori 3: MBL, Förhandlingsskyldighet & Kollektivavtal
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

    # Kategori 4: Semester, Löneberäkning & Arbetstidslag
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
        "expected_statutes": ["Lag (1970:215) om arbetsgivares kvittningsrätt"],
        "expected_ad_cases": ["AD 2012 nr 69", "AD 2010 nr 82"],
        "expected_keywords": ["kvittningslagen", "otillåten kvittning", "skadestånd"]
    },

    # Kategori 5: Rehabilitering, SGI, Basbelopp & Diskriminering
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
    }
]
