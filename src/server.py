import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from typing import Optional, Dict, Any, List
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.middleware.cors import CORSMiddleware
from fastmcp import FastMCP
from src.config import settings
from src.db.firebase_client import db_client
from src.db.auth_service import auth_service
from src.mcp_tools.tools import (
    lookup_statute as _lookup_statute,
    search_labor_law as _search_labor_law,
    search_case_law as _search_case_law,
    get_cba_exception as _get_cba_exception,
    compare_statute_vs_cba as _compare_statute_vs_cba,
    calculate_vacation_pay as _calculate_vacation_pay,
    calculate_unpaid_vacation_deduction as _calculate_unpaid_vacation_deduction,
    calculate_earned_vacation_days as _calculate_earned_vacation_days,
    get_employer_certificate_info as _get_employer_certificate_info,
    get_rehabilitation_plan_info as _get_rehabilitation_plan_info,
    get_discrimination_act_guide as _get_discrimination_act_guide,
    check_bank_days_and_deadlines as _check_bank_days_and_deadlines,
    calculate_redundancy_turnorder_and_exceptions as _calculate_redundancy_turnorder_and_exceptions
)

mcp = FastMCP(
    name=settings.MCP_SERVER_NAME,
    instructions=(
        "Svensk Arbetsrätt & LAS MCP Server för AI-agenter och Claude. "
        "Innehåller verktyg för lagparagrafer (LAS, MBL, Semesterlagen, Arbetstidslagen, Diskrimineringslagen), "
        "turordningsregler och undantagsberäkningar vid arbetsbrist (Unionen & 22 § LAS), "
        "Arbetsdomstolens prejudikat, 17 kollektivavtal, semesterberäkningar, Försäkringskassans plan för återgång i arbete (FK 7459), "
        "arbetsgivarintyg (arbetsgivarintyg.nu / 47 § ALF), DO:s vägledning samt Riksbankens bankdagar och helgdagar för löneutbetalning och lagstadgade frister."
    )
)

# Tillåt CORS för alla webbläsare och Claude
@mcp.custom_route("/", methods=["GET", "OPTIONS"])
async def serve_landing_page(request):
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "*", "Access-Control-Allow-Headers": "*"})
    html_path = Path(project_root) / "public" / "index.html"
    if html_path.exists():
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
            return HTMLResponse(content)
    return HTMLResponse("<h1>MCP LAS Server</h1><p><a href='/sse'>/sse</a></p>")

from src.services.notification_service import notification_service

