import os
import sys
import time
import logging
import inspect
import asyncio
from datetime import datetime, timezone
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from typing import Optional, Dict, Any, List
from starlette.responses import HTMLResponse, JSONResponse, Response
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware import Middleware
from src.services.request_limits import RequestSizeLimit
from src.services.usage_logging import tracked_tool, tracked_rest
from fastmcp import FastMCP
from src.config import settings
from src.db.firebase_client import db_client
from src.db.auth_service import auth_service
from src.mcp_tools.tools import (
    get_legal_coverage as _get_legal_coverage,
    lookup_statute as _lookup_statute,
    search_labor_law as _search_labor_law,
    search_case_law as _search_case_law,
    get_cba_exception as _get_cba_exception,
    compare_statute_vs_cba as _compare_statute_vs_cba,
    calculate_vacation_pay as _calculate_vacation_pay,
    calculate_notice_period as _calculate_notice_period,
    calculate_unpaid_vacation_deduction as _calculate_unpaid_vacation_deduction,
    calculate_earned_vacation_days as _calculate_earned_vacation_days,
    get_employer_certificate_info as _get_employer_certificate_info,
    get_rehabilitation_plan_info as _get_rehabilitation_plan_info,
    get_discrimination_act_guide as _get_discrimination_act_guide,
    check_bank_days_and_deadlines as _check_bank_days_and_deadlines,
    calculate_redundancy_turnorder_and_exceptions as _calculate_redundancy_turnorder_and_exceptions,
    generate_turordningslista_excel as _generate_turordningslista_excel,
    get_hr_document_template as _get_hr_document_template,
    calculate_travel_deduction_and_mileage as _calculate_travel_deduction_and_mileage,
    get_base_amounts_and_indices as _get_base_amounts_and_indices,
    search_parliament_and_legislation as _search_parliament_and_legislation,
    get_parliament_document_details as _get_parliament_document_details,
    GENERATED_EXCEL_FILES
)

mcp = FastMCP(
    name=settings.MCP_SERVER_NAME,
    mask_error_details=True,
    instructions=(
        "Arbetsrätts-MCP för Sverige, Danmark, Finland, Norge, Tyskland och Spanien. "
        "Välj jurisdiction (SE, DK, FI, NO, DE, ES) för laguppslag och sökning. "
        "Källor: Riksdagen, Retsinformation, Finlex, Lovdata, Gesetze im Internet och BOE. "
        "get_legal_coverage visar faktisk datatäckning per land; kontrollera den före uppslag. "
        "Specialverktyg för beräkningar, praxis, kollektivavtal och mallar gäller endast Sverige. "
        "Innehåller verktyg för lagparagrafer (LAS, MBL, Semesterlagen, Arbetstidslagen, Diskrimineringslagen), "
        "HR-dokumentmallar (omplaceringsutredning 7 § LAS, omplaceringserbjudande, varsel 30 § LAS, uppsägningsbesked), "
        "turordningsregler, Excel-export av turordningslista vid arbetsbrist (Unionen & 22 § LAS), "
        "Arbetsdomstolens prejudikat, 13 kollektivavtal, semesterberäkningar, Försäkringskassans plan för återgång i arbete (FK 7459), "
        "arbetsgivarintyg (arbetsgivarintyg.nu / 47 § ALF), DO:s vägledning samt Riksbankens bankdagar och helgdagar för löneutbetalning och lagstadgade frister."
    )
)

# Tillåt CORS för alla webbläsare och Claude
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "*",
    "Access-Control-Allow-Headers": "*",
}

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

