from typing import Optional, Dict, Any, List
from src.db.firebase_client import db_client

def _determine_certainty(text: str, source_type: str = "statute") -> Dict[str, Any]:
    """
    Bedömer den juridiska säkerhetsnivån baserat på källtyp och förekomst av tolkningsrekvisit.
    """
    text_lower = text.lower() if text else ""
    interpretive_keywords = ["sakliga skäl", "saklig grund", "skälig", "personliga skäl", "omplacering", "synnerliga skäl", "illojal", "väsentlig"]
    is_interpretive = any(kw in text_lower for kw in interpretive_keywords)

    if source_type == "calculation":
        return {
            "score_pct": 99,
            "level": "EXACT_CALCULATION",
            "badge": "🟢 Mycket hög (99%) — Exakt matematisk beräkning",
            "type": "Formelbaserad lag- och avtalsberäkning",
            "is_interpretive": False
        }
    elif source_type == "statute":
        if is_interpretive:
            return {
                "score_pct": 80,
                "level": "STATUTORY_WITH_INTERPRETATION",
                "badge": "🟡 Medelhög (80%) — Lagstadgad ram med tolkningsutrymme",
                "type": "Lagens grundregel (tillämpning kräver skälighetsbedömning/praxis)",
                "is_interpretive": True
            }
        else:
            return {
                "score_pct": 95,
                "level": "DIRECT_STATUTE",
                "badge": "🟢 Hög (95%) — Direkt lagregel",
                "type": "Tydlig lagregel med fastställda frister/krav",
                "is_interpretive": False
            }
    elif source_type == "cba":
        return {
            "score_pct": 90,
            "level": "CBA_RULE",
            "badge": "🔵 Hög (90%) — Kollektivavtalsregel",
            "type": "Gäller under förutsättning att arbetsgivaren är bunden av avtalet",
            "is_interpretive": is_interpretive
        }
    elif source_type == "precedent":
        return {
            "score_pct": 75,
            "level": "CASE_LAW_PRECEDENT",
            "badge": "🟡 Medel (75%) — Rättspraxis (AD)",
            "type": "Vägledande domstolspraxis från Arbetsdomstolen i enskilt rättsfall",
            "is_interpretive": True
        }
    return {
        "score_pct": 70,
        "level": "GENERAL",
        "badge": "⚪ Allmän juridisk information",
        "type": "Allmän rättskälla",
        "is_interpretive": False
    }

def lookup_statute(law: str, section: str, chapter: Optional[str] = None) -> Dict[str, Any]:
    """
    Exact retrieval of a specific Swedish legal paragraph (e.g. law='LAS', section='7').
    Returns the active statutory text, metadata, certainty score, and cross-references.
    """
    result = db_client.get_statute_section(law=law, section=section, chapter=chapter)
    if not result:
        return {
            "found": False,
            "message": f"Kunde inte hitta {law} {chapter + ' kap. ' if chapter else ''}{section} § i databasen.",
            "data": None,
            "certainty": {
                "score_pct": 0,
                "badge": "🔴 Ej funnen i databasen",
                "level": "NOT_FOUND"
            }
        }
    
    content = result.get("content", "")
    certainty = _determine_certainty(content, source_type="statute")
    
    return {
        "found": True,
        "law": result.get("statute_short"),
        "sfs_number": result.get("statute_id"),
        "chapter": result.get("chapter"),
        "section": result.get("section_number"),
        "title": result.get("section_title"),
        "content": content,
        "keywords": result.get("keywords"),
        "certainty": certainty
    }