@mcp.custom_route("/api/request-key", methods=["POST", "OPTIONS"])
async def handle_key_request(request):
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "*", "Access-Control-Allow-Headers": "*"})
    try:
        data = await request.json()
        name = data.get("name", "").strip()
        email = data.get("email", "").strip()
        company = data.get("company", "").strip()
        reason = data.get("reason", "").strip()
        
        if not name or not email or "@" not in email or "." not in email:
            return JSONResponse({"success": False, "message": "Giltigt namn och e-postadress krävs."}, status_code=400)
            
        request_record = {
            "name": name,
            "email": email,
            "company": company,
            "reason": reason,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Spara i databasen
        if db_client.db:
            doc_ref = db_client.db.collection("key_requests").document()
            doc_ref.set(request_record)
        
        # Skicka e-postavisering till administratören
        try:
            notification_service.send_key_request_notification(request_record)
        except Exception as notify_err:
            print(f"[NOTIFICATION ERROR] {notify_err}")

        return JSONResponse({"success": True, "message": "Din ansökan har tagits emot! Vi återkommer via e-post."})
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

def _check_rate_limit(api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    client_id = api_key if api_key else "anon"
    limit = 300 if api_key else 60
    if not auth_service.check_rate_limit(client_id, max_requests=limit, window_seconds=60):
        return {
            "error": "Rate limit exceeded (max 60 förfrågningar/minut). Vänligen vänta en kort stund innan du skickar fler anrop.",
            "status": "rate_limited"
        }
    return None

@mcp.tool()
def lookup_statute(law: str, section: str, chapter: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _lookup_statute(law=law, section=section, chapter=chapter)
    auth_service.log_access(api_key or "anon", None, "lookup_statute", {"law": law, "section": section}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def search_labor_law(query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 5, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return [rl_err]
    t0 = time.time()
    res = _search_labor_law(query=query, filters=filters, limit=limit)
    auth_service.log_access(api_key or "anon", None, "search_labor_law", {"query": query}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def search_case_law(query: str, statute_ref: Optional[str] = None, year_from: Optional[int] = None, limit: int = 10, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return [rl_err]
    t0 = time.time()
    res = _search_case_law(query=query, statute_ref=statute_ref, year_from=year_from, limit=limit)
    auth_service.log_access(api_key or "anon", None, "search_case_law", {"query": query, "statute_ref": statute_ref}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def get_cba_exception(statute: str, section: str, agreement_name: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _get_cba_exception(statute=statute, section=section, agreement_name=agreement_name)
    auth_service.log_access(api_key or "anon", None, "get_cba_exception", {"statute": statute, "section": section, "agreement": agreement_name}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def compare_statute_vs_cba(topic: str, agreement_name: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _compare_statute_vs_cba(topic=topic, agreement_name=agreement_name)
    auth_service.log_access(api_key or "anon", None, "compare_statute_vs_cba", {"topic": topic, "agreement": agreement_name}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def calculate_vacation_pay(
    monthly_salary: float,
    variable_salary: float = 0.0,
    vacation_days: int = 25,
    agreement_name: Optional[str] = "Unionen / Tjänstemannaavtalet",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Beräknar semesterlön och semestertillägg enligt svensk lag (Semesterlagen 16 a-b §§)
    och jämför med Unionens och centrala kollektivavtalsregler (0.8% fast lön, 0.5% rörlig lön).
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _calculate_vacation_pay(
        monthly_salary=monthly_salary,
        variable_salary=variable_salary,
        vacation_days=vacation_days,
        agreement_name=agreement_name
    )
    auth_service.log_access(api_key or "anon", None, "calculate_vacation_pay", {"monthly_salary": monthly_salary, "days": vacation_days}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def calculate_unpaid_vacation_deduction(
    monthly_salary: float,
    unpaid_days: int = 1,
    is_advance_vacation_debt: bool = False,
    agreement_name: Optional[str] = "Unionen / Tjänstemannaavtalet",
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Beräknar löneavdrag vid uttag av obetalda semesterdagar eller skuldavräkning för förskottssemester
    enligt Unionens kollektivavtalsregler (4,6 % av månadslönen per dag) samt Semesterlagen (1977:480) 29 a §.
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _calculate_unpaid_vacation_deduction(
        monthly_salary=monthly_salary,
        unpaid_days=unpaid_days,
        is_advance_vacation_debt=is_advance_vacation_debt,
        agreement_name=agreement_name
    )
    auth_service.log_access(api_key or "anon", None, "calculate_unpaid_vacation_deduction", {"monthly_salary": monthly_salary, "unpaid_days": unpaid_days}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def calculate_earned_vacation_days(
    employment_days_in_earning_year: int = 365,
    annual_vacation_right: int = 25,
    non_qualifying_absence_days: int = 0,
    earning_year_days: int = 365,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Beräknar antal betalda och obetalda semesterdagar enligt Semesterlagen (1977:480) 7 §
    och Unionens kollektivavtal baserat på anställningstid och frånvaro under intjänandeåret.
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _calculate_earned_vacation_days(
        employment_days_in_earning_year=employment_days_in_earning_year,
        annual_vacation_right=annual_vacation_right,
        non_qualifying_absence_days=non_qualifying_absence_days,
        earning_year_days=earning_year_days
    )
    auth_service.log_access(api_key or "anon", None, "calculate_earned_vacation_days", {"employment_days": employment_days_in_earning_year, "right": annual_vacation_right}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def get_employer_certificate_info(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Ger information om lagkrav och rutiner för Arbetsgivarintyg för a-kassa (47 § ALF)
    samt hänvisning till den officiella digitala tjänsten www.arbetsgivarintyg.nu.
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _get_employer_certificate_info()
    auth_service.log_access(api_key or "anon", None, "get_employer_certificate_info", {}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def get_rehabilitation_plan_info(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Ger lagkrav, tidsfrister och direktlänk till Försäkringskassans mall/blankett (FK 7459 PDF)
    för 'Plan för återgång i arbete' enligt 30 kap. 6 § Socialförsäkringsbalken (SFB).
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _get_rehabilitation_plan_info()
    auth_service.log_access(api_key or "anon", None, "get_rehabilitation_plan_info", {}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def get_discrimination_act_guide(topic: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Vägledning och lagregler från Diskrimineringsombudsmannen (DO) och Diskrimineringslagen (2008:567),
    inklusive de 7 diskrimineringsgrunderna, aktiva åtgärder (lönekartläggning) och repressalieförbud.
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _get_discrimination_act_guide(topic=topic)
    auth_service.log_access(api_key or "anon", None, "get_discrimination_act_guide", {"topic": topic}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def check_bank_days_and_deadlines(
    date_str: Optional[str] = None,
    check_salary_payout_for_month: Optional[int] = None,
    year: int = 2026,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Kontrollerar bankdagar och Riksbankens officiella helgdagar (helgdagar-2026),
    beräknar datum för löneutbetalning (närmast föregående bankdag) samt lagstadgade frister enligt lag (1930:173).
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _check_bank_days_and_deadlines(
        date_str=date_str,
        check_salary_payout_for_month=check_salary_payout_for_month,
        year=year
    )
    auth_service.log_access(api_key or "anon", None, "check_bank_days_and_deadlines", {"date": date_str, "month": check_salary_payout_for_month}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def calculate_redundancy_turnorder_and_exceptions(
    total_employees_in_unit: Optional[int] = None,
    redundancy_count: Optional[int] = None,
    has_collective_bargaining_agreement: bool = True,
    single_operating_unit_only: bool = False,
    merged_operating_units_in_municipality: bool = False,
    contract_areas_count: int = 1,
    employees_list: Optional[List[Dict[str, Any]]] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Beräknar turordningslista och undantag vid arbetsbrist (undantagsregler 1-4, procentregeln 15%/10%, LAS 22 § vs kollektivavtal)
    samt krav på omplaceringsutredning (7 § LAS) och anställningstid (3 § LAS).
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _calculate_redundancy_turnorder_and_exceptions(
        total_employees_in_unit=total_employees_in_unit,
        redundancy_count=redundancy_count,
        has_collective_bargaining_agreement=has_collective_bargaining_agreement,
        single_operating_unit_only=single_operating_unit_only,
        merged_operating_units_in_municipality=merged_operating_units_in_municipality,
        contract_areas_count=contract_areas_count,
        employees_list=employees_list
    )
    auth_service.log_access(api_key or "anon", None, "calculate_redundancy_turnorder_and_exceptions", {"total": total_employees_in_unit, "redundant": redundancy_count}, (time.time() - t0)*1000)
    return res

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    if "PORT" in os.environ:
        mcp.run(transport="http", host="0.0.0.0", port=port)
    else:
        mcp.run()