@mcp.custom_route("/health", methods=["GET", "OPTIONS"])
async def health_check(request):
    """Vilken kod kör här just nu?

    Finns för att frågan ska gå att ställa med ett anrop. Utan den krävdes
    deployloggar, revisionslistor och git-historik för att avgöra om det som
    svarar på en domän är det som ligger på main — och två parallella
    driftsättningar av samma tjänst är då omöjliga att skilja åt utifrån.

    BUILD_SHA sätts av CI vid deploy. En image byggd för hand har ingen, och
    svarar "unknown" hellre än något som ser ut som en sha.

    Ingen Firestore-läsning: endpointet är tänkt att kunna pollas. Det är
    också publikt och oautentiserat — därav att det inte lämnar ut projekt-id
    eller sökvägar, samma gräns som felsvaren drar sedan #30.
    """
    if request.method == "OPTIONS":
        return Response(status_code=200, headers=CORS_HEADERS)

    return JSONResponse(
        {
            "status": "ok",
            "build_sha": os.environ.get("BUILD_SHA") or "unknown",
            "build_ref": os.environ.get("BUILD_REF") or "unknown",
            "server": settings.MCP_SERVER_NAME,
            "database_connected": db_client.db is not None,
            "tool_count": len(DIRECT_TOOLS_MAP),
            "time": datetime.now(timezone.utc).isoformat(),
        },
        headers=CORS_HEADERS,
    )

@mcp.custom_route("/api/download-turordning", methods=["GET", "OPTIONS"])
async def download_turordning_excel(request):
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "*", "Access-Control-Allow-Headers": "*"})
    file_id = request.query_params.get("id", "")
    file_data = GENERATED_EXCEL_FILES.get(file_id) if len(file_id) == 43 else None
    if file_data is None:
        return JSONResponse({"error": "Filen hittades inte eller har löpt ut. Generera en ny via MCP-verktyget."}, status_code=404)

    headers = {
        "Cache-Control": "no-store",
        "Referrer-Policy": "no-referrer",
        "X-Content-Type-Options": "nosniff",
        "Content-Disposition": f"attachment; filename=\"{file_data['file_name']}\"",
        "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "Access-Control-Allow-Origin": "*"
    }
    return Response(content=file_data["bytes"], media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)


@mcp.custom_route("/api/coverage", methods=["GET", "OPTIONS"])
async def public_legal_coverage(request):
    """Small public, read-only snapshot used by the landing page.

    The underlying aggregate is cached in the database client for 60 seconds,
    and the same period is advertised to browsers/CDNs.  This keeps the site
    truthful after source synchronization without turning page views into
    unbounded Firestore reads.
    """
    if request.method == "OPTIONS":
        return Response(status_code=200, headers=CORS_HEADERS)
    try:
        coverage = await asyncio.to_thread(_get_legal_coverage)
        return JSONResponse(
            coverage,
            headers={**CORS_HEADERS, "Cache-Control": "public, max-age=60"},
        )
    except Exception:
        logging.error("Kunde inte läsa publik lagtäckning")
        return JSONResponse(
            {"error": "Täckningsstatus är tillfälligt otillgänglig."},
            status_code=503,
            headers={**CORS_HEADERS, "Cache-Control": "no-store"},
        )

from src.services.notification_service import notification_service

@mcp.custom_route("/api/request-key", methods=["POST", "OPTIONS"])
async def handle_key_request(request):
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "*", "Access-Control-Allow-Headers": "*"})
    # Enda publika endpointet som skriver utan nyckel. Utan tak kan en loop
    # fylla Firestore och samtidigt mejlbomba mottagaren av aviseringarna.
    # Nycklas pa klientens IP - "anon" delas av alla, sa en ensam avsandare
    # skulle annars sla ut formuläret for alla andra.
    klient_ip = (getattr(getattr(request, "client", None), "host", "")
                 or "anon")
    if not auth_service.check_rate_limit(f"key-request:{klient_ip}",
                                         max_requests=5, window_seconds=600):
        return JSONResponse(
            {"success": False, "message": "För många ansökningar. Försök igen om en stund."},
            status_code=429, headers={"Access-Control-Allow-Origin": "*"})

    # Falten hamnar i databasen och i ett mejl. Utan tak ar de obegransade.
    MAXLANGD = {"name": 200, "email": 320, "company": 200, "reason": 2000}

    try:
        data = await request.json()
        name = str(data.get("name", "")).strip()
        email = str(data.get("email", "")).strip()
        company = str(data.get("company", "")).strip()
        reason = str(data.get("reason", "")).strip()

        if not name or not email or "@" not in email or "." not in email:
            return JSONResponse({"success": False, "message": "Giltigt namn och e-postadress krävs."}, status_code=400)

        for falt, varde in (("name", name), ("email", email),
                            ("company", company), ("reason", reason)):
            if len(varde) > MAXLANGD[falt]:
                return JSONResponse(
                    {"success": False,
                     "message": f"Fältet '{falt}' är för långt (max {MAXLANGD[falt]} tecken)."},
                    status_code=400, headers={"Access-Control-Allow-Origin": "*"})

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
    except Exception:
        # Samma skal som i /api/tools: undantagstexten kan bara projekt-id och
        # sokvagar, och sager anroparen ingenting. Loggas, returneras inte.
        logging.error("Fel vid mottagning av nyckelansokan")
        return JSONResponse({"success": False, "message": "Kunde inte ta emot ansökan just nu."},
                            status_code=500)

