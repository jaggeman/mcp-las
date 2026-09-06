import re
import requests
from typing import Dict, Any, Optional, List
from bs4 import BeautifulSoup
from pydantic import BaseModel
from src.chunking.law_chunker import LawChunker, StatuteSection

class StatuteMetadata(BaseModel):
    id: str
    sfs_number: str
    title: str
    short_name: str
    valid_from: Optional[str] = None
    in_force: bool = True
    document_url: Optional[str] = None
    total_sections: int = 0

class RiksdagenFetcher:
    """
    Client for fetching Swedish Statutes (SFS) from Riksdagens Öppna Data API.
    """
    
    BASE_SEARCH_URL = "https://data.riksdagen.se/dokumentlista/"
    BASE_DOC_URL = "https://data.riksdagen.se/dokument/"
    
    KNOWN_LABOR_LAWS = {
        "1982:80": {"short_name": "LAS", "title": "Lag (1982:80) om anställningsskydd"},
        "1976:580": {"short_name": "MBL", "title": "Lag (1976:580) om medbestämmande i arbetslivet"},
        "1977:480": {"short_name": "Semesterlagen", "title": "Semesterlag (1977:480)"},
        "1982:673": {"short_name": "Arbetstidslagen", "title": "Arbetstidslag (1982:673)"},
        "2008:567": {"short_name": "Diskrimineringslagen", "title": "Diskrimineringslag (2008:567)"},
        "1977:1160": {"short_name": "Arbetsmiljölagen", "title": "Arbetsmiljölag (1977:1160)"},
        "1991:1047": {"short_name": "Sjuklönelagen", "title": "Lag (1991:1047) om sjuklön"},
        "1995:584": {"short_name": "Föräldraledighetslagen", "title": "Föräldraledighetslag (1995:584)"},
    }

    @classmethod
    def sfs_to_doc_id(cls, sfs_number: str) -> str:
        # e.g. "1982:80" -> "sfs-1982-80"
        normalized = sfs_number.strip().replace(":", "-").replace(" ", "")
        return f"sfs-{normalized}"

    @classmethod
    def fetch_statute_html_or_text(cls, sfs_number: str) -> Optional[str]:
        doc_id = cls.sfs_to_doc_id(sfs_number)
        
        # 1. Try text format
        try:
            resp_text = requests.get(f"{cls.BASE_DOC_URL}{doc_id}.text", timeout=15)
            if resp_text.status_code == 200 and len(resp_text.text.strip()) > 200:
                return resp_text.text
        except Exception:
            pass
            
        # 2. Try html format
        try:
            resp_html = requests.get(f"{cls.BASE_DOC_URL}{doc_id}.html", timeout=15)
            if resp_html.status_code == 200 and len(resp_html.text.strip()) > 200:
                soup = BeautifulSoup(resp_html.text, "html.parser")
                # Strip scripts and styles
                for s in soup(["script", "style"]):
                    s.decompose()
                return soup.get_text("\n")
        except Exception:
            pass

        return None

    @classmethod
    def get_statute(cls, sfs_number: str) -> tuple[StatuteMetadata, List[StatuteSection]]:
        sfs_clean = sfs_number.strip().replace("SFS ", "")
        known_info = cls.KNOWN_LABOR_LAWS.get(sfs_clean, {
            "short_name": f"SFS {sfs_clean}",
            "title": f"SFS {sfs_clean}"
        })
        
        raw_text = cls.fetch_statute_html_or_text(sfs_clean)
        if not raw_text:
            raise ValueError(f"Could not fetch statute text for SFS {sfs_clean} from Riksdagen API.")

        sections = LawChunker.chunk_statute_text(
            statute_id=sfs_clean,
            statute_short=known_info["short_name"],
            full_text=raw_text
        )

        metadata = StatuteMetadata(
            id=sfs_clean,
            sfs_number=sfs_clean,
            title=known_info["title"],
            short_name=known_info["short_name"],
            document_url=f"{cls.BASE_DOC_URL}{cls.sfs_to_doc_id(sfs_clean)}.html",
            total_sections=len(sections)
        )

        return metadata, sections
