from typing import Optional, Dict, Any, List
from src.db.firebase_client import db_client

def lookup_statute(law: str, section: str, chapter: Optional[str] = None) -> Dict[str, Any]:
    """
    Exact retrieval of a specific Swedish legal paragraph (e.g. law='LAS', section='7').
    Returns the active statutory text, metadata, and cross-references.
    """
    result = db_client.get_statute_section(law=law, section=section, chapter=chapter)
    if not result:
        return {
            "found": False,
            "message": f"Kunde inte hitta {law} {chapter + ' kap. ' if chapter else ''}{section} § i databasen.",
            "data": None
        }
    return {
        "found": True,
        "law": result.get("statute_short"),
        "sfs_number": result.get("statute_id"),
        "chapter": result.get("chapter"),
        "section": result.get("section_number"),
        "title": result.get("section_title"),
        "content": result.get("content"),
        "keywords": result.get("keywords")
    }

def search_labor_law(query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Hybrid semantic + lexical search across Swedish labor law provisions with relevance scoring.
    """
    return db_client.search_statute_sections(query=query, filters=filters, limit=limit)

def search_case_law(query: str, statute_ref: Optional[str] = None, year_from: Optional[int] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Searches Arbetsdomstolen (AD) case law precedents. Returns matching cases and citations.
    """
    return db_client.search_precedents(query=query, statute_ref=statute_ref, year_from=year_from, limit=limit)

def get_cba_exception(statute: str, section: str, agreement_name: str) -> Dict[str, Any]:
    """
    Checks if a collective bargaining agreement deviates from statutory semi-discretionary rules.
    """
    result = db_client.get_cba_exception(statute=statute, section=section, agreement_name=agreement_name)
    if not result:
        return {
            "has_exception": False,
            "message": f"Ingen specifik avvikelse hittades i {agreement_name} för {statute} {section} §.",
            "data": None
        }
    return {
        "has_exception": True,
        "agreement": result.get("agreement_name"),
        "statute": result.get("statute"),
        "section": result.get("section"),
        "topic": result.get("topic"),
        "rule_content": result.get("rule_content"),
        "statutory_deviation_ref": result.get("statutory_deviation_ref")
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
        }
    }