DIRECT_TOOLS_MAP = {
    "get_legal_coverage": _get_legal_coverage,
    "lookup_statute": _lookup_statute,
    "search_labor_law": _search_labor_law,
    "search_case_law": _search_case_law,
    "get_cba_exception": _get_cba_exception,
    "compare_statute_vs_cba": _compare_statute_vs_cba,
    "calculate_vacation_pay": _calculate_vacation_pay,
    "calculate_notice_period": _calculate_notice_period,
    "calculate_unpaid_vacation_deduction": _calculate_unpaid_vacation_deduction,
    "calculate_earned_vacation_days": _calculate_earned_vacation_days,
    "get_employer_certificate_info": _get_employer_certificate_info,
    "get_rehabilitation_plan_info": _get_rehabilitation_plan_info,
    "get_discrimination_act_guide": _get_discrimination_act_guide,
    "check_bank_days_and_deadlines": _check_bank_days_and_deadlines,
    "calculate_redundancy_turnorder_and_exceptions": _calculate_redundancy_turnorder_and_exceptions,
    "generate_turordningslista_excel": _generate_turordningslista_excel,
    "get_hr_document_template": _get_hr_document_template,
    "calculate_travel_deduction_and_mileage": _calculate_travel_deduction_and_mileage,
    "get_base_amounts_and_indices": _get_base_amounts_and_indices,
    "search_parliament_and_legislation": _search_parliament_and_legislation,
    "get_parliament_document_details": _get_parliament_document_details,
}

@mcp.custom_route("/api/tools/list", methods=["GET", "OPTIONS"])
async def list_available_tools_rest(request):
    """Returnerar lista över tillgängliga verktyg för behöriga klienter med giltig API-nyckel."""
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "*", "Access-Control-Allow-Headers": "*"})

    api_key = request.headers.get("X-API-Key")
    if not api_key:
        return JSONResponse({
            "success": False,
            "error": "API-nyckel krävs. Ansök om en API-nyckel på https://las.novro.se/#key-request."
        }, status_code=401, headers={"Access-Control-Allow-Origin": "*"})

    key_info = await asyncio.to_thread(auth_service.validate_key, api_key)
    if not key_info:
        return JSONResponse({
            "success": False,
            "error": "Ogiltig eller inaktiv API-nyckel."
        }, status_code=403, headers={"Access-Control-Allow-Origin": "*"})

    return JSONResponse({
        "success": True,
        "tools_count": len(DIRECT_TOOLS_MAP),
        "tools": list(DIRECT_TOOLS_MAP.keys()),
        "authorized_user": key_info.get("name", "Authorized Client")
    }, headers={"Access-Control-Allow-Origin": "*"})

