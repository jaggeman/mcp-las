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

