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
    compare_statute_vs_cba as _compare_statute_vs_cba
)

mcp = FastMCP(
    name=settings.MCP_SERVER_NAME,
    instructions="Svensk Arbetsrätt & LAS MCP Server för AI-agenter och Claude."
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
        
        if not name or not email:
            return JSONResponse({"success": False, "message": "Namn och e-post krävs."}, status_code=400)
            
        if db_client.db:
            doc_ref = db_client.db.collection("key_requests").document()
            doc_ref.set({
                "name": name,
                "email": email,
                "company": company,
                "reason": reason,
                "status": "pending",
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            return JSONResponse({"success": True, "message": "Din ansökan har tagits emot! Vi återkommer via e-post."})
        else:
            return JSONResponse({"success": False, "message": "Databasfel."}, status_code=500)
    except Exception as e:
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)

@mcp.tool()
def lookup_statute(law: str, section: str, chapter: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
    t0 = time.time()
    res = _lookup_statute(law=law, section=section, chapter=chapter)
    auth_service.log_access(api_key or "anon", None, "lookup_statute", {"law": law, "section": section}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def search_labor_law(query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 5, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    t0 = time.time()
    res = _search_labor_law(query=query, filters=filters, limit=limit)
    auth_service.log_access(api_key or "anon", None, "search_labor_law", {"query": query}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def search_case_law(query: str, statute_ref: Optional[str] = None, year_from: Optional[int] = None, limit: int = 10, api_key: Optional[str] = None) -> List[Dict[str, Any]]:
    t0 = time.time()
    res = _search_case_law(query=query, statute_ref=statute_ref, year_from=year_from, limit=limit)
    auth_service.log_access(api_key or "anon", None, "search_case_law", {"query": query, "statute_ref": statute_ref}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def get_cba_exception(statute: str, section: str, agreement_name: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    t0 = time.time()
    res = _get_cba_exception(statute=statute, section=section, agreement_name=agreement_name)
    auth_service.log_access(api_key or "anon", None, "get_cba_exception", {"statute": statute, "section": section, "agreement": agreement_name}, (time.time() - t0)*1000)
    return res

@mcp.tool()
def compare_statute_vs_cba(topic: str, agreement_name: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    t0 = time.time()
    res = _compare_statute_vs_cba(topic=topic, agreement_name=agreement_name)
    auth_service.log_access(api_key or "anon", None, "compare_statute_vs_cba", {"topic": topic, "agreement": agreement_name}, (time.time() - t0)*1000)
    return res

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    if "PORT" in os.environ:
        mcp.run(transport="http", host="0.0.0.0", port=port)
    else:
        mcp.run()
