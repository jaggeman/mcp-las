from typing import Optional, Dict, Any, List
from fastmcp import FastMCP
from src.config import settings
from src.mcp_tools.tools import (
    lookup_statute as _lookup_statute,
    search_labor_law as _search_labor_law,
    search_case_law as _search_case_law,
    get_cba_exception as _get_cba_exception,
    compare_statute_vs_cba as _compare_statute_vs_cba
)

# Initialize FastMCP Server
mcp = FastMCP(
    name=settings.MCP_SERVER_NAME,
    instructions="Svensk Arbetsrätt & LAS MCP Server. Indexerar och söker i lagar (LAS, MBL m.fl.), AD-praxis och kollektivavtal."
)

@mcp.tool()
def lookup_statute(law: str, section: str, chapter: Optional[str] = None) -> Dict[str, Any]:
    """
    Exakt hämtning av en specifik lagparagraf (t.ex. law='LAS', section='7').
    Returnerar gällande lagtext, rubrik och metadata.
    """
    return _lookup_statute(law=law, section=section, chapter=chapter)

@mcp.tool()
def search_labor_law(query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Semantisk och nyckelordsbaserad hybridsökning i svensk arbetsrättslagstiftning (LAS, MBL, Semesterlagen etc.).
    """
    return _search_labor_law(query=query, filters=filters, limit=limit)

@mcp.tool()
def search_case_law(query: str, statute_ref: Optional[str] = None, year_from: Optional[int] = None, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Söker i Arbetsdomstolens (AD) avgöranden och praxis.
    """
    return _search_case_law(query=query, statute_ref=statute_ref, year_from=year_from, limit=limit)

@mcp.tool()
def get_cba_exception(statute: str, section: str, agreement_name: str) -> Dict[str, Any]:
    """
    Undersöker om ett specifikt kollektivavtal (t.ex. Teknikavtalet) avviker från semidispositiva lagregler.
    """
    return _get_cba_exception(statute=statute, section=section, agreement_name=agreement_name)

@mcp.tool()
def compare_statute_vs_cba(topic: str, agreement_name: str) -> Dict[str, Any]:
    """
    Jämför lagens grundregel (t.ex. LAS uppsägningstid eller turordning) mot kollektivavtalets bestämmelser.
    """
    return _compare_statute_vs_cba(topic=topic, agreement_name=agreement_name)

if __name__ == "__main__":
    mcp.run()