@mcp.custom_route("/api/tools/{tool_name}", methods=["POST", "OPTIONS"])
@tracked_rest
async def execute_tool_direct_rest(request):
    """
    Kräver giltig API-nyckel via X-API-Key-header.
    Användare utan nyckel nekas med 401 Unauthorized och uppmanas ansöka om nyckel.
    """
    if request.method == "OPTIONS":
        return Response(status_code=200, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "*", "Access-Control-Allow-Headers": "*"})

    tool_name = request.path_params.get("tool_name", "").strip()
    if tool_name not in DIRECT_TOOLS_MAP:
        return JSONResponse({
            "error": f"Verktyget '{tool_name}' finns inte.",
            "available_tools": list(DIRECT_TOOLS_MAP.keys())
        }, status_code=404, headers={"Access-Control-Allow-Origin": "*"})

    try:
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass

        if not isinstance(body, dict):
            return JSONResponse({"error": "JSON måste vara ett objekt."}, status_code=400)

        api_key = request.headers.get("X-API-Key")
        if not api_key:
            return JSONResponse({
                "success": False,
                "error": "API-nyckel krävs för att anropa verktyg. Ansök om en personlig nyckel på https://las.novro.se/#key-request eller skicka med 'X-API-Key' i HTTP-headern."
            }, status_code=401, headers={"Access-Control-Allow-Origin": "*"})

        key_info = await asyncio.to_thread(auth_service.validate_key, api_key)
        if not key_info:
            return JSONResponse({
                "success": False,
                "error": "Ogiltig eller inaktiv API-nyckel. Kontakta support eller ansök om ny nyckel."
            }, status_code=403, headers={"Access-Control-Allow-Origin": "*"})

        rl_err = await asyncio.to_thread(_check_rate_limit, api_key)
        if rl_err:
            return JSONResponse(rl_err, status_code=429, headers={"Access-Control-Allow-Origin": "*"})

        func = DIRECT_TOOLS_MAP[tool_name]

        # Validera parameternamnen innan anropet. Gors det inte blir ett
        # stavfel hos anroparen ett TypeError som ser ut som ett serverfel.
        giltiga = set(inspect.signature(func).parameters)
        okanda = sorted(set(body) - giltiga)
        if okanda:
            return JSONResponse({
                "success": False,
                "error": f"Okand(a) parameter(rar): {', '.join(okanda)}.",
                "valid_parameters": sorted(giltiga - {"api_key"}),
            }, status_code=400, headers={"Access-Control-Allow-Origin": "*"})

        t0 = time.time()
        try:
            result = await asyncio.to_thread(func, **body)
        except (TypeError, ValueError) as e:
            # Fel typ eller otillatet varde - anroparens fel, inte serverns.
            # Detaljen loggas, men gar inte ut: den har formen
            # "'<=' not supported between instances of 'str' and 'int'", vilket
            # inte hjalper anroparen och rojer interna detaljer.
            logging.warning("Ogiltiga argument till %s", tool_name)
            return JSONResponse({
                "success": False,
                "error": "Ett eller flera varden har fel typ eller format.",
                "valid_parameters": sorted(giltiga - {"api_key"}),
            }, status_code=400, headers={"Access-Control-Allow-Origin": "*"})

        duration_ms = (time.time() - t0) * 1000


        return JSONResponse({
            "success": True,
            "tool": tool_name,
            "execution_time_ms": round(duration_ms, 2),
            "result": result
        }, headers={"Access-Control-Allow-Origin": "*"})
    except Exception:
        # Genuint serverfel. Meddelandet loggas men returneras aldrig - samma
        # except fangar fel fran Firestore, embedder och natverkslager, vars
        # texter kan innehalla projekt-id och sokvagar.
        logging.error("Fel vid anrop av verktyget")
        return JSONResponse({
            "success": False,
            "error": "Internt fel vid korning av verktyget."
        }, status_code=500, headers={"Access-Control-Allow-Origin": "*"})

