"""Coverage catalog based on the Danish Ministry of Employment's official overview."""

_BM_OVERVIEW = "https://www.bm.dk/arbejdsomraader/arbejdsvilkaar/arbejdsretlige-love/oversigt-over-arbejdsretlige-love"


def _entry(name: str, priority: str, category: str, aliases: list[str]) -> dict:
    return {
        "name": name,
        "jurisdiction": "DK",
        "language": "da",
        "source": "Beskæftigelsesministeriet/Retsinformation",
        "source_listing_url": _BM_OVERVIEW,
        "priority": priority,
        "category": category,
        "aliases": aliases,
    }


DANISH_LABOR_LAW_CATALOG = [
    _entry("Lov om ansættelsesbeviser og visse arbejdsvilkår", "core", "employment_contract", ["ansættelsesbevisloven", "ansættelsesvilkår"]),
    _entry("Lov om ret til orlov og dagpenge ved barsel (barselsloven)", "core", "parental_leave", ["barselsloven", "barsel", "forældreorlov"]),
    _entry("Lov om gennemførelse af dele af arbejdstidsdirektivet (arbejdstidsloven)", "core", "working_time", ["arbejdstidsloven", "tidsregistrering", "48 timer"]),
    _entry("Deltidsloven", "extended", "working_time", ["deltidsansatte", "deltidsarbejde"]),
    _entry("Ferieloven", "core", "holiday", ["ferie", "feriedage", "feriepenge"]),
    _entry("Foreningsfrihedsloven", "core", "collective_relations", ["foreningsfrihed", "fagforening"]),
    _entry("Forskelsbehandlingsloven", "core", "discrimination", ["alder", "handicap", "religion", "seksuel orientering"]),
    _entry("Funktionærloven", "core", "termination", ["funktionær", "opsigelse", "fratrædelsesgodtgørelse", "løn under sygdom"]),
    _entry("Helbredsoplysningsloven", "extended", "privacy_and_health", ["helbredsoplysninger", "helbredsundersøgelse"]),
    _entry("Ligebehandlingsloven", "core", "equality", ["køn", "graviditet", "barsel", "seksuel chikane"]),
    _entry("Ligelønsloven", "core", "equality", ["lige løn", "kønsligestilling"]),
    _entry("Lov om information og høring af lønmodtagere", "core", "employee_information", ["information og høring", "medarbejderindflydelse"]),
    _entry("Lov om lønmodtagers ret til fravær fra arbejde af særlige familiemæssige årsager", "core", "leave", ["omsorgsorlov", "familiemæssige årsager"]),
    _entry("Lov om tidsbegrænset ansættelse", "core", "fixed_term", ["tidsbegrænset ansættelse", "vikariat"]),
    _entry("Lov om udstationering af lønmodtagere m.v.", "core", "posted_workers", ["udstationering", "RUT", "udenlandsk virksomhed"]),
    _entry("Lov om vikarers retsstilling ved udsendelse af et vikarbureau m.v.", "extended", "agency_workers", ["vikar", "vikarbureau", "ligebehandling"]),
    _entry("Lov om lønmodtageres retsstilling ved virksomhedsoverdragelse (Virksomhedsoverdragelsesloven)", "core", "transfer", ["virksomhedsoverdragelse", "overdragelse", "arbejdsgiverskifte"]),
    _entry("Lov om Arbejdsretten og faglige voldgiftsretter", "core", "labor_disputes", ["Arbejdsretten", "faglig voldgift", "overenskomstbrud"]),
    _entry("Lov om mægling i arbejdsstridigheder", "extended", "labor_disputes", ["forligsmand", "arbejdsstrid"]),
    _entry("Lov om europæiske samarbejdsudvalg", "specialized", "employee_information", ["ESU", "europæiske samarbejdsudvalg"]),
    _entry("Lov om medarbejderindflydelse i SE-selskaber", "specialized", "employee_information", ["SE-selskab", "medarbejderindflydelse"]),
    _entry("Lov om medarbejderindflydelse i SCE-selskaber", "specialized", "employee_information", ["SCE-selskab", "medarbejderindflydelse"]),
    _entry("Lov om barselsudligning på det private arbejdsmarked", "extended", "parental_leave", ["barselsudligning", "barselsrefusion"]),
    _entry("Lov om brug af køberet eller tegningsret til aktier m.v. i ansættelsesforhold", "specialized", "pay_and_benefits", ["aktieoptioner", "køberet", "tegningsret"]),
    _entry("Lov om værnepligtsorlov og om orlov ved forsvarets udsendelse af lønmodtagere til udlandet", "specialized", "leave", ["værnepligtsorlov", "udsendelse"]),
    _entry("Lov om konsekvenser ved afskaffelsen af store bededag som helligdag", "specialized", "working_time", ["store bededag", "løntillæg"]),
    _entry("Deltidsloven", "extended", "working_time", ["deltid", "fuldtid"]),
    _entry("Medhjælperloven", "specialized", "employment_contract", ["husligt arbejde", "landbrugsarbejde"]),
    _entry("LD-loven", "specialized", "pay_and_benefits", ["Lønmodtagernes Dyrtidsfond", "LD"]),
    _entry("LG-loven", "extended", "pay_and_benefits", ["Lønmodtagernes Garantifond", "konkurs", "lønkrav"]),
    _entry("Lov om ligebehandlingsnævnet (Ligebehandlingsnævnsloven)", "core", "discrimination", ["Ligebehandlingsnævnet", "klage", "godtgørelse"]),
]

# The Ministry list contains Deltidsloven once; keep catalog IDs unique for ingestion.
_seen = set()
DANISH_LABOR_LAW_CATALOG = [
    item for item in DANISH_LABOR_LAW_CATALOG
    if not (item["name"] in _seen or _seen.add(item["name"]))
]
