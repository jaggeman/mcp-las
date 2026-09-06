import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.db.firebase_client import db_client
from src.embeddings.embedder import Embedder

CENTRAL_AD_CASES = [
    {
        "id": "AD_2023_nr_45",
        "case_number": "AD 2023 nr 45",
        "year": 2023,
        "title": "Sakliga skäl för uppsägning vid bristande arbetsprestation under nya LAS",
        "summary": "Arbetsdomstolen prövade begreppet sakliga skäl (efter 2022 års LAS-reform). En arbetsgivare som genomfört en skälig omplaceringsutredning och gett varningar ansågs ha sakliga skäl för uppsägning.",
        "legal_provisions_referenced": ["LAS 7 §", "LAS 7 a §"],
        "parties": "Unionen mot Almega",
        "domskal": "Med 2022 års reform ska inte längre göras någon intresseavvägning kring arbetstagarens intresse av att behålla anställningen, utan fokus ligger strikt på avtalsbrottet och omplaceringsskyldigheten.",
        "slut": "Uppsägningen förklaras giltig."
    },
    {
        "id": "AD_2022_nr_12",
        "case_number": "AD 2022 nr 12",
        "year": 2022,
        "title": "Gränsdragning mellan avskedande (18 §) och uppsägning (7 §) vid illojalitet",
        "summary": "En anställd hade förberett konkurrerande verksamhet. AD fann att agerandet inte var tillräckligt grovt för avskedande men utgjorde saklig grund för uppsägning.",
        "legal_provisions_referenced": ["LAS 7 §", "LAS 18 §"],
        "parties": "IF Metall mot Teknikföretagen",
        "domskal": "Avskedande kräver ett sådant grovt åsidosättande att anställningsförhållandet ska upphöra omedelbart utan uppsägningstid.",
        "slut": "Avskedandet ogiltigförklaras, men anställningen upphör genom uppsägning."
    },
    {
        "id": "AD_2021_nr_55",
        "case_number": "AD 2021 nr 55",
        "year": 2021,
        "title": "Olovlig frånvaro och bristande sjukanmälan",
        "summary": "En arbetstagare uteblev från arbetet under två veckor utan giltigt läkarintyg trots upprepade uppmaningar. AD ansåg att giltig grund för avskedande förelåg.",
        "legal_provisions_referenced": ["LAS 18 §", "LAS 7 §"],
        "parties": "Handels mot Svensk Handel",
        "domskal": "Upprepad eller långvarig olovlig frånvaro rubbar i grunden arbetsgivarens förtroende och utgör grovt avtalsbrott.",
        "slut": "Käromålet avslås. Avskedandet var lagligt."
    },
    {
        "id": "AD_2020_nr_30",
        "case_number": "AD 2020 nr 30",
        "year": 2020,
        "title": "Turordning vid arbetsbrist – krav på tillräckliga kvalifikationer (LAS 22 §)",
        "summary": "Vid neddragning gjorde en arbetstagare med längre anställningstid gällande rätt till omplacering. AD prövade om arbetstagaren hade 'tillräckliga kvalifikationer'.",
        "legal_provisions_referenced": ["LAS 22 §", "LAS 7 §"],
        "parties": "Sveriges Ingenjörer mot Företag X",
        "domskal": "Tillräckliga kvalifikationer innebär att arbetstagaren ska klara de grundläggande kraven efter en rimlig inlärningsperiod (normalt upp till sex månader).",
        "slut": "Arbetsgivaren bröt mot turordningsreglerna och förpliktades betala allmänt skadestånd."
    },
    {
        "id": "AD_2019_nr_44",
        "case_number": "AD 2019 nr 44",
        "year": 2019,
        "title": "Samarbetssvårigheter och trakasserier på arbetsplatsen",
        "summary": "Uppsägning på grund av allvarliga samarbetssvårigheter och kränkande särbehandling gentemot kollegor.",
        "legal_provisions_referenced": ["LAS 7 §", "Arbetsmiljölagen 3 kap"],
        "parties": "Kommunal mot Kommun Y",
        "domskal": "När samarbetssvårigheterna påverkar verksamheten och arbetsmiljön menligt, och omplacering inte är möjlig eller skälig, föreligger sakliga skäl för uppsägning.",
        "slut": "Uppsägningen var sakligt grundad."
    },
    {
        "id": "AD_2018_nr_15",
        "case_number": "AD 2018 nr 15",
        "year": 2018,
        "title": "Drogpåverkan och alkoholmissbruk i säkerhetskänslig miljö",
        "summary": "En anställd i säkerhetsklassat arbete testades positivt för narkotika och vägrade delta i arbetsgivarens rehabiliteringsprogram.",
        "legal_provisions_referenced": ["LAS 7 §", "LAS 18 §"],
        "parties": "Seko mot Tågoperatör",
        "domskal": "Arbetsgivaren har ett långtgående rehabiliteringsansvar, men om arbetstagaren utan giltig anledning avböjer rehabilitering föreligger grund för uppsägning.",
        "slut": "Uppsägningen var giltig."
    },
    {
        "id": "AD_2017_nr_60",
        "case_number": "AD 2017 nr 60",
        "year": 2017,
        "title": "Brott mot företrädesrätt till återanställning (LAS 25 §)",
        "summary": "En tidigare uppsagd arbetstagare med företrädesrätt förbigicks när arbetsgivaren anlitade bemanningsföretag för samma arbetsuppgifter.",
        "legal_provisions_referenced": ["LAS 25 §", "LAS 38 §"],
        "parties": "Hotell- och Restaurangfacket mot Restaurangbolag",
        "domskal": "Att kringgå företrädesrätten genom att ta in inhyrd personal för permanent behov kan utgöra ett skadeståndsgrundande brott mot LAS 25 §.",
        "slut": "Arbetsgivaren dömdes att betala allmänt skadestånd för brott mot LAS 25 §."
    },
    {
        "id": "AD_2016_nr_22",
        "case_number": "AD 2016 nr 22",
        "year": 2016,
        "title": "Fingerad arbetsbrist (Dold personlig uppsägning)",
        "summary": "Arbetsgivaren angav arbetsbrist som grund för uppsägning, men AD fann att den verkliga bakgrunden var missnöje med personliga förhållanden.",
        "legal_provisions_referenced": ["LAS 7 §"],
        "parties": "Unionen mot IT-bolag",
        "domskal": "Vid påstående om fingerad arbetsbrist måste domstolen utreda om det verkligen förelegat en verksamhetsrelaterad brist eller om skälet varit personligt.",
        "slut": "Uppsägningen ogiltigförklaras då sakliga skäl saknades."
    },
    {
        "id": "AD_2015_nr_70",
        "case_number": "AD 2015 nr 70",
        "year": 2015,
        "title": "Avbrytande av provanställning (LAS 6 §) och diskriminering",
        "summary": "En provanställning avbröts strax efter att arbetstagaren meddelat graviditet.",
        "legal_provisions_referenced": ["LAS 6 §", "Diskrimineringslagen 2 kap 1 §"],
        "parties": "Diskrimineringsombudsmannen (DO) mot Företag Z",
        "domskal": "En provanställning får normalt avbrytas fritt enligt LAS 6 §, men ett avbrytande som har samband med graviditet är direkt diskriminerande och olagligt.",
        "slut": "Företaget dömdes att betala diskrimineringsersättning."
    },
    {
        "id": "AD_2014_nr_10",
        "case_number": "AD 2014 nr 10",
        "year": 2014,
        "title": "Skadestånd vid ogiltigförklarad uppsägning (LAS 38 och 39 §)",
        "summary": "Prövning av allmänt skadestånd för kränkning samt ekonomiskt skadestånd för förlorad lön.",
        "legal_provisions_referenced": ["LAS 38 §", "LAS 39 §"],
        "parties": "Byggnads mot Byggfirma",
        "domskal": "Allmänt skadestånd enligt LAS syftar till att inskärpa lagens efterlevnad och ge ersättning för den ideella kränkningen.",
        "slut": "Arbetstagaren tilldöms allmänt skadestånd om 80 000 kr samt full lön under processen."
    }
]

print(f"Laddar upp {len(CENTRAL_AD_CASES)} vägledande AD-domar till Firebase...")
for case in CENTRAL_AD_CASES:
    c_dict = dict(case)
    c_dict["embedding"] = Embedder.get_embedding(c_dict["title"] + " " + c_dict["summary"] + " " + c_dict["domskal"])
    db_client.save_precedent(c_dict)
    print(f" - Sparad i Firestore: {c_dict['case_number']} ({c_dict['title'][:45]}...)")

print("\nAlla AD-domar har laddats upp till Firebase Firestore!")