def search_labor_law(query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Hybrid semantic + lexical search across Swedish labor law provisions with relevance & certainty scoring.
    """
    results = db_client.search_statute_sections(query=query, filters=filters, limit=limit)
    for r in results:
        r["certainty"] = _determine_certainty(r.get("content", ""), source_type="statute")
    return results

def search_case_law(query: str, statute_ref: Optional[str] = None, year_from: Optional[int] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Searches Arbetsdomstolen (AD) case law precedents. Returns matching cases, citations, and legal certainty score.
    """
    results = db_client.search_precedents(query=query, statute_ref=statute_ref, year_from=year_from, limit=limit)
    for r in results:
        r["certainty"] = _determine_certainty(r.get("summary", ""), source_type="precedent")
    return results

def get_cba_exception(statute: str, section: str, agreement_name: str) -> Dict[str, Any]:
    """
    Checks if a collective bargaining agreement deviates from statutory semi-discretionary rules.
    """
    result = db_client.get_cba_exception(statute=statute, section=section, agreement_name=agreement_name)
    if not result:
        return {
            "has_exception": False,
            "message": f"Ingen specifik avvikelse hittades i {agreement_name} för {statute} {section} §.",
            "data": None,
            "certainty": {
                "score_pct": 85,
                "badge": "🔵 Hög (85%) — Lagens grundregel gäller (inga kända avtalsundantag)",
                "level": "STATUTE_DEFAULT"
            }
        }
    return {
        "has_exception": True,
        "agreement": result.get("agreement_name"),
        "statute": result.get("statute"),
        "section": result.get("section"),
        "topic": result.get("topic"),
        "rule_content": result.get("rule_content"),
        "statutory_deviation_ref": result.get("statutory_deviation_ref"),
        "certainty": _determine_certainty(result.get("rule_content", ""), source_type="cba")
    }

def compare_statute_vs_cba(topic: str, agreement_name: str) -> Dict[str, Any]:
    """
    Pulls both statutory baseline (e.g. LAS) and matching collective agreement rules to highlight discrepancies.
    """
    return db_client.compare_statute_vs_cba(topic=topic, agreement_name=agreement_name)

def calculate_vacation_pay(
    monthly_salary: float,
    variable_salary: float = 0.0,
    vacation_days: int = 25,
    agreement_name: Optional[str] = "Unionen / Tjänstemannaavtalet"
) -> Dict[str, Any]:
    """
    Beräknar semesterlön och semestertillägg enligt svensk lag (Semesterlagen)
    och jämför med gällande kollektivavtalsregler (t.ex. Unionen, Teknikavtalet, Almega).
    """
    if monthly_salary <= 0:
        return {"error": "Månadslön måste vara större än 0 kr."}
    if vacation_days <= 0:
        return {"error": "Antal semesterdagar måste vara minst 1."}

    # 1. Kollektivavtal (Unionens standard / Tjänstemän: 0.8% fast lön per dag, 0.5% rörlig lön per dag)
    # Vissa avtal har 0.84% (arbetare) eller 0.6% vid fler semesterdagar, men standarden för 25 dgr tjänstemän är 0.8%.
    cba_fixed_rate = 0.008
    cba_variable_rate = 0.005

    cba_fixed_supplement = monthly_salary * cba_fixed_rate * vacation_days
    cba_variable_supplement = variable_salary * cba_variable_rate * vacation_days
    cba_total_supplement = cba_fixed_supplement + cba_variable_supplement

    # 2. Semesterlagen (Grundregeln enligt 16 a - 16 b §§: 0.43% per dag på fast lön, 12% på rörlig lön)
    statute_fixed_rate = 0.0043
    statute_fixed_supplement = monthly_salary * statute_fixed_rate * vacation_days
    statute_variable_supplement = (variable_salary * 0.12) * (vacation_days / 25.0)
    statute_total_supplement = statute_fixed_supplement + statute_variable_supplement

    diff = cba_total_supplement - statute_total_supplement

    return {
        "input": {
            "monthly_salary": monthly_salary,
            "variable_salary": variable_salary,
            "vacation_days": vacation_days,
            "agreement_name": agreement_name
        },
        "with_collective_agreement": {
            "agreement": agreement_name or "Unionens standardavtal",
            "fixed_supplement_kr": round(cba_fixed_supplement, 2),
            "variable_supplement_kr": round(cba_variable_supplement, 2),
            "total_supplement_kr": round(cba_total_supplement, 2),
            "total_vacation_pay_with_salary_kr": round((monthly_salary * (vacation_days / 25.0)) + cba_total_supplement, 2),
            "formula_fixed": f"{monthly_salary} kr * 0.8% * {vacation_days} dagar",
            "formula_variable": f"{variable_salary} kr * 0.5% * {vacation_days} dagar" if variable_salary > 0 else "0 kr"
        },
        "without_collective_agreement_statute": {
            "legal_basis": "Semesterlagen (1977:480) 16 a-b §§",
            "fixed_supplement_kr": round(statute_fixed_supplement, 2),
            "variable_supplement_kr": round(statute_variable_supplement, 2),
            "total_supplement_kr": round(statute_total_supplement, 2),
            "total_vacation_pay_with_salary_kr": round((monthly_salary * (vacation_days / 25.0)) + statute_total_supplement, 2),
            "formula_fixed": f"{monthly_salary} kr * 0.43% * {vacation_days} dagar",
            "formula_variable": f"{variable_salary} kr * 12% * ({vacation_days}/25)" if variable_salary > 0 else "0 kr"
        },
        "cba_advantage": {
            "extra_in_pocket_kr": round(diff, 2),
            "fixed_rate_difference": "0.80% (kollektivavtal) vs 0.43% (lagen) per semesterdag",
            "summary": f"Kollektivavtalet ger cirka {round(diff):,} kr mer i semestertillägg före skatt jämfört med lagens miniminivå."
        },
        "certainty": {
            "score_pct": 98,
            "badge": "🟢 Mycket hög (98%) — Exakt matematisk beräkning enligt kollektivavtal & Semesterlagen",
            "level": "EXACT_CALCULATION"
        }
    }

def calculate_unpaid_vacation_deduction(
    monthly_salary: float,
    unpaid_days: int = 1,
    is_advance_vacation_debt: bool = False,
    agreement_name: Optional[str] = "Unionen / Tjänstemannaavtalet"
) -> Dict[str, Any]:
    """
    Beräknar löneavdrag vid uttag av obetald semester eller skuldavräkning för förskottssemester
    enligt Unionens kollektivavtal (4,6 % per dag) och allmän arbetsrättspraxis.
    """
    if monthly_salary <= 0:
        return {"error": "Månadslön måste vara större än 0 kr."}
    if unpaid_days <= 0:
        return {"error": "Antal obetalda dagar måste vara minst 1."}

    daily_deduction_rate = 0.046  # 4,6% per dag enligt Unionens tjänstemannaavtal
    daily_deduction_kr = round(monthly_salary * daily_deduction_rate, 2)
    total_deduction_kr = round(monthly_salary * daily_deduction_rate * unpaid_days, 2)
    remaining_salary_kr = max(0.0, round(monthly_salary - total_deduction_kr, 2))

    response = {
        "input": {
            "monthly_salary": monthly_salary,
            "unpaid_days": unpaid_days,
            "is_advance_vacation_debt": is_advance_vacation_debt,
            "agreement_name": agreement_name or "Unionen / Tjänstemannaavtalet"
        },
        "calculation": {
            "daily_deduction_rate_pct": 4.6,
            "daily_deduction_kr": daily_deduction_kr,
            "total_deduction_kr": total_deduction_kr,
            "remaining_monthly_salary_kr": remaining_salary_kr,
            "formula": f"{unpaid_days} dagar * 4.6% * {monthly_salary} kr = {total_deduction_kr} kr"
        },
        "summary": (
            f"Löneavdraget för {unpaid_days} obetalda semesterdagar blir {total_deduction_kr:,.0f} kr före skatt "
            f"(4,6 % av månadslönen per dag). Din kvarvarande månadslön blir {remaining_salary_kr:,.0f} kr."
        ),
        "certainty": {
            "score_pct": 98,
            "badge": "🟢 Mycket hög (98%) — Exakt avdragsberäkning enligt kollektivavtal & praxis",
            "level": "EXACT_CALCULATION"
        }
    }

    if is_advance_vacation_debt:
        response["advance_vacation_rules"] = {
            "legal_basis": "Semesterlagen (1977:480) 29 a § samt kollektivavtal",
            "statutory_protection": (
                "Skulden för förskottssemester avskrivs helt efter 5 års anställning. "
                "Skulden kan INTE krävas tillbaka om anställningen upphör på grund av arbetsbrist, "
                "sjukdom eller om arbetsgivaren i väsentlig grad åsidosatt sina åligganden."
            ),
            "debt_amount_kr": total_deduction_kr,
            "note": "Beräkningen av skulden baseras på den månadslön arbetstagaren hade när förskottssemestern togs ut."
        }

    return response

def calculate_earned_vacation_days(
    employment_days_in_earning_year: int = 365,
    annual_vacation_right: int = 25,
    non_qualifying_absence_days: int = 0,
    earning_year_days: int = 365
) -> Dict[str, Any]:
    """
    Beräknar antal betalda och obetalda semesterdagar enligt Semesterlagen (1977:480) 7 §
    och Unionens/svenska kollektivavtalsregler med lagstadgad uppǻtavrundning.
    """
    import math
    if annual_vacation_right <= 0:
        return {"error": "Årlig semesterrätt måste vara minst 1 dag (normalt 25 enligt lag)."}
    if employment_days_in_earning_year < 0:
        return {"error": "Anställningsdagar kan inte vara negativa."}
    if non_qualifying_absence_days < 0:
        return {"error": "Frånvarodagar kan inte vara negativa."}

    qualifying_days = max(0, employment_days_in_earning_year - non_qualifying_absence_days)
    qualifying_days = min(qualifying_days, earning_year_days)

    # Semesterlagen 7 § st 2: "Uppkommer vid beräkningen av antalet betalda semesterdagar ett brutet dagantal, avrundas detta uppåt till närmaste hela dagantal."
    exact_paid_days = (annual_vacation_right * qualifying_days) / float(earning_year_days)
    paid_vacation_days = math.ceil(exact_paid_days)
    paid_vacation_days = min(paid_vacation_days, annual_vacation_right)

    unpaid_vacation_days = max(0, annual_vacation_right - paid_vacation_days)

    return {
        "input": {
            "employment_days_in_earning_year": employment_days_in_earning_year,
            "annual_vacation_right": annual_vacation_right,
            "non_qualifying_absence_days": non_qualifying_absence_days,
            "earning_year_days": earning_year_days
        },
        "result": {
            "paid_vacation_days": paid_vacation_days,
            "unpaid_vacation_days": unpaid_vacation_days,
            "total_vacation_right": annual_vacation_right,
            "exact_unrounded_paid_days": round(exact_paid_days, 2),
            "qualifying_days_count": qualifying_days
        },
        "legal_basis": "Semesterlagen (1977:480) 7 § samt Unionens kollektivavtalsregler",
        "rounding_rule": "Avrundas alltid UPPÅT till helt dagantal enligt Semesterlagen 7 § andra stycket.",
        "summary": (
            f"Du har rätt till {paid_vacation_days} betalda semesterdagar och "
            f"{unpaid_vacation_days} obetalda semesterdagar (av totalt {annual_vacation_right} semesterdagar per år)."
        ),
        "certainty": {
            "score_pct": 99,
            "badge": "🟢 Mycket hög (99%) — Exakt matematisk beräkning enligt Semesterlagen 7 §",
            "level": "EXACT_CALCULATION"
        }
    }

def get_employer_certificate_info() -> Dict[str, Any]:
    """
    Returnerar information och lagkrav gällande Arbetsgivarintyg för a-kassa enligt 47 § lagen (1997:238) om arbetslöshetsförsäkring
    samt länk till den officiella digitala e-tjänsten www.arbetsgivarintyg.nu.
    """
    return {
        "title": "Arbetsgivarintyg för A-kassa & Ersättning",
        "official_service_url": "https://www.arbetsgivarintyg.nu",
        "service_name": "Arbetsgivarintyg.nu (Sveriges a-kassor)",
        "legal_duty": {
            "statute": "Lag (1997:238) om arbetslöshetsförsäkring (ALF)",
            "section": "47 §",
            "summary": "Arbetsgivaren är enligt 47 § lagstadgat skyldig att på begäran av arbetstagaren snarast utfärda arbetsgivarintyg.",
            "enforcement": "Om arbetsgivaren vägrar eller fördröjer intyget kan arbetstagaren begära vitesföreläggande och arbetsgivaren kan bli skadeståndsskyldig."
        },
        "how_it_works": {
            "for_employers": (
                "Arbetsgivaren loggar in på https://www.arbetsgivarintyg.nu med BankID eller Freja eID, "
                "fyller i arbetad tid och lön för de senaste 12–13 månaderna och signerar digitalt. "
                "Intyget skickas automatiskt digitalt till den anställdes a-kassa."
            ),
            "for_employees": (
                "Begär av din arbetsgivare att de utfärdar intyget via www.arbetsgivarintyg.nu. "
                "När arbetsgivaren har signerat får du ett meddelande och kan godkänna intyget på Mina sidor hos din a-kassa."
            )
        },
        "distinction": {
            "arbetsgivarintyg": "Specifikt intyg om arbetad tid och inkomst avsett för prövning av ersättning hos A-kassan (lagkrav enligt 47 § ALF).",
            "tjanstgoringsintyg": "Intyg som bekräftar att du varit anställd, befattning och anställningstid (för framtida arbetsgivare).",
            "tjanstgoringsbetyg": "Intyg med personligt omdöme och vitsord över hur arbetet har utförts."
        },
        "certainty": {
            "score_pct": 99,
            "badge": "🟢 Mycket hög (99%) — Direkt lagstadgad skyldighet (47 § ALF) & Officiell e-tjänst",
            "level": "DIRECT_STATUTE"
        }
    }

def get_rehabilitation_plan_info() -> Dict[str, Any]:
    """
    Returnerar lagkrav, tidsfrister, mallar (blankett FK7459 PDF) och vägledning för
    'Plan för återgång i arbete' enligt 30 kap. 6 § Socialförsäkringsbalken (SFB) och Försäkringskassan.
    """
    return {
        "title": "Plan för återgång i arbete (Rehabiliteringsplan)",
        "authority": "Försäkringskassan",
        "official_url": "https://www.forsakringskassan.se/arbetsgivare/att-forebygga-sjukfranvaro/plan-for-atergang-i-arbete",
        "template_pdf": {
            "form_number": "FK 7459",
            "name": "Arbetsgivarens plan för återgång i arbete",
            "download_url": "https://www.forsakringskassan.se/download/18.398e2a521762d534987369/1777963998354/7459-arbetsgivarens-plan-for-atergang-i-arbete.pdf",
            "help_guide_url": "https://www.forsakringskassan.se/download/18.73da25b81888fb1e89b9e4/1695379733662/hjalptext-till-blankett-7459-plan-atergang-till-arbetet.pdf"
        },
        "legal_duty": {
            "statute": "Socialförsäkringsbalken (2010:110) 30 kap. 6 §",
            "deadline": "Senast dag 30 i sjukperioden om den anställde väntas vara sjukskriven i minst 60 dagar.",
            "cooperation": "Planen ska upprättas i samråd med arbetstagaren och justeras löpande vid behov.",
            "enforcement": "Planen ska uppvisas för Försäkringskassan på begäran. Vid upprepade försummelser kan Försäkringskassan anmäla till Arbetsmiljöverket (AML 3 kap.)."
        },
        "key_rehab_measures": [
            "Anpassning av arbetsuppgifter och arbetsmiljö",
            "Deltidsarbete / deltidssjukskrivning",
            "Arbetstekniska hjälpmedel och ergonomiska anpassningar",
            "Tillfällig eller permanent omplacering",
            "Utbildning eller omskolning",
            "Inkoppling av företagshälsovård eller extern rehabaktör"
        ],
        "financial_support": {
            "name": "Arbetsplatsinriktat rehabiliteringsstöd",
            "description": "Bidrag från Försäkringskassan för att köpa in expertstöd från företagshälsovård (upp till 10 000 kr/insats och max 200 000 kr/år per arbetsgivare)."
        },
        "certainty": {
            "score_pct": 99,
            "badge": "🟢 Mycket hög (99%) — Direkt lagstadgat krav (30 kap. 6 § SFB) & Försäkringskassans officiella föreskrifter",
            "level": "DIRECT_STATUTE"
        }
    }

def get_discrimination_act_guide(topic: Optional[str] = None) -> Dict[str, Any]:
    """
    Vägledning och lagregler från Diskrimineringsombudsmannen (DO) och Diskrimineringslagen (2008:567),
    inklusive de 7 diskrimineringsgrunderna, aktiva åtgärder (lönekartläggning) och repressalieförbud.
    """
    return {
        "title": "Diskrimineringslagen (2008:567) & DO:s Vägledning",
        "official_url": "https://www.do.se",
        "authority": "Diskrimineringsombudsmannen (DO)",
        "grounds_of_discrimination": [
            "1. Kön",
            "2. Könsöverskridande identitet eller uttryck",
            "3. Etnisk tillhörighet",
            "4. Religion eller annan trosuppfattning",
            "5. Funktionsnedsättning",
            "6. Sexuell läggning",
            "7. Ålder"
        ],
        "forms_of_discrimination": [
            "Direkt diskriminering (missgynnande med koppling till diskrimineringsgrund)",
            "Indirekt diskriminering (till synes neutral bestämmelse som särskilt missgynnar en grupp)",
            "Bristande tillgänglighet (uteblivna skäliga åtgärder för personer med funktionsnedsättning)",
            "Trakasserier och sexuella trakasserier (kränkande uppträdande)",
            "Instruktioner att diskriminera"
        ],
        "employer_obligations_active_measures": {
            "legal_basis": "Diskrimineringslagen 3 kap. (Aktiva åtgärder)",
            "four_steps": "1. Undersöka risker -> 2. Analysera orsaker -> 3. Genomföra åtgärder -> 4. Följa upp och utvärdera",
            "areas": ["Arbetsförhållanden", "Löner och anställningsvillkor", "Rekrytering och befordran", "Utbildning och kompetensutveckling", "Föräldraskap och arbete"],
            "equal_pay_audit": "Årlig lönekartläggning är obligatorisk för alla arbetsgivare. Arbetsgivare med minst 10 anställda måste dokumentera den skriftligt varje år.",
            "written_documentation": "Arbetsgivare med minst 25 anställda måste skriftligt dokumentera hela arbetet med aktiva åtgärder."
        },
        "investigation_and_retaliation": {
            "investigation_duty": "Arbetsgivaren är enligt 2 kap. 3 § DL skyldig att skyndsamt utreda och vidta åtgärder vid kännedom om trakasserier eller sexuella trakasserier.",
            "ban_on_retaliation": "Arbetsgivaren får enligt 2 kap. 18–19 §§ DL inte utsätta en arbetstagare för repressalier (bestraffning/missgynnande) för att denne påtalat diskriminering eller deltagit i en utredning."
        },
        "certainty": {
            "score_pct": 98,
            "badge": "🟢 Mycket hög (98%) — Direkt lagstadgad rätt (Diskrimineringslagen 2008:567) & DO-praxis",
            "level": "DIRECT_STATUTE"
        }
    }

def check_bank_days_and_deadlines(
    date_str: Optional[str] = None,
    check_salary_payout_for_month: Optional[int] = None,
    year: int = 2026
) -> Dict[str, Any]:
    """
    Kontrollerar bankdagar, Riksbankens officiella helgdagar (helgdagar-2026) samt beräknar
    korrekt löneutbetalningsdag (närmast föregående bankdag) och arbetsrättsliga frister
    enligt lag (1930:173) om beräkning av lagstadgad tid.
    """
    import datetime

    # Riksbankens officiella helgdagar och bankfria dagar för 2026 (Källa: www.riksbank.se)
    holidays_2026 = {
        "2026-01-01": "Nyårsdagen",
        "2026-01-06": "Trettondedag jul",
        "2026-04-03": "Långfredagen",
        "2026-04-04": "Påskafton",
        "2026-04-05": "Påskdagen",
        "2026-04-06": "Annandag påsk",
        "2026-05-01": "Första maj",
        "2026-05-14": "Kristi himmelsfärds dag",
        "2026-05-24": "Pingstdagen",
        "2026-06-06": "Sveriges nationaldag",
        "2026-06-19": "Midsommarafton",
        "2026-06-20": "Midsommardagen",
        "2026-10-31": "Alla helgons dag",
        "2026-12-24": "Julafton",
        "2026-12-25": "Juldagen",
        "2026-12-26": "Annandag jul",
        "2026-12-31": "Nyårsafton"
    }

    def is_bank_day(d: datetime.date) -> bool:
        if d.weekday() >= 5:
            return False
        d_str = d.strftime("%Y-%m-%d")
        if d_str in holidays_2026:
            return False
        return True

    def get_salary_payout_date(target_year: int, month: int, standard_day: int = 25) -> Dict[str, Any]:
        target_date = datetime.date(target_year, month, standard_day)
        curr = target_date
        while not is_bank_day(curr):
            curr -= datetime.timedelta(days=1)
        
        sw_days = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
        return {
            "month": month,
            "standard_payout_date": target_date.strftime("%Y-%m-%d"),
            "standard_weekday": sw_days[target_date.weekday()],
            "actual_payout_date": curr.strftime("%Y-%m-%d"),
            "actual_weekday": sw_days[curr.weekday()],
            "is_shifted_earlier": curr < target_date,
            "reason": (
                f"Den {standard_day}:e infaller på en {sw_days[target_date.weekday()].lower()}" +
                (f" ({holidays_2026.get(target_date.strftime('%Y-%m-%d'))})" if target_date.strftime("%Y-%m-%d") in holidays_2026 else "") +
                f". Enligt kollektivavtal ska lönen utbetalas närmast föregående bankdag ({curr.strftime('%Y-%m-%d')})."
                if curr < target_date else
                f"Den {standard_day}:e är en ordinarie bankdag ({sw_days[target_date.weekday()]})."
            )
        }

    response = {
        "source": "Sveriges Riksbank (Officiell kalender för helgdagar 2026)",
        "source_url": "https://www.riksbank.se/sv/press-och-publicerat/kalender/helgdagar-2026/",
        "legal_basis_deadlines": "Lag (1930:173) om beräkning av lagstadgad tid",
        "holidays_2026_count": len(holidays_2026),
        "all_holidays_2026": holidays_2026
    }

    if check_salary_payout_for_month is not None:
        m = max(1, min(12, check_salary_payout_for_month))
        response["salary_payout_analysis"] = get_salary_payout_date(year, m)
    elif date_str:
        try:
            d = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            is_bday = is_bank_day(d)
            sw_days = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
            holiday_name = holidays_2026.get(d.strftime("%Y-%m-%d"))
            
            next_bday = d
            while not is_bank_day(next_bday):
                next_bday += datetime.timedelta(days=1)

            response["date_checked"] = {
                "date": date_str,
                "weekday": sw_days[d.weekday()],
                "is_bank_day": is_bday,
                "is_weekend": d.weekday() >= 5,
                "holiday_name": holiday_name,
                "legal_deadline_shift": (
                    f"Eftersom {date_str} är en bankfri dag/helg förlängs en lagstadgad frist enligt Lag (1930:173) till nästkommande bankdag ({next_bday.strftime('%Y-%m-%d')}, {sw_days[next_bday.weekday()]})."
                    if not is_bday else
                    f"{date_str} är en ordinarie bankdag och ingen fristförlängning sker."
                )
            }
        except ValueError:
            response["date_checked_error"] = f"Ogiltigt datumformat: '{date_str}'. Använd formatet YYYY-MM-DD."
    else:
        response["all_salary_payouts_2026"] = [get_salary_payout_date(year, m) for m in range(1, 13)]

    response["certainty"] = {
        "score_pct": 100,
        "badge": "🟢 Mycket hög (100%) — Riksbankens officiella kalender 2026 & Lag (1930:173)",
        "level": "EXACT_CALCULATION"
    }

    return response


def calculate_redundancy_turnorder_and_exceptions(
    total_employees_in_unit: Optional[int] = None,
    redundancy_count: Optional[int] = None,
    has_collective_bargaining_agreement: bool = True,
    single_operating_unit_only: bool = False,
    merged_operating_units_in_municipality: bool = False,
    contract_areas_count: int = 1,
    employees_list: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Beräknar turordning och undantag vid uppsägning på grund av arbetsbrist enligt
    Unionens kollektivavtalsregler och Lagen om anställningsskydd (LAS 3 §, 7 §, 22 § och 25-27 §§).
    Källa: https://www.unionen.se/rad-och-stod/regler-turordning-vid-uppsagning
    """
    # 1. Undantagsberäkningar (Exemption calculations)
    las_max_exemptions = 3
    cba_alternatives = {}
    
    # Alternativ 1: 3 arbetstagare per berörd driftsenhet och avtalsområde
    cba_alternatives["alternativ_1"] = {
        "name": "Standardundantag per driftsenhet & avtalsområde",
        "allowed_exemptions": 3,
        "rule": "Arbetsgivaren kan vid berörd driftsenhet och avtalsområde undanta 3 arbetstagare.",
        "applies_per": "Per berörd driftsenhet och avtalsområde"
    }
    
    # Alternativ 2: Om arbetsgivaren endast har en enda driftsenhet totalt
    cba_alternatives["alternativ_2"] = {
        "name": "Ensam driftsenhet i företaget (totalt för samtliga avtalsområden)",
        "allowed_exemptions": 4 if single_operating_unit_only else None,
        "rule": "Arbetsgivare som endast har en driftsenhet i hela bolaget kan istället välja att undanta totalt 4 arbetstagare för samtliga avtalsområden gemensamt.",
        "is_applicable": single_operating_unit_only
    }
    
    # Alternativ 3: Sammanslagna driftsenheter på samma ort (22 § 3 st LAS)
    alt3_count = 3 + contract_areas_count if merged_operating_units_in_municipality else None
    cba_alternatives["alternativ_3"] = {
        "name": "Sammanslagna driftsenheter på samma ort",
        "allowed_exemptions": alt3_count,
        "rule": f"Om driftsenheter slagits samman till en gemensam krets på samma ort (22 § 3 st LAS) medges 3 undantag + 1 ytterligare per avtalsområde ({alt3_count} st totalt).",
        "is_applicable": merged_operating_units_in_municipality
    }
    
    # Alternativ 4: Procentregeln (15% av de uppsagda, max 10% av enhetens totala personal)
    if total_employees_in_unit is not None and redundancy_count is not None:
        raw_15_pct = int(redundancy_count * 0.15)
        raw_10_pct_cap = int(total_employees_in_unit * 0.10)
        final_pct_exemptions = min(raw_15_pct, raw_10_pct_cap)
        cba_alternatives["alternativ_4_procentregel"] = {
            "name": "Procentregeln (15 % av uppsagda, max 10 % av arbetsstyrkan)",
            "allowed_exemptions": final_pct_exemptions,
            "calculation_details": {
                "redundancy_count": redundancy_count,
                "fifteen_percent_of_redundant": raw_15_pct,
                "total_employees": total_employees_in_unit,
                "ten_percent_cap": raw_10_pct_cap,
                "final_allowed": final_pct_exemptions
            },
            "rule": "Undanta 15 % av de som slutligen sägs upp på grund av arbetsbrist, dock högst 10 % av totala personalen vid driftsenheten per avtalsområde.",
            "is_applicable": True
        }
    else:
        cba_alternatives["alternativ_4_procentregel"] = {
            "name": "Procentregeln (15 % av uppsagda, max 10 % av arbetsstyrkan)",
            "allowed_exemptions": "Kräver totalt antal anställda och antal varslade för exakt siffra",
            "rule": "Undanta 15 % av de som slutligen sägs upp på grund av arbetsbrist, dock högst 10 % av totala personalen vid driftsenheten per avtalsområde.",
            "is_applicable": False
        }

    # 2. Turordningslista sortering om anställda skickats med
    processed_employees = None
    if employees_list and isinstance(employees_list, list):
        # Sortera: Flest anställningsdagar först (sist in = minst dagar = sägs upp först)
        # Vid lika anställningstid: Äldre före yngre (störst age först)
        sorted_emps = sorted(
            employees_list,
            key=lambda x: (x.get("seniority_days", 0), x.get("age", 0)),
            reverse=True
        )
        processed_employees = []
        for rank, emp in enumerate(sorted_emps, start=1):
            processed_employees.append({
                "rank_seniority": rank,
                "name": emp.get("name", f"Anställd {rank}"),
                "seniority_days": emp.get("seniority_days", 0),
                "age": emp.get("age", 0),
                "has_qualifications": emp.get("has_qualifications", True),
                "is_exempt": emp.get("is_exempt", False),
                "protection_status": (
                    "⭐ Undantagen från turordning (Behåller tjänst)" if emp.get("is_exempt") else
                    "⚠️ Saknar tillräckliga kvalifikationer (Kan gå före i uppsägning)" if not emp.get("has_qualifications", True) else
                    "🛡️ Skyddad genom turordning (Längre anställningstid)" if rank <= (len(sorted_emps) - (redundancy_count or 0)) else
                    "🚨 Risk för uppsägning (Kortast anställningstid)"
                )
            })

    result = {
        "source": "Unionen & Lagen om anställningsskydd (LAS 3 §, 7 §, 22 §, 25-27 §§)",
        "source_url": "https://www.unionen.se/rad-och-stod/regler-turordning-vid-uppsagning",
        "core_steps_and_rules": {
            "step_1_omplacering": {
                "legal_basis": "7 § 2 st LAS",
                "title": "Omplaceringsutredning före turordning",
                "description": "Innan turordning blir aktuell måste arbetsgivaren utreda och erbjuda eventuella lediga tjänster som den anställde har tillräckliga kvalifikationer för. Tackar arbetstagaren nej till skäligt omplaceringserbjudande föreligger normalt sakliga skäl för uppsägning utan turordning."
            },
            "step_2_turordningskrets": {
                "title": "Indelning i turordningskretsar",
                "description": "Kretsen fastställs utifrån organisationsnummer, driftsenhet (geografiskt arbetsställe) och avtalsområde (tjänstemän vs arbetare). Facket kan begära gemensam krets för flera driftsenheter på samma ort. Yttersta gränsen är alltid kommunen."
            },
            "step_3_anstallningstid": {
                "legal_basis": "3 § LAS",
                "title": "Beräkning av anställningstid",
                "description": "All sammanlagd anställningstid hos arbetsgivaren räknas (heltid/deltid/visstid/tillsvidare). Föräldraledighet och studieledighet tillgodoräknas. Vid särskild visstid: har man haft 3+ anställningar under samma kalendermånad räknas även mellanliggande dagar."
            },
            "step_4_kvalifikationer": {
                "title": "Krav på tillräckliga kvalifikationer",
                "description": "För att behålla en tjänst med stöd av längre anställningstid krävs 'tillräckliga kvalifikationer'. Det innebär allmänna kvalifikationer som normalt ställs och möjlighet att lära sig inom rimlig tid (ej krav på att vara bäst kvalificerad)."
            },
            "step_5_huvudregel_kollektivavtal": {
                "title": "Avtalsturlista (Huvudregel vid kollektivavtal)",
                "description": "Fack och arbetsgivare (PTK-L) förhandlar i första hand om en avtalsturlista utifrån verksamhetens behov av kompetens med 'sist in, först ut' som grund."
            }
        },
        "exemption_rules": {
            "las_statutory_exemption": {
                "legal_basis": "22 § LAS",
                "max_exemptions": las_max_exemptions,
                "description": "Arbetsgivaren får undanta högst 3 arbetstagare av särskild betydelse för verksamheten.",
                "freeze_period_months": 3,
                "freeze_rule": "En arbetsgivare som använt undantag får inte göra nya undantag vid uppsägning som sker inom 3 månader."
            },
            "cba_exemption_alternatives": cba_alternatives,
            "recommendation_summary": (
                "Vid kollektivavtal kan arbetsgivaren välja det mest förmånliga alternativet (Alternativ 1, 2, 3 eller 4/Procentregeln) om inte avtalsturlista träffas."
                if has_collective_bargaining_agreement else
                "Utan kollektivavtal gäller strikt 22 § LAS med max 3 undantagna arbetstagare."
            )
        },
        "sorted_turordningslista": processed_employees,
        "certainty": {
            "score_pct": 95,
            "badge": "🟢 Hög (95%) — Unionens officiella turordningsregler & LAS (1982:80)",
            "level": "CBA_AND_STATUTORY_RULE"
        }
    }

    return result


import io
import base64
import uuid
import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# In-memory store för genererade Excel-filer så att de kan laddas ner via HTTP
GENERATED_EXCEL_FILES: Dict[str, Dict[str, Any]] = {}


def generate_turordningslista_excel(
    company_name: str = "Företaget AB",
    employees: Optional[List[Dict[str, Any]]] = None,
    redundancy_count: Optional[int] = 0,
    cba_name: Optional[str] = "Unionen / Tjänstemannaavtalet",
    single_operating_unit: bool = False,
    as_of_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Skapar och formaterar en professionell Excel-arbetsbok (.xlsx) för turordningslista vid arbetsbrist.
    Inkluderar automatisk ID-generering, beräkning av anställningsdagar med Excel-formler (=DATEDIF),
    sortering efter anställningstid (sist in, först ut) och ålder, samt undantagsregler (LAS 22 § vs kollektivavtal).
    """
    target_date = datetime.date.today()
    if as_of_date:
        try:
            target_date = datetime.datetime.strptime(as_of_date, "%Y-%m-%d").date()
        except Exception:
            pass

    if not employees:
        # Skapa realistiskt exempel om inga anställda skickades med
        employees = [
            {"name": "Anna Lindqvist", "title": "Senior Projektledare", "driftsenhet": "Huvudkontor Stockholm", "avtalsomrade": "Tjänstemän", "start_date": "2015-03-01", "birth_date": "1980-05-12", "has_qualifications": True, "is_exempt": False, "notes": "Tillsvidare"},
            {"name": "Erik Johansson", "title": "Systemutvecklare", "driftsenhet": "Huvudkontor Stockholm", "avtalsomrade": "Tjänstemän", "start_date": "2019-09-15", "birth_date": "1988-11-23", "has_qualifications": True, "is_exempt": True, "notes": "Nyckelkompetens arkitektur (Undantagen)"},
            {"name": "Maria Nilsson", "title": "Marknadskoordinator", "driftsenhet": "Huvudkontor Stockholm", "avtalsomrade": "Tjänstemän", "start_date": "2021-02-01", "birth_date": "1992-04-03", "has_qualifications": True, "is_exempt": False, "notes": "Tillsvidare"},
            {"name": "Johan Berg", "title": "Junior Utvecklare", "driftsenhet": "Huvudkontor Stockholm", "avtalsomrade": "Tjänstemän", "start_date": "2023-08-15", "birth_date": "1997-01-19", "has_qualifications": True, "is_exempt": False, "notes": "Tillsvidare"},
            {"name": "Sara Karlsson", "title": "Ekonomiassistent", "driftsenhet": "Huvudkontor Stockholm", "avtalsomrade": "Tjänstemän", "start_date": "2023-08-15", "birth_date": "1994-07-30", "has_qualifications": True, "is_exempt": False, "notes": "Samma startdatum som Johan, men äldre"}
        ]

    # Beräkna anställningsdagar och ålder
    parsed_employees = []
    for idx, emp in enumerate(employees, start=1):
        name = emp.get("name", f"Anställd {idx}")
        title = emp.get("title", "Tjänsteman")
        unit = emp.get("driftsenhet", "Driftsenhet 1")
        cba_area = emp.get("avtalsomrade", "Tjänstemän")
        start_date_str = emp.get("start_date", "2022-01-01")
        birth_date_str = emp.get("birth_date", "1990-01-01")
        has_qual = emp.get("has_qualifications", True)
        is_exempt = emp.get("is_exempt", False)
        notes = emp.get("notes", "")

        try:
            s_date = datetime.datetime.strptime(str(start_date_str), "%Y-%m-%d").date()
            seniority_days = (target_date - s_date).days
        except Exception:
            seniority_days = emp.get("seniority_days", 365)
            start_date_str = "2023-01-01"

        try:
            b_date = datetime.datetime.strptime(str(birth_date_str), "%Y-%m-%d").date()
            age = (target_date - b_date).days // 365
        except Exception:
            age = emp.get("age", 30)

        years = seniority_days // 365
        months = (seniority_days % 365) // 30
        tenure_text = f"{years} år, {months} mån"

        parsed_employees.append({
            "orig_index": idx,
            "name": name,
            "title": title,
            "driftsenhet": unit,
            "avtalsomrade": cba_area,
            "start_date": str(start_date_str),
            "seniority_days": seniority_days,
            "tenure_text": tenure_text,
            "birth_date": str(birth_date_str),
            "age": age,
            "has_qualifications": has_qual,
            "is_exempt": is_exempt,
            "notes": notes
        })

    # Sortera enligt LAS & Kollektivavtal:
    # 1. Mest anställningstid först (störst seniority_days)
    # 2. Vid lika anställningstid: Äldre före yngre (störst age)
    sorted_employees = sorted(
        parsed_employees,
        key=lambda x: (x["seniority_days"], x["age"]),
        reverse=True
    )

    total_count = len(sorted_employees)
    red_count = redundancy_count or 0
    cutoff_rank = total_count - red_count

    # Tilldela ID och status
    table_rows = []
    for rank, emp in enumerate(sorted_employees, start=1):
        emp_id = f"EMP-{rank:03d}"
        if emp["is_exempt"]:
            status = "⭐ Undantagen (Behåller tjänst)"
            status_code = "EXEMPT"
        elif not emp["has_qualifications"]:
            status = "⚠️ Saknar tillräckliga kvalifikationer"
            status_code = "NO_QUAL"
        elif rank <= cutoff_rank:
            status = "🛡️ Skyddad enligt turordning"
            status_code = "PROTECTED"
        else:
            status = "🚨 Risk för uppsägning (Kortast anställningstid)"
            status_code = "AT_RISK"

        emp["id"] = emp_id
        emp["rank"] = rank
        emp["status"] = status
        emp["status_code"] = status_code
        table_rows.append(emp)

    # Skapa Excel-fil med openpyxl
    wb = Workbook()
    
    # ----------------------------------------------------
    # Flik 1: Turordningslista
    # ----------------------------------------------------
    ws1 = wb.active
    ws1.title = "Turordningslista"
    ws1.views.sheetView[0].showGridLines = True

    # Styling-definitioner
    font_title = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    font_subtitle = Font(name="Calibri", size=10, italic=True, color="E2E8F0")
    fill_header_banner = PatternFill(start_color="166534", end_color="166534", fill_type="solid") # Dark Forest Green
    
    font_col_header = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    fill_col_header = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid") # Slate Dark Header
    
    thin_border_side = Side(border_style="thin", color="CBD5E1")
    thin_border = Border(left=thin_border_side, right=thin_border_side, top=thin_border_side, bottom=thin_border_side)
    
    fill_exempt = PatternFill(start_color="FEF9C3", end_color="FEF9C3", fill_type="solid") # Yellow / Gold
    fill_risk = PatternFill(start_color="FEE2E2", end_color="FEE2E2", fill_type="solid") # Light Red
    fill_protected = PatternFill(start_color="DCFCE7", end_color="DCFCE7", fill_type="solid") # Light Green
    fill_no_qual = PatternFill(start_color="FFEDD5", end_color="FFEDD5", fill_type="solid") # Light Orange

    # Banner Header
    ws1.merge_cells("A1:M1")
    ws1["A1"] = f"TURORDNINGSLISTA VID ARBETSBRIST — {company_name.upper()}"
    ws1["A1"].font = font_title
    ws1["A1"].fill = fill_header_banner
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 35

    ws1.merge_cells("A2:M2")
    ws1["A2"] = f"Upprättad: {target_date.strftime('%Y-%m-%d')} | Lagstöd: LAS 3 §, 7 §, 22 § & Kollektivavtal: {cba_name} | Berörda vid arbetsbrist: {red_count} av {total_count}"
    ws1["A2"].font = font_subtitle
    ws1["A2"].fill = fill_header_banner
    ws1["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[2].height = 20

    # Tabellkolumner
    headers = [
        "Anställnings-ID",
        "Namn",
        "Befattning / Titel",
        "Driftsenhet",
        "Avtalsområde",
        "Anställningsdatum",
        "Anställningsdagar (Formel)",
        "Anställningstid",
        "Födelsedatum",
        "Kvalifikationer",
        "Undantagen",
        "Rang",
        "Skyddsstatus / Utfall"
    ]

    ws1.row_dimensions[4].height = 26
    for col_idx, h in enumerate(headers, start=1):
        cell = ws1.cell(row=4, column=col_idx, value=h)
        cell.font = font_col_header
        cell.fill = fill_col_header
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

    # Rader med anställda
    for row_idx, emp in enumerate(table_rows, start=5):
        ws1.row_dimensions[row_idx].height = 22
        
        c1 = ws1.cell(row=row_idx, column=1, value=emp["id"])
        c2 = ws1.cell(row=row_idx, column=2, value=emp["name"])
        c3 = ws1.cell(row=row_idx, column=3, value=emp["title"])
        c4 = ws1.cell(row=row_idx, column=4, value=emp["driftsenhet"])
        c5 = ws1.cell(row=row_idx, column=5, value=emp["avtalsomrade"])
        c6 = ws1.cell(row=row_idx, column=6, value=emp["start_date"])
        
        # Excel Formel för anställningsdagar: =DATEDIF(F5, TODAY(), "d")
        formula_days = f'=DATEDIF(F{row_idx}, TODAY(), "D")'
        c7 = ws1.cell(row=row_idx, column=7, value=formula_days)
        
        c8 = ws1.cell(row=row_idx, column=8, value=emp["tenure_text"])
        c9 = ws1.cell(row=row_idx, column=9, value=emp["birth_date"])
        c10 = ws1.cell(row=row_idx, column=10, value="Ja" if emp["has_qualifications"] else "Nej")
        c11 = ws1.cell(row=row_idx, column=11, value="Ja (Undantagen)" if emp["is_exempt"] else "Nej")
        c12 = ws1.cell(row=row_idx, column=12, value=emp["rank"])
        c13 = ws1.cell(row=row_idx, column=13, value=emp["status"])

        # Formatering och färgkodning per status
        for col_i in range(1, 14):
            cell = ws1.cell(row=row_idx, column=col_i)
            cell.border = thin_border
            cell.alignment = Alignment(vertical="center", horizontal="center" if col_i in [1, 6, 7, 8, 9, 10, 11, 12] else "left")
            
            if emp["status_code"] == "EXEMPT":
                if col_i in [11, 13]:
                    cell.fill = fill_exempt
                    cell.font = Font(name="Calibri", size=10, bold=True, color="854D0E")
            elif emp["status_code"] == "AT_RISK":
                if col_i == 13:
                    cell.fill = fill_risk
                    cell.font = Font(name="Calibri", size=10, bold=True, color="991B1B")
            elif emp["status_code"] == "NO_QUAL":
                if col_i in [10, 13]:
                    cell.fill = fill_no_qual
                    cell.font = Font(name="Calibri", size=10, bold=True, color="C2410C")
            elif emp["status_code"] == "PROTECTED":
                if col_i == 13:
                    cell.fill = fill_protected
                    cell.font = Font(name="Calibri", size=10, bold=True, color="166534")

    # Auto-anpassa kolumnbredder
    for col in ws1.columns:
        max_len = max(len(str(cell.value or '')) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws1.column_dimensions[col_letter].width = max(max_len + 4, 12)

    # ----------------------------------------------------
    # Flik 2: Undantagsregler & Lagstöd
    # ----------------------------------------------------
    ws2 = wb.create_sheet(title="Undantagsregler & Lagstöd")
    ws2.views.sheetView[0].showGridLines = True

    ws2.merge_cells("A1:G1")
    ws2["A1"] = "UNDANTAGSREGLER & JURIDISKT LAGSTÖD VID ARBETSBRIST"
    ws2["A1"].font = font_title
    ws2["A1"].fill = fill_header_banner
    ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws2.row_dimensions[1].height = 35

    rules_info = [
        ("1. Omplaceringsutredning (7 § LAS)", "Innan turordning får tillämpas måste arbetsgivaren utreda och erbjuda eventuella lediga tjänster i organisationen som arbetstagaren har tillräckliga kvalifikationer för."),
        ("2. Turordningskretsar", "Kretsen bestäms av driftsenhet (geografisk plats) och avtalsområde (tjänstemän vs arbetare). Facket kan begära gemensam krets för driftsenheter på samma ort."),
        ("3. Sist in, först ut (22 § LAS)", "Huvudregeln är att längst sammanlagd anställningstid ger företräde. Vid lika anställningstid prioriteras högre ålder."),
        ("4. Tillräckliga kvalifikationer", "Kräver allmänna kvalifikationer med rimlig inlärningstid. Arbetsgivaren kan ej välja den 'bäste' om en person med längre anställningstid uppfyller baskraven."),
        ("5. Avtalsturlista (Kollektivavtal)", "Huvudregeln vid kollektivavtalsbundenhet är att fack och arbetsgivare förhandlar om en överenskommen avtalsturlista (PTK-L)."),
        ("6. LAS Undantagsregel (22 § LAS)", "Arbetsgivaren får undanta högst 3 personer av särskild betydelse för verksamheten (3 månaders spärrtid/karens)."),
        ("7. Kollektivavtal Alternativ 1", "Arbetsgivaren kan vid berörd driftsenhet och avtalsområde undanta 3 arbetstagare."),
        ("8. Kollektivavtal Alternativ 2", "Vid endast 1 driftsenhet i hela företaget kan arbetsgivaren undanta totalt 4 arbetstagare gemensamt."),
        ("9. Kollektivavtal Alternativ 3", "Vid sammanslagna driftsenheter på samma ort medges 3 undantag + 1 extra per avtalsområde."),
        ("10. Kollektivavtal Alternativ 4 (Procentregeln)", f"Undanta 15 % av de uppsagda ({int(red_count * 0.15)} st), dock max 10 % av enhetens personal ({int(total_count * 0.10)} st).")
    ]

    ws2.cell(row=3, column=1, value="Regel / Område").font = font_col_header
    ws2.cell(row=3, column=1).fill = fill_col_header
    ws2.cell(row=3, column=2, value="Beskrivning och tillämpning").font = font_col_header
    ws2.cell(row=3, column=2).fill = fill_col_header
    ws2.row_dimensions[3].height = 24

    for r_idx, (r_title, r_desc) in enumerate(rules_info, start=4):
        ws2.row_dimensions[r_idx].height = 24
        c_t = ws2.cell(row=r_idx, column=1, value=r_title)
        c_d = ws2.cell(row=r_idx, column=2, value=r_desc)
        c_t.border = thin_border
        c_d.border = thin_border
        c_t.font = Font(name="Calibri", size=10, bold=True)
        c_d.font = Font(name="Calibri", size=10)

    ws2.column_dimensions["A"].width = 36
    ws2.column_dimensions["B"].width = 90

    # Spara till minne och skapa base64
    excel_stream = io.BytesIO()
    wb.save(excel_stream)
    excel_bytes = excel_stream.getvalue()
    excel_base64 = base64.b64encode(excel_bytes).decode("utf-8")

    file_id = str(uuid.uuid4())[:8]
    clean_company = company_name.replace(" ", "_").replace("/", "_")
    file_name = f"Turordningslista_{clean_company}_{target_date.strftime('%Y%m%d')}.xlsx"

    # Spara i global cache för direkt nedladdning via servern
    GENERATED_EXCEL_FILES[file_id] = {
        "file_name": file_name,
        "bytes": excel_bytes,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    download_url = f"https://mcp-las-rules.web.app/api/download-turordning?id={file_id}"

    # Skapa markdown-tabell för AI-chatten
    md_lines = [
        f"### 📋 Turordningslista vid Arbetsbrist — {company_name}",
        f"*Upprättad: {target_date.strftime('%Y-%m-%d')} | Kollektivavtal: {cba_name} | Varsel: {red_count} av {total_count} anställda*",
        "",
        "| ID | Namn | Befattning | Driftsenhet | Anställd sedan | Dagar (Formel) | Rang | Utfall / Status |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |"
    ]
    for emp in table_rows:
        md_lines.append(
            f"| `{emp['id']}` | **{emp['name']}** | {emp['title']} | {emp['driftsenhet']} | {emp['start_date']} | {emp['seniority_days']} dgr | #{emp['rank']} | {emp['status']} |"
        )

    return {
        "success": True,
        "file_id": file_id,
        "file_name": file_name,
        "download_url": download_url,
        "data_uri_download": f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{excel_base64}",
        "file_base64": excel_base64,
        "file_size_bytes": len(excel_bytes),
        "total_employees": total_count,
        "redundancy_count": red_count,
        "markdown_table": "\n".join(md_lines),
        "instructions_for_ai": (
            f"Excel-filen har genererats och sparats. Erbjuda användaren att ladda ner Excel-filen via länken: "
            f"[{file_name}]({download_url}) eller bädda in den som fil med nedladdningsknapp."
        ),
        "certainty": {
            "score_pct": 100,
            "badge": "🟢 Mycket hög (100%) — Komplett Excel-arbetsbok med DATEDIF-formler & LAS-undantag",
            "level": "EXACT_CALCULATION"
        }
    }


def get_hr_document_template(
    template_type: str,
    company_name: Optional[str] = "Arbetsgivaren AB / Organisationen",
    employee_name: Optional[str] = "[Arbetstagarens Förnamn Efternamn]",
    personal_identity_number: Optional[str] = "[ÅÅÅÅMMDD-XXXX]",
    job_title: Optional[str] = "[Nuvarande Befattning]",
    workplace_location: Optional[str] = "[Driftsenhet / Arbetsställe]",
    reason_type: Optional[str] = "arbetsbrist",
    union_name: Optional[str] = "[Lokal arbetstagarorganisation / Fackförbund]",
    offered_position_title: Optional[str] = "[Erbjuden ny befattning]",
    offered_position_terms: Optional[str] = "[Anställningsvillkor, sysselsättningsgrad, lön, placering]",
    response_deadline: Optional[str] = "[Datum för svar, t.ex. ÅÅÅÅ-MM-DD]",
    date_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    Genererar officiella svenska mallar för arbetsrättsliga HR-dokument (SKR / LAS-standard)
    som användaren kan ladda ner eller kopiera och skriva vidare i:
    1. 'omplaceringsutredning' (7 § andra stycket LAS - arbetsbrist / personliga skäl)
    2. 'omplaceringserbjudande' (skriftligt erbjudande med svarsalternativ Ja/Nej och signatur)
    3. 'varsel_personliga_skal' (Varsel till facklig organisation enligt 30 § LAS)
    4. 'underrattelse_personliga_skal' (Underrättelse till arbetstagaren enligt 30 § LAS)
    5. 'uppsagningsbesked_arbetsbrist' (Uppsägningsbesked vid arbetsbrist med företrädesrätt 8 § & 25 § LAS)
    """
    today = date_str or datetime.date.today().strftime("%Y-%m-%d")
    c_name = company_name or "Arbetsgivaren AB / Organisationen"
    e_name = employee_name or "[Arbetstagarens Förnamn Efternamn]"
    p_num = personal_identity_number or "[ÅÅÅÅMMDD-XXXX]"
    j_title = job_title or "[Nuvarande Befattning]"
    w_loc = workplace_location or "[Driftsenhet / Arbetsställe]"
    u_name = union_name or "[Lokal arbetstagarorganisation]"
    off_title = offered_position_title or "[Erbjuden ny befattning]"
    off_terms = offered_position_terms or "[Beskriv anställningsvillkor, lön, sysselsättningsgrad och placeringsort]"
    resp_dl = response_deadline or "[Datum för svar, t.ex. inom 7 dagar]"

    t_type = template_type.lower().strip()

    if "omplaceringsutredning" in t_type or "utredning" in t_type:
        title = "Mall för omplaceringsutredning enligt 7 § andra stycket LAS"
        legal_basis = "7 § andra stycket Lagen (1982:80) om anställningsskydd (LAS)"
        required_elements = [
            "Arbetstagarens namn, personnummer och nuvarande anställning",
            "Orsak till utredningen (arbetsbrist eller personliga skäl/sjukdom)",
            "Utbildningsbakgrund och yrkeserfarenhet (Bilaga 1)",
            "Sammanlagd anställningstid hos arbetsgivaren",
            "Utredningsperiod och kartläggning av lediga tjänster (Bilaga 2)",
            "Kvalifikationsbedömning (om arbetstagaren har tillräckliga kvalifikationer)",
            "Ort, datum och behörig företrädares underskrift"
        ]
        doc_text = f"""Datum: {today}
Arbetsgivare: {c_name}

MALL AVSEENDE OMPLACERINGSUTREDNING ENLIGT 7 § ANDRA STYCKET LAS

1. Personuppgifter
Omplaceringsutredning för: {e_name} ({p_num})
Nuvarande befattning: {j_title}
Nuvarande placering: {w_loc}

2. Grund för omplaceringsutredningen
Omplaceringsutredningen är föranledd av:
[ {'X' if 'arbetsbrist' in (reason_type or '').lower() else ' '} ] Arbetsbrist
[ {'X' if 'personlig' in (reason_type or '').lower() else ' '} ] Personliga skäl (inkl. sjukdom / nedsatt arbetsförmåga)

3. Kompetens och anställningshistorik
- Utbildningsbakgrund och yrkeserfarenhet: Se Bilaga 1 (CV & intyg).
- Tidigare anställningar hos arbetsgivaren: [Ange tidigare roller och sammanlagd anställningstid].

4. Genomförande och inventering av lediga befattningar
Omplaceringsutredningen är genomförd under perioden: [ÅÅÅÅ-MM-DD] till [ÅÅÅÅ-MM-DD].
Nedan anges de lediga anställningar inom organisationen som inventerats under perioden (se fullständig förteckning i Bilaga 2):
1. [Befattning 1, Driftsenhet, Sysselsättningsgrad]
2. [Befattning 2, Driftsenhet, Sysselsättningsgrad]
*(Obs: Vid personliga skäl/sjukdom ska även lämpliga tidsbegränsade anställningar redovisas om tillsvidareanställning saknas).*

5. Bedömning av tillräckliga kvalifikationer
[ ] Arbetstagaren ({e_name}) bedöms ha tillräckliga kvalifikationer för följande arbete/n:
    ........................................................................................................................
[ ] Arbetstagaren ({e_name}) bedöms INTE ha tillräckliga kvalifikationer för något av de lediga arbeten som redovisas i Bilaga 2.

6. Underskrift
Ort och datum: .....................................................................................

För {c_name}:
.....................................................................................................
Namnteckning

.....................................................................................................
Namnförtydligande och befattning
"""

    elif "omplaceringserbjudande" in t_type or "erbjudande" in t_type:
        title = "Omplaceringserbjudande enligt 7 § LAS"
        legal_basis = "7 § andra stycket Lagen (1982:80) om anställningsskydd (LAS)"
        required_elements = [
            "Hänvisning till genomförd omplaceringsutredning",
            "Exakt beskrivning av den erbjudna befattningen och anställningsvillkor",
            "Tidsfrist för arbetstagarens skriftliga svar",
            "Kryssrutor för 'Tackar ja' respektive 'Tackar nej'",
            "Mottagandebevis och underskrifter för båda parter",
            "Upplysning om att nej till skäligt erbjudande kan utgöra sakliga skäl för uppsägning"
        ]
        doc_text = f"""Datum: {today}
Arbetsgivare: {c_name}

OMPLACERINGSERBJUDANDE

Till: {e_name} ({p_num})

I enlighet med den omplaceringsutredning som {c_name} har genomfört och kommunicerat till dig den {today} erbjuds du härmed följande befattning som ett skäligt omplaceringserbjudande:

Erbjuden befattning: {off_title}

Befattningen innebär följande anställningsvillkor och arbetsuppgifter:
{off_terms}

Placeringsort / Driftsenhet: {w_loc}
Tillträdesdag: [ÅÅÅÅ-MM-DD]

Ditt skriftliga svar önskas senast den: {resp_dl}

Ort och datum: .....................................................................................

För {c_name}:
.....................................................................................................
Namnteckning & Namnförtydligande

-------------------------------------------------------------------------------------
ARBETSTAGARENS SVARSBLANKETT

Jag har tagit del av ovanstående omplaceringserbjudande den: ........................ 20xx

[  ] Tackar JA till den erbjudna befattningen
[  ] Tackar NEJ till den erbjudna befattningen

Ort och datum: .....................................................................................

Arbetstagarens underskrift:
.....................................................................................................
Namnteckning ({e_name})
"""

    elif ("varsel_personliga_skal" in t_type or "varsel" in t_type) and "avsked" not in t_type:
        title = "Varsel om uppsägning på grund av personliga skäl (till facklig organisation)"
        legal_basis = "30 § första stycket Lagen (1982:80) om anställningsskydd (LAS)"
        required_elements = [
            "Mottagare: Arbetstagarens lokala fackförbund",
            "Den anställdes namn och driftsenhet/arbetsplats",
            "Upplysning om fackets lagstadgade rätt till överläggning",
            "Tidsfrist: Begäran om överläggning ska lämnas inom 1 vecka efter att varslet lämnats",
            "Underskrift av behörig företrädare för arbetsgivaren"
        ]
        doc_text = f"""Datum: {today}
Avsändare: {c_name}

Till: {u_name}
Adress: [Fackets adress / e-post för förhandling]

VARSEL OM UPPSÄGNING PÅ GRUND AV PERSONLIGA SKÄL
(Enligt 30 § lagen om anställningsskydd, LAS)

Uppsägning övervägs beträffande arbetstagaren:
Namn: {e_name} ({p_num})
Befattning: {j_title}
Arbetsställe / Driftsenhet: {w_loc}

{u_name} har enligt 30 § andra stycket LAS rätt till överläggning med {c_name} om den övervägda åtgärden.

Enligt 30 § andra stycket LAS ska begäran om överläggning lämnas till arbetsgivaren ({c_name}) inom EN VECKA efter det att detta varsel lämnats. Om överläggning begärs får arbetsgivaren inte verkställa uppsägningen förrän överläggningen har avslutats.

Ort och datum: .....................................................................................

För {c_name}:
.....................................................................................................
(Undertecknas av behörig företrädare för arbetsgivaren)

.....................................................................................................
Namnförtydligande och titel
"""

    elif "underrattelse_personlig" in t_type or "underrattelse_30" in t_type or ("underrattelse" in t_type and "tidsbegr" not in t_type and "28" not in t_type):
        title = "Underrättelse till arbetstagare om övervägd uppsägning (30 § LAS)"
        legal_basis = "30 § första stycket Lagen (1982:80) om anställningsskydd (LAS)"
        required_elements = [
            "Besked till arbetstagaren att uppsägning övervägs (personliga skäl / avskedande)",
            "Upplysning om rätt till överläggning inom 1 vecka",
            "Information om att facklig organisation samtidigt har varslats",
            "Mottagandekvittens"
        ]
        doc_text = f"""Datum: {today}
Arbetsgivare: {c_name}

UNDERRÄTTELSE OM ÖVERVÄGD UPPSÄGNING PÅ GRUND AV PERSONLIGA SKÄL
(Enligt 30 § lagen om anställningsskydd, LAS)

Till: {e_name} ({p_num})
Befattning: {j_title}

Härmed underrättas du om att {c_name} överväger att säga upp din anställning på grund av personliga skäl.

Du har enligt 30 § andra stycket LAS rätt till överläggning med arbetsgivaren om den övervägda åtgärden. Om du vill begära överläggning ska du meddela arbetsgivaren detta inom EN VECKA från det att du mottog denna underrättelse.

Ditt fackförbund ({u_name}) har samtidigt varslats enligt lag.

Ort och datum: .....................................................................................

För {c_name}:
.....................................................................................................
Namnteckning & Namnförtydligande

-------------------------------------------------------------------------------------
MOTTAGANDEBEVIS

Jag har denna dag mottagit denna underrättelse:

Ort och datum: .....................................................................................

Arbetstagarens underskrift:
.....................................................................................................
Namnteckning ({e_name})
"""

    elif "anstallningsbevis" in t_type or "anstallningsavtal" in t_type or "villkor" in t_type:
        title = "Anställningsbevis med information om anställningsvillkor enligt 6 c § LAS"
        legal_basis = "6 c § Lagen (1982:80) om anställningsskydd (LAS)"
        required_elements = [
            "Arbetsgivarens och arbetstagarens namn, personnummer/org.nr och adress",
            "Tillträdesdag och arbetsplats/driftsenhet",
            "Befattning, yrkesbenämning och huvudsakliga arbetsuppgifter",
            "Anställningsform (tillsvidare, provanställning 6 § LAS, eller tidsbegränsad anställning som särskild visstid/vikariat)",
            "Begynnelselön, löneförmåner, utbetalningsintervall och löneutbetalningssätt",
            "Normal arbetstid, förläggning, regler för övertid/mertid",
            "Semestervillkor och uppsägningsregler",
            "Tillämpligt kollektivavtal (centralt och lokalt)",
            "Information om social trygghet och pensionsavtal (PA16, TGL-S, PSA)"
        ]
        doc_text = f"""ANSTÄLLNINGSBEVIS
(Information om anställningsvillkor enligt 6 c § lagen [1982:80] om anställningsskydd)

Organisation / Arbetsgivare: {c_name}
Datum: {today} | Diarienummer / Anställnings-ID: [Dnr/ID]

1. ARBETSTAGAREN
Namn (efternamn, tilltalsnamn): {e_name}
Personnummer: {p_num}
Adress: [Arbetstagarens bostadsadress]
Telefon / E-post: [Telefonnummer / e-postadress]

2. ANSTÄLLNING
Anställd som: {j_title}
För närvarande placerad vid: {w_loc}
Omfattning: [t.ex. 100% / Heltid / Deltid X %]
Tillträdesdag: [ÅÅÅÅ-MM-DD]
Huvudsakliga arbetsuppgifter: [Beskriv arbetsuppgifternas art och huvudsakliga innehåll]

3. ANSTÄLLNINGSFORM
[  ] Provanställning enligt 6 § LAS fr.o.m. [ÅÅÅÅ-MM-DD] under längst [X] månader (max 6 mån).
[  ] Tills vidare fr.o.m. [ÅÅÅÅ-MM-DD].
[  ] Tidsbegränsad anställning, bestämd tid fr.o.m. [ÅÅÅÅ-MM-DD] t.o.m. [ÅÅÅÅ-MM-DD].
[  ] Tidsbegränsad anställning, tills vidare fr.o.m. [ÅÅÅÅ-MM-DD], dock längst t.o.m. [ÅÅÅÅ-MM-DD].
Grund för tidsbegränsad anställning:
[  ] Särskild visstidsanställning (SÄVA)
[  ] Vikariat (namn på den som vikarien ersätter: .......................................)
[  ] Säsongsarbete
[  ] Annan grund enligt lag/avtal: ....................................................

4. LÖN OCH FÖRMÅNER
Begynnelselön: [XX XXX kr/månad]
Löneutbetalning: Månadsvis i efterskott via bank (den 25:e eller närmast föregående bankdag).
Andra eventuella löneförmåner: [Friskvårdsbidrag, tjänstepension, lunchförmån m.m.].

5. ARBETSTID
Normal arbetstid: [40 timmar/vecka, måndag–fredag].
Regler för mertid och övertid: Ersätts i enlighet med gällande kollektivavtal.

6. KOLLEKTIVAVTAL OCH SOCIAL TRYGGHET
Tillämpligt kollektivavtal: {u_name} / Centralt villkorsavtal.
Social trygghet och försäkringar: Arbetsgivaren betalar lagstadgade arbetsgivaravgifter samt kollektivavtalade försäkringar (TGL, AGS, PA16 / ITP).
Rätt till utbildning: Arbetstagaren har rätt till nödvändig kompetensutveckling och arbetsmiljöutbildning.

7. AVSLUTA ANSTÄLLNING
Uppsägningstider regleras i enlighet med LAS (11 §) och tillämpligt kollektivavtal.

Underskrift för {c_name}:
.....................................................................................................
Behörig företrädare

Mottagits och godkänts av arbetstagaren ({e_name}):
.....................................................................................................
Ort och datum: {today}
"""

    elif "anmalan_foretradesratt" in t_type or "ansprak_foretradesratt" in t_type or "anmalan" in t_type:
        title = "Anmälan om anspråk på företrädesrätt till återanställning (25–27 §§ LAS)"
        legal_basis = "25–27 §§ Lagen (1982:80) om anställningsskydd (LAS)"
        required_elements = [
            "Arbetstagarens namn och kontaktuppgifter",
            "Hänvisning till tidigare uppsägningsbesked och datum",
            "Tidsperiod under vilken företrädesrätten gäller (under uppsägningstid + 9 månader)",
            "Formell skriftlig förklaring om anspråk på företrädesrätt",
            "Datum och underskrift"
        ]
        doc_text = f"""Ort och datum: {today}

Till Arbetsgivaren: {c_name}
Avdelning / HR: [HR-avdelningen / Enhetschef]

ANMÄLAN OM ANSPRÅK PÅ FÖRETRÄDESRÄTT TILL ÅTERANSTÄLLNING
(Enligt 25–27 §§ lagen [1982:80] om anställningsskydd, LAS)

I uppsägningsbesked daterat [ÅÅÅÅ-MM-DD] har jag underrättats om att jag uppfyller kvalifikationstiden och har företrädesrätt till återanställning till och med [ÅÅÅÅ-MM-DD].

Härmed anmäler jag skriftligen mitt anspråk på denna företrädesrätt till återanställning hos {c_name}.

Mina aktuella kontaktuppgifter:
Namn: {e_name}
Personnummer: {p_num}
Adress: [Gatuadress, Postnummer, Ort]
Telefonnummer: [Telefonnummer]
E-postadress: [E-postadress]

Jag ber om skriftlig bekräftelse på att denna anmälan har mottagits och registrerats.

Ort och datum: .....................................................................................

Arbetstagarens underskrift:
.....................................................................................................
Namnteckning ({e_name})
"""

    elif "begaran_forhandling" in t_type or "forhandling_32" in t_type or "32_las" in t_type:
        title = "Begäran om förhandling enligt 32 § LAS (Företrädesrätt)"
        legal_basis = "32 § Lagen (1982:80) om anställningsskydd (LAS)"
        required_elements = [
            "Mottagare: Lokal arbetstagarorganisation",
            "Påkallande av förhandling enligt 32 § LAS",
            "Beskrivning av ärendet (kravprofil, omfattning, företrädesrättsanspråk)",
            "Förslag om tid och plats för förhandling",
            "Underskrift av behörig företrädare"
        ]
        doc_text = f"""Datum: {today}
Arbetsgivare: {c_name}
Diarienummer / Ärendenummer: [Dnr/Ärende]

Till: {u_name}
(Lokal arbetstagarorganisation)

BEGÄRAN OM FÖRHANDLING ENLIGT 32 § LAS

Härmed påkallas förhandling enligt 32 § lagen (1982:80) om anställningsskydd (LAS).

1. Beskrivning av ärendet
Arbetsgivaren avser att tillsätta följande anställning och önskar förhandla om företrädesrätt till återanställning enligt 25 § LAS:
- Befattning / Anställning: {off_title}
- Kravprofil och kvalifikationer: [Ange nödvändiga kompetenskrav och utbildning]
- Omfattning och varaktighet: [Heltid / Deltid / Tillsvidare / Visstid fr.o.m. ÅÅÅÅ-MM-DD]
- Arbetsställe / Driftsenhet: {w_loc}
- Berörd arbetstagare med företrädesrättsanspråk: {e_name} ({p_num})

2. Förslag om tid och plats för förhandling
Datum: [ÅÅÅÅ-MM-DD]  |  Tid: [Kl. XX:XX]
Plats / Möteslänk: [Mötesrum / Digital länk]

Ort och datum: .....................................................................................

För {c_name}:
.....................................................................................................
Signatur & Namnförtydligande
"""

    elif "underrattelse_tidsbegransad" in t_type or "28_las" in t_type:
        title = "Underrättelse om tidsbegränsad anställning enligt 28 § LAS"
        legal_basis = "28 § Lagen (1982:80) om anställningsskydd (LAS)"
        required_elements = [
            "Mottagare: Lokal arbetstagarorganisation",
            "Den anställdes namn och personnummer",
            "Tidsbegränsad befattning och placering",
            "Anställningens period och varaktighet (start- och slutdatum)"
        ]
        doc_text = f"""Datum: {today}
Arbetsgivare: {c_name}
Diarienummer: [Dnr]

Till: {u_name}
(Lokal arbetstagarorganisation)

UNDERRÄTTELSE OM TIDSBEGRÄNSAD ANSTÄLLNING ENLIGT 28 § LAS

Den här underrättelsen sker enligt 28 § lagen (1982:80) om anställningsskydd (LAS).

Arbetstagare:
Namn: {e_name}
Personnummer: {p_num}

har den {today} anställts tidsbegränsat som:
Befattning / Placering: {j_title}, {w_loc}
från och med den: [ÅÅÅÅ-MM-DD]
till och med den: [ÅÅÅÅ-MM-DD]

Upplysningar om anställningens period och varaktighet:
[Ange anställningsform, t.ex. Vikariat / Särskild visstidsanställning samt skäl för tidsbegränsningen].

Ort och datum: .....................................................................................

För {c_name}:
.....................................................................................................
Signatur & Namnförtydligande
"""

    elif "avskedande_varsel" in t_type or "varsel_avskedande" in t_type:
        title = "Varsel om avskedande enligt 30 § LAS (Arbetsgivarverket & SKR)"
        legal_basis = "30 § och 18 § Lagen (1982:80) om anställningsskydd (LAS)"
        required_elements = [
            "Mottagare: Lokal arbetstagarorganisation",
            "Den anställdes namn, personnummer och befattning",
            "Underrättelse om att arbetsgivaren avser att avskeda arbetstagaren",
            "Information om rätt till överläggning inom en vecka från varslet",
            "Datum och behörig underskrift"
        ]
        doc_text = f"""Datum: {today}
Arbetsgivare / Myndighet: {c_name}
Diarienummer: [Dnr]

Till: {u_name}
(Lokal arbetstagarorganisation)

VARSEL OM AVSKEDANDE ENLIGT 30 § LAS

Härmed varslas den lokala arbetstagarorganisationen enligt 30 § lagen (1982:80) om anställningsskydd (LAS) om att arbetsgivaren avser att avskeda följande arbetstagare:

Arbetstagare:
Namn: {e_name}
Personnummer: {p_num}
Befattning / Tjänst: {j_title}
Arbetsställe / Placering: {w_loc}

Grund för den tilltänkta åtgärden:
Arbetstagaren har grovt åsidosatt sina åligganden mot arbetsgivaren enligt 18 § LAS genom följande agerande:
[Specificera de faktiska omständigheterna och datum för händelserna].

Överläggning:
Arbetstagarorganisationen har enligt 30 § andra stycket LAS rätt till överläggning med arbetsgivaren om den tilltänkta åtgärden. Begäran om överläggning ska framställas senast en (1) vecka efter det att varslet lämnades.

Ort och datum: .....................................................................................

För {c_name}:
.....................................................................................................
Signatur & Namnförtydligande
"""

    elif "avskedande_beslut" in t_type or "besked_avskedande" in t_type or "avsked" in t_type:
        title = "Besked om avskedande (18–19 §§ LAS / Arbetsgivarverket)"
        legal_basis = "18–19 §§ och 40–41 §§ Lagen (1982:80) om anställningsskydd (LAS)"
        required_elements = [
            "Skriftlig form och orsak (grovt åsidosättande enligt 18 § LAS)",
            "Omedelbart upphörande utan uppsägningstid",
            "Fullföljdsanvisning för ogiltighetstalan (2 veckor / 4 veckor)",
            "Fullföljdsanvisning för skadeståndstalan (4 månader / 8 månader)",
            "Tidpunkt då avskedandet anses ske (19 § / 10 § LAS)",
            "Mottagandekvittens"
        ]
        doc_text = f"""BESKED OM AVSKEDANDE
(Enligt 18–19 §§ lagen [1982:80] om anställningsskydd, LAS)

Arbetsgivare / Myndighet: {c_name}
Ort & Datum: {today} | Dnr: [Dnr]
Mottagare (Arbetstagarens namn): {e_name} ({p_num})

1. BESKED OM AVSKEDANDE
Du avskedas härmed med omedelbar verkan från din anställning som {j_title} vid {w_loc}.
Anställningen upphör omedelbart från och med den dag du får del av detta besked.

2. GRUND FÖR AVSKEDANDET
Grund för avskedandet är att du grovt har åsidosatt dina åligganden mot arbetsgivaren enligt 18 § LAS.
[Skriftlig uppgift om de omständigheter som åberopas som grund för avskedandet skall lämnas till arbetstagaren om arbetstagaren begär det enligt 19 § 3 st LAS].

3. TALAN OM OGILTIGHET (19 § 2 st & 40 § LAS)
Om du avser att yrka att avskedandet ska förklaras ogiltigt, ska du underrätta arbetsgivaren om detta senast två (2) veckor efter det att avskedandet skedde.
Har din fackliga organisation inom två veckor efter det att avskedandet skedde påkallat överläggning/förhandling, ska talan väckas inom två (2) veckor efter det att förhandlingen avslutades. I annat fall ska talan väckas inom fyra (4) veckor efter avskedandet.

4. TALAN OM SKADESTÅND (41 § LAS)
Om du vill kräva skadestånd med anledning av avskedandet, ska du underrätta arbetsgivaren om detta inom fyra (4) månader och väcka talan inom fyra månader efter förhandlingens avslut (eller åtta månader om förhandling inte påkallats).

Ort och datum: .....................................................................................

För {c_name}:
.....................................................................................................
Signatur & Namnförtydligande

-------------------------------------------------------------------------------------
KVITTERAR MOTTAGANDET
Jag har denna dag tagit del av detta besked om avskedande:

Ort och datum: .....................................................................................
Arbetstagarens underskrift: .........................................................................
"""

    elif "69_ar" in t_type or "pension" in t_type or "32_a" in t_type:
        title = "Skriftligt besked om anställningens upphörande för arbetstagare som fyllt 69 år (32 a–33 §§ LAS)"
        legal_basis = "32 a–33 §§ Lagen (1982:80) om anställningsskydd (LAS)"
        required_elements = [
            "Arbetsgivarens skriftliga besked enligt 33 § LAS",
            "Minst en månads varsel före upphörandet",
            "Angivande av att uppsägningen sker med stöd av uppnådd LAS-ålder (69 år)",
            "Inga sakliga skäl eller företrädesrätt krävs enligt 32 a §",
            "Underskrift och kvittens"
        ]
        doc_text = f"""BESKED OM ANSTÄLLNINGENS UPPHÖRANDE VID UPPNÅDD LAS-ÅLDER (69 ÅR)
(Enligt 32 a och 33 §§ lagen [1982:80] om anställningsskydd, LAS)

Arbetsgivare / Myndighet: {c_name}
Ort & Datum: {today}
Till Arbetstagaren: {e_name} ({p_num})

Härmed meddelas att din anställning som {j_title} vid {w_loc} upphör i och med att du har uppnått 69 års ålder, i enlighet med 32 a § och 33 § LAS.

1. Anställningens upphörande
Anställningen upphör att gälla den: [ÅÅÅÅ-MM-DD] (vilket är minst 1 månad efter att detta besked lämnats).

2. Rättslig reglering
Enligt 32 a § LAS har en arbetstagare rätt att kvarstå i anställningen till utgången av den månad då arbetstagaren fyller 69 år. Därefter har arbetsgivaren rätt att avsluta anställningen genom ett skriftligt besked minst en månad i förväg utan krav på sakliga skäl (7 § LAS) eller företrädesrätt till återanställning (25 § LAS).

Ort och datum: .....................................................................................

För {c_name}:
.....................................................................................................
Signatur & Namnförtydligande

KVITTERAS:
Jag har tagit del av detta besked:
.....................................................................................................
Namnteckning ({e_name})
"""

    elif "ura" in t_type or "utlandsstationering" in t_type:
        title = "Avtal om utlandskontrakt och villkorsbilaga (URA – Arbetsgivarverket)"
        legal_basis = "URA (Avtal om utlandskontrakt och riktlinjer för anställningsvillkor vid tjänstgöring utomlands)"
        required_elements = [
            "Myndighet / Arbetsgivare och Arbetstagare",
            "Stationeringsort, land och tidsperiod för utlandsuppdraget",
            "Tjänstgöringens art och befattning under utlandsvistelsen",
            "Ersättningar: URA-tillägg, merkostnadstillägg, bostadsförmån, medflyttandeersättning",
            "Försäkringsskydd (Kammarkollegiets URA-försäkring)",
            "Hemresor och semestervillkor under utlandsstationering",
            "Återgångsvillkor till hemarbetsplatsen i Sverige"
        ]
        doc_text = f"""AVTAL OM UTLANDSKONTRAKT ENLIGT URA-AVTALET
(Arbetsgivarverket / Statliga avtalsområdet)

1. PARTER
Statlig myndighet / Arbetsgivare: {c_name}
Arbetstagare: {e_name} ({p_num})

2. STATIONERINGSORT OCH UPPDRAG
Stationeringsland: [Land]
Stationeringsort: [Stad / Plats]
Befattning utomlands: {j_title}
Tjänstgöringsperiod: Fr.o.m. [ÅÅÅÅ-MM-DD] t.o.m. [ÅÅÅÅ-MM-DD]

3. ERSÄTTNINGAR OCH FÖRMÅNER ENLIGT URA
- Grundlön i Sverige: [XX XXX kr/månad]
- URA-utlandstillägg: [Belopp kr/månad]
- Merkostnadstillägg (UD/Skatteverkets schablon för stationeringsorten): [Belopp kr/månad]
- Bostad: [Tillhandahålls av myndigheten / Bostadsbidrag enligt URA]
- Medflyttande familj: [Make/maka/partner och X barn]
- Medflyttandetillägg: [Specificeras enligt URA-bestämmelser]

4. FÖRSÄKRING OCH SJUKVÅRD
Arbetstagaren och medföljande familjemedlemmar omfattas av Kammarkollegiets URA-försäkring för läkekostnader, olycksfall och hemtransport.

5. ÅTERGÅNG TILL TJÄNST I SVERIGE
Efter avslutad utlandsstationering återgår arbetstagaren till ordinarie tjänst vid hemorganisationen {w_loc} i enlighet med centrala kollektivavtal.

Ort och datum: .....................................................................................

För {c_name}:                                      Arbetstagaren:
...........................................        ...........................................
Signatur & Namnförtydligande                       {e_name}
"""

    else:
        # Standard: Fullständigt 2-sidigt Uppsägningsbesked vid arbetsbrist (SKR & Arbetsgivarverket)
        title = "Uppsägningsbesked på grund av arbetsbrist (Fullständigt standardformulär)"
        legal_basis = "8–10 §§ och 25–27 §§ Lagen (1982:80) om anställningsskydd (LAS)"
        required_elements = [
            "Skriftlig form och orsak (arbetsbrist)",
            "Uppsägningstid i månader och sista anställningsdag",
            "Besked om företrädesrätt till återanställning (25–27 §§ LAS / 9 månader) och krav på skriftlig anmälan",
            "Fullföljdsanvisning för talan om ogiltighet (underrätta inom 2 veckor / talan inom 2 el. 4 veckor enligt lag 1974:371)",
            "Fullföljdsanvisning för talan om skadestånd (underrätta inom 4 månader / talan inom 4 el. 8 månader)",
            "Tidpunkt när uppsägning anses ske enligt 10 § LAS (personligt överlämnande, rek. brev 10 dagar, semesterregel)",
            "Signaturer och dubbelsidig mottagandekvittens"
        ]
        doc_text = f"""UPPSÄGNINGSBESKED PÅ GRUND AV ARBETSBRIST
(Sida 1 av 2)

Arbetsgivare: {c_name}
Ort & Datum: {today} | Diarienummer / Ärendenummer: [Dnr]
Mottagare (Arbetstagarens namn): {e_name} ({p_num})

1. BESKED OM UPPSÄGNING
Du sägs härmed upp från din anställning som {j_title} med placering vid {w_loc}.
Orsaken till detta är arbetsbrist.

Du har enligt gällande bestämmelser rätt till en uppsägningstid av [X] månader.
Uppsägningstiden räknas från den dag då uppsägningen sker.
Din sista anställningsdag är: [ÅÅÅÅ-MM-DD].

2. FÖRETRÄDESRÄTT TILL ÅTERANSTÄLLNING
[  ] Du har inte företrädesrätt.
[  ] Du har företrädesrätt. Vill du göra anspråk på den ska du skriftligen anmäla det till arbetsgivaren.
     Från den dag du är uppsagd och därefter till dess nio (9) månader har förflutit från anställningens upphörande har du företrädesrätt till återanställning hos {c_name} enligt bestämmelserna i 25–27 §§ lagen (1982:80) om anställningsskydd (LAS) samt gällande kollektivavtal ({u_name}).

3. TALAN OM OGILTIGHET (8 § 2 st & 40 § LAS)
Om du avser att yrka att uppsägningen ska förklaras ogiltig, ska du underrätta arbetsgivaren om detta senast två (2) veckor efter det att uppsägningen skedde.
Har din arbetstagarorganisation inom två veckor efter det att uppsägningen skedde påkallat förhandling om uppsägningens giltighet, ska talan väckas inom två (2) veckor efter det att förhandlingen avslutades. I annat fall ska talan väckas inom fyra (4) veckor efter det att uppsägningen skedde.
Lämnas inte underrättelse eller väcks inte talan inom de angivna tiderna, är rätten till talan om uppsägningens giltighet förlorad. Talan om ogiltighet skall väckas enligt lagen (1974:371) om rättegången i arbetstvister.

-------------------------------------------------------------------------------------
(Sida 2 av 2)

4. TALAN OM SKADESTÅND (41 § LAS)
Om du vill kräva skadestånd med anledning av uppsägningen, ska du underrätta arbetsgivaren om detta inom fyra (4) månader efter det att uppsägningen skedde.
Har din arbetstagarorganisation inom fyra månader efter det att uppsägningen skedde påkallat förhandling om skadestånd på grund av uppsägningen, ska talan väckas inom fyra (4) månader efter det att förhandlingen avslutades. I annat fall ska talan väckas inom åtta (8) månader efter det att uppsägningen skedde.
Lämnas inte underrättelse eller väcks inte talan inom de angivna tiderna, är rätten till talan om skadestånd förlorad.

5. TIDPUNKT NÄR UPPSÄGNINGEN ANSES SKE (10 § LAS)
Vilken dag en uppsägning sker framgår av 10 § LAS:
"Uppsägningsbeskedet skall lämnas till arbetstagaren personligen. Är det inte skäligt att kräva detta, får beskedet i stället sändas i rekommenderat brev till arbetstagarens senast kända adress.
Uppsägning anses ske när arbetstagaren får del av uppsägningen. Om arbetstagaren inte kan anträffas och ett uppsägningsbesked har sänts i brev enligt första stycket, anses uppsägning ha skett tio dagar efter det att brevet lämnades till posten för befordran. Har arbetstagaren semester, anses uppsägning ha skett tidigast dagen efter den då semestern upphörde."

För {c_name}:
.....................................................................................................
Signatur & Namnförtydligande

-------------------------------------------------------------------------------------
KVITTERAR MOTTAGANDET
Jag har denna dag tagit del av detta uppsägningsbesked:

Ort och datum: .....................................................................................

Arbetstagarens signatur:
.....................................................................................................
Namnteckning ({e_name})

(Arbetsgivaren och arbetstagaren ska ha varsitt exemplar av denna blankett).
"""

    return {
        "template_type": t_type,
        "title": title,
        "legal_basis": legal_basis,
        "statutory_required_elements": required_elements,
        "document_template_text": doc_text,
        "instructions_for_ai": (
            "Presentera dokumentmallen med tydlig formatering. "
            "Förklara vilka lagkrav som gäller och ge användaren mallen så att de kan kopiera eller redigera vidare."
        ),
        "certainty": {
            "score_pct": 98,
            "badge": "🟢 Mycket hög (98%) — SKR & Arbetsgivarverket Officiell LAS-standard",
            "level": "STATUTORY_LEGAL_TEMPLATE"
        }
    }


def calculate_travel_deduction_and_mileage(
    transport_mode: str = "egen_bil",
    distance_km_one_way: float = 25.0,
    work_days_per_year: int = 210,
    public_transit_time_minutes_roundtrip: Optional[int] = None,
    car_time_minutes_roundtrip: Optional[int] = None,
    public_transit_cost_yearly: Optional[float] = 0.0,
    tax_year: int = 2026,
    has_public_transit: bool = True,
    marginal_tax_pct: float = 32.0
) -> Dict[str, Any]:
    """
    Beräknar avdrag för resor till och från arbetet (reseavdrag & milersättning) enligt Skatteverkets regler.
    
    Regler och gränsvärden (Inkomstskattelagen 12 kap. 26–30 §§):
    - Egen bil: 25,00 kr per mil.
    - Förmånsbil (ren elbil): 9,50 kr per mil.
    - Förmånsbil (övriga drivmedel bensin/diesel/hybrid): 12,00 kr per mil.
    - Motorcykel / Mopedbil: 12,50 kr per mil.
    - Moped: 6,00 kr per mil.
    - Cykel: Schablon 350 kr/år.
    - Kollektivtrafik: Faktiska biljettkostnader (avstånd >= 2 km).
    
    Villkor för bilavdrag:
    - Minst 5 km enkel resa (eller minst 2 km om kollektivtrafik saknas).
    - Tidsvinst: Du måste regelmässigt tjäna minst 2 timmar (120 min) per dag tur och retur jämfört med kollektivtrafik.
    
    Självrisk / Beloppsgräns:
    - Inkomstår 2026 (Deklaration 2027): 15 000 kr.
    - Inkomstår 2025 (Deklaration 2026): 11 000 kr.
    """
    mode = transport_mode.strip().lower()
    
    # Validering
    if distance_km_one_way <= 0 and mode != "kollektivtrafik":
        return {"error": "Avstånd enkel resa (distance_km_one_way) måste vara större än 0 km."}
    if work_days_per_year <= 0:
        return {"error": "Antal arbetsdagar per år måste vara minst 1."}
        
    total_km_daily = distance_km_one_way * 2.0
    total_km_yearly = total_km_daily * work_days_per_year
    total_mil_yearly = total_km_yearly / 10.0
    
    threshold = 15000.0 if tax_year >= 2026 else 11000.0
    
    # Beräkning per transportmedel
    rate_per_mil = 0.0
    mode_name = "Egen bil"
    total_expense = 0.0
    conditions_met = True
    condition_notes = []
    
    if "formansbil_el" in mode or "elbil" in mode:
        mode_name = "Förmånsbil (Ren Elbil)"
        rate_per_mil = 9.50
        total_expense = total_mil_yearly * rate_per_mil
    elif "formansbil" in mode:
        mode_name = "Förmånsbil (Bensin / Diesel / Hybrid)"
        rate_per_mil = 12.00
        total_expense = total_mil_yearly * rate_per_mil
    elif "motorcykel" in mode or "mopedbil" in mode:
        mode_name = "Motorcykel / Mopedbil"
        rate_per_mil = 12.50
        total_expense = total_mil_yearly * rate_per_mil
    elif "moped" in mode:
        mode_name = "Moped"
        rate_per_mil = 6.00
        total_expense = total_mil_yearly * rate_per_mil
    elif "cykel" in mode:
        mode_name = "Cykel"
        rate_per_mil = 0.0
        total_expense = 350.0  # Fast schablon per år
    elif "kollektiv" in mode or "buss" in mode or "tag" in mode:
        mode_name = "Kollektivtrafik (Buss/Tåg/Spårvagn)"
        total_expense = float(public_transit_cost_yearly or 0.0)
        if distance_km_one_way < 2.0:
            conditions_met = False
            condition_notes.append("För kollektivtrafik krävs normalt att avståndet mellan bostad och arbetsplats är minst 2 km.")
    else:
        # Default: Egen privat bil
        mode_name = "Egen privat bil"
        rate_per_mil = 25.00
        total_expense = total_mil_yearly * rate_per_mil

    # Kontrollera villkor för bil / MC
    time_saved_minutes = None
    if mode in ["egen_bil", "formansbil_el", "formansbil_drivmedel", "motorcykel_mopedbil", "formansbil"]:
        # 1. Avståndskrav
        min_dist = 2.0 if not has_public_transit else 5.0
        if distance_km_one_way < min_dist:
            conditions_met = False
            condition_notes.append(
                f"Avståndet ({distance_km_one_way} km) är kortare än minimikravet på {min_dist} km enkel väg."
            )
            
        # 2. Tidsvinstkrav (om kollektivtrafik finns)
        if has_public_transit:
            if public_transit_time_minutes_roundtrip is not None and car_time_minutes_roundtrip is not None:
                time_saved_minutes = public_transit_time_minutes_roundtrip - car_time_minutes_roundtrip
                if time_saved_minutes < 120:
                    conditions_met = False
                    condition_notes.append(
                        f"Tidsvinsten med bil är {time_saved_minutes} minuter/dag. Skatteverket kräver minst 120 minuters (2 timmars) tidsvinst per dag tur och retur jämfört med kollektivtrafik."
                    )
            else:
                condition_notes.append(
                    "Obs: För fullständigt avdrag kräver Skatteverket att du sparar minst 2 timmar per dag jämfört med kollektivtrafik."
                )

    deductible_amount = max(0.0, total_expense - threshold) if conditions_met else 0.0
    tax_reduction = deductible_amount * (marginal_tax_pct / 100.0)
    
    return {
        "transport_mode": mode_name,
        "tax_year": tax_year,
        "distance_km_one_way": distance_km_one_way,
        "work_days_per_year": work_days_per_year,
        "total_mil_yearly": round(total_mil_yearly, 1),
        "rate_per_mil_sek": rate_per_mil,
        "total_travel_cost_sek": round(total_expense, 2),
        "threshold_deductible_floor_sek": threshold,
        "deductible_amount_sek": round(deductible_amount, 2),
        "estimated_tax_savings_sek": round(tax_reduction, 2),
        "marginal_tax_rate_applied": f"{marginal_tax_pct}%",
        "conditions_met": conditions_met,
        "time_saved_minutes_per_day": time_saved_minutes,
        "condition_notes": condition_notes,
        "skatteverket_schabloner": {
            "milersattning_egen_bil": "25 kr/mil (25,00 kr per mil skattefritt)",
            "milersattning_formansbil_bensin_diesel": "12 kr/mil",
            "milersattning_formansbil_el": "9,50 kr/mil",
            "inrikes_helt_traktamente": "290 kr per hel dag (skattefritt maximibelopp)",
            "inrikes_halvt_traktamente": "145 kr per halv dag",
            "nattraktamente": "145 kr per natt"
        },
        "declaration_guide": {
            "deklarationsruta": "Under 'Avdrag för resor till och från arbetet' i Inkomstdeklaration 1",
            "belopp_att_fylla_i": f"{int(round(deductible_amount))} kr (efter avdragen självrisk om {int(threshold)} kr)",
            "regelverk": "Inkomstskattelagen (1999:1229) 12 kap. 26–30 §§ samt Skatteverkets allmänna råd."
        },
        "certainty": {
            "score_pct": 100,
            "badge": "🟢 100% — Skatteverkets Officiella Skatteregler",
            "level": "STATUTORY_TAX_REGULATION"
        }
    }


def get_base_amounts_and_indices(
    year: Optional[int] = 2026,
    compare_all_years: bool = False
) -> Dict[str, Any]:
    """
    Hämtar officiella prisbasbelopp (PBB), förhöjt prisbasbelopp, inkomstbasbelopp (IBB)
    och inkomstindex från SCB och Regeringen/Pensionsmyndigheten för 2026 och tidigare år.
    Inkluderar automatisk årlig kontrollfunktion för 1 januari.
    """
    from src.services.base_amount_service import BaseAmountService
    
    if compare_all_years:
        return BaseAmountService.list_all_years()
        
    target_year = year or 2026
    data = BaseAmountService.get_amounts_for_year(target_year)
    update_info = BaseAmountService.check_and_update_yearly()
    
    return {
        "target_year": target_year,
        "data": data,
        "auto_update_status": update_info,
        "summary_text": (
            f"För år {target_year} är Prisbasbeloppet (PBB) {data.get('prisbasbelopp', 0):,} kr "
            f"och Inkomstbasbeloppet (IBB) {data.get('inkomstbasbelopp', 0):,} kr "
            f"(Inkomstindex {data.get('inkomstindex', 0)})."
        ),
        "certainty": {
            "score_pct": 100,
            "badge": "🟢 100% — Officiellt fastställt av Regeringen & SCB",
            "level": "OFFICIAL_STATUTORY_INDEX"
        }
    }