def _check_rate_limit(api_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
    if api_key and (len(api_key) > 512 or not auth_service.validate_key(api_key)):
        return {"error": "Ogiltig eller inaktiv API-nyckel.", "status": "unauthorized"}
    client_id = api_key if api_key else "anon"
    limit = 300 if api_key else 60
    if not auth_service.check_rate_limit(client_id, max_requests=limit, window_seconds=60):
        return {
            "error": f"Rate limit exceeded (max {limit} förfrågningar/minut). Vänligen vänta en kort stund innan du skickar fler anrop.",
            "status": "rate_limited"
        }
    return None

@mcp.tool()
@tracked_tool
def get_legal_coverage(api_key: Optional[str] = None) -> Dict[str, Any]:
    """Visar land, språk, officiell källa och vilka specialområden som stöds."""
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    return _get_legal_coverage()

@mcp.tool()
@tracked_tool
def lookup_statute(law: str, section: str, chapter: Optional[str] = None, jurisdiction: str = "SE", api_key: Optional[str] = None) -> Dict[str, Any]:
    """Slå upp en paragraf i SE, DK, FI, NO, DE eller ES. Spanien använder artikelnummer, t.ex. section='20 bis'."""
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _lookup_statute(law=law, section=section, chapter=chapter, jurisdiction=jurisdiction)
    return res

@mcp.tool()
@tracked_tool
def search_labor_law(query: str, jurisdiction: Optional[str] = None, language: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, limit: int = 5, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """Sök arbetsrätt i SE, DK, FI, NO, DE eller ES. Använd källspråket nb/de/es för NO/DE/ES."""
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return [rl_err]
    t0 = time.time()
    res = _search_labor_law(query=query, jurisdiction=jurisdiction, language=language, filters=filters, limit=limit)
    return res

@mcp.tool()
@tracked_tool
def search_case_law(query: str, statute_ref: Optional[str] = None, year_from: Optional[int] = None, limit: int = 10, jurisdiction: str = "SE", api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return [rl_err]
    t0 = time.time()
    res = _search_case_law(query=query, statute_ref=statute_ref, year_from=year_from, limit=limit, jurisdiction=jurisdiction)
    return res

@mcp.tool()
@tracked_tool
def get_cba_exception(statute: str, section: str, agreement_name: str, jurisdiction: str = "SE", api_key: Optional[str] = None) -> Dict[str, Any]:
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _get_cba_exception(statute=statute, section=section, agreement_name=agreement_name, jurisdiction=jurisdiction)
    return res

@mcp.tool()
@tracked_tool
def compare_statute_vs_cba(topic: str, agreement_name: str, jurisdiction: str = "SE", api_key: Optional[str] = None) -> Dict[str, Any]:
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _compare_statute_vs_cba(topic=topic, agreement_name=agreement_name, jurisdiction=jurisdiction)
    return res

@mcp.tool()
@tracked_tool
def calculate_notice_period(
    employment_years: float,
    terminated_by: str = "employer",
    agreement_name: Optional[str] = None,
    age: Optional[int] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Beräknar uppsägningstid enligt LAS 11 § utifrån sammanlagd anställningstid
    (LAS 3 §), och visar avvikelser i tillämpligt kollektivavtal.

    Trappan i 11 § andra stycket gäller endast när arbetsgivaren säger upp.
    Vid arbetstagarens egen uppsägning gäller en månad oavsett anställningstid.
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _calculate_notice_period(
        employment_years=employment_years,
        terminated_by=terminated_by,
        agreement_name=agreement_name,
        age=age
    )
    return res

@mcp.tool()
@tracked_tool
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
    return res

@mcp.tool()
@tracked_tool
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
    return res

@mcp.tool()
@tracked_tool
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
    return res

@mcp.tool()
@tracked_tool
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
    return res

@mcp.tool()
@tracked_tool
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
    return res

@mcp.tool()
@tracked_tool
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
    return res

@mcp.tool()
@tracked_tool
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
    return res

@mcp.tool()
@tracked_tool
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
    return res

@mcp.tool()
@tracked_tool
def generate_turordningslista_excel(
    company_name: str = "Företaget AB",
    employees: Optional[List[Dict[str, Any]]] = None,
    redundancy_count: Optional[int] = 0,
    cba_name: Optional[str] = "Unionen / Tjänstemannaavtalet",
    single_operating_unit: bool = False,
    as_of_date: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Skapar och genererar en nedladdningsbar Excel-fil (.xlsx) med formaterad turordningslista vid arbetsbrist.
    Inkluderar ID-kolumn (EMP-001...), beräkning av anställningsdagar via Excel-formler (=DATEDIF),
    sortering efter anställningstid (sist in, först ut) och ålder, samt undantagsregler (LAS 22 § och kollektivavtal).
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _generate_turordningslista_excel(
        company_name=company_name,
        employees=employees,
        redundancy_count=redundancy_count,
        cba_name=cba_name,
        single_operating_unit=single_operating_unit,
        as_of_date=as_of_date
    )
    return res
@mcp.tool()
@tracked_tool
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
    date_str: Optional[str] = None,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Hämtar och anpassar officiella svenska HR-dokumentmallar enligt SKR / LAS-standard:
    1. 'omplaceringsutredning' (7 § andra stycket LAS - arbetsbrist / personliga skäl)
    2. 'omplaceringserbjudande' (skriftligt erbjudande med svarsfält Ja/Nej och signatur)
    3. 'varsel_personliga_skal' (Varsel till facklig organisation enligt 30 § LAS)
    4. 'underrattelse_personliga_skal' (Underrättelse till arbetstagaren enligt 30 § LAS)
    5. 'uppsagningsbesked_arbetsbrist' (Uppsägningsbesked vid arbetsbrist med företrädesrätt 8 § & 25 § LAS)
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _get_hr_document_template(
        template_type=template_type,
        company_name=company_name,
        employee_name=employee_name,
        personal_identity_number=personal_identity_number,
        job_title=job_title,
        workplace_location=workplace_location,
        reason_type=reason_type,
        union_name=union_name,
        offered_position_title=offered_position_title,
        offered_position_terms=offered_position_terms,
        response_deadline=response_deadline,
        date_str=date_str
    )
    return res

@mcp.tool()
@tracked_tool
def calculate_travel_deduction_and_mileage(
    transport_mode: Optional[str] = "egen_bil",
    distance_km_one_way: float = 25.0,
    work_days_per_year: int = 210,
    public_transit_time_minutes_roundtrip: Optional[int] = None,
    car_time_minutes_roundtrip: Optional[int] = None,
    public_transit_cost_yearly: Optional[float] = 0.0,
    tax_year: int = 2026,
    has_public_transit: bool = True,
    marginal_tax_pct: float = 32.0,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Beräknar Skatteverkets reseavdrag för resor till och från arbetet (egen bil 25 kr/mil, förmånsbil el 9.50 kr/mil, bensin/diesel 12 kr/mil, moped, cykel 350 kr/år, kollektivtrafik).
    Hanterar självrisknivåer (15 000 kr för 2026, 11 000 kr för 2025), tidsvinstkrav (minst 2 timmar) och avståndskrav (minst 5 km / 2 km).
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _calculate_travel_deduction_and_mileage(
        transport_mode=transport_mode or "egen_bil",
        distance_km_one_way=distance_km_one_way,
        work_days_per_year=work_days_per_year,
        public_transit_time_minutes_roundtrip=public_transit_time_minutes_roundtrip,
        car_time_minutes_roundtrip=car_time_minutes_roundtrip,
        public_transit_cost_yearly=public_transit_cost_yearly,
        tax_year=tax_year,
        has_public_transit=has_public_transit,
        marginal_tax_pct=marginal_tax_pct
    )
    return res

@mcp.tool()
@tracked_tool
def get_base_amounts_and_indices(
    year: Optional[int] = 2026,
    compare_all_years: bool = False,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Hämtar officiella prisbasbelopp (PBB), förhöjt prisbasbelopp, inkomstbasbelopp (IBB) och inkomstindex
    från SCB och Regeringen/Pensionsmyndigheten för 2026, 2025, 2024 m.fl.
    Inkluderar automatisk årlig hämtning/kontrollfunktion för 1 januari.
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _get_base_amounts_and_indices(
        year=year,
        compare_all_years=compare_all_years
    )
    return res

@mcp.tool()
@tracked_tool
def search_parliament_and_legislation(
    query: str,
    doc_type: Optional[str] = None,
    limit: int = 5,
    page: int = 1,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Söker live i Riksdagens Öppna Data API (data.riksdagen.se) efter propositioner (prop),
    Statens offentliga utredningar (sou), utskottsbetänkanden (bet), departementsserien (ds) och lagförslag.
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _search_parliament_and_legislation(
        query=query,
        doc_type=doc_type,
        limit=limit,
        page=page
    )
    return res

@mcp.tool()
@tracked_tool
def get_parliament_document_details(
    dok_id: str,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Hämtar detaljerad status, förslag, beslutsprocess, bilagor och textutdrag för ett specifikt
    dokument från Riksdagen (t.ex. 'HD03304', 'sfs-1982-80', 'prop-202122-176').
    """
    rl_err = _check_rate_limit(api_key)
    if rl_err:
        return rl_err
    t0 = time.time()
    res = _get_parliament_document_details(dok_id=dok_id)
    return res

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    if "PORT" in os.environ:
        mcp.run(transport="http", host="0.0.0.0", port=port,
                middleware=[Middleware(RequestSizeLimit)],
                uvicorn_config={"proxy_headers": False, "access_log": False})
    else:
        mcp.run()
