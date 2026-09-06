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



