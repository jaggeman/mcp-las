import re
import time
from typing import Optional, Dict, Any, List, Union
import httpx
from bs4 import BeautifulSoup

class RiksdagenAPIService:
    """
    Service för att söka och hämta propositioner, förarbeten, utskottsbetänkanden,
    SOU (Statens offentliga utredningar) och lagtexter direkt från Riksdagens Öppna Data API (data.riksdagen.se).
    """

    BASE_SEARCH_URL = "https://data.riksdagen.se/dokumentlista/"
    BASE_DOC_URL = "https://data.riksdagen.se/dokument/"
    BASE_DOCSTATUS_URL = "https://data.riksdagen.se/dokumentstatus/"

    DOKTYP_LABELS = {
        "prop": "Proposition (Regeringens lagförslag)",
        "sou": "Statens offentliga utredningar (SOU)",
        "bet": "Utskottsbetänkande",
        "sfs": "Svensk författningssamling (SFS lagtext)",
        "ds": "Departementsserien (Ds)",
        "mot": "Motion (Riksdagsledamöters förslag)",
        "rskr": "Riksdagsskrivelse (Riksdagens beslut till regeringen)",
        "skr": "Regeringens skrivelse",
        "f-bet": "Förenklat betänkande",
        "yttr": "Utskottsyttrande"
    }

    def __init__(self, cache_ttl_seconds: int = 86400):
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}

    def _get_from_cache(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if time.time() - entry["timestamp"] < self.cache_ttl_seconds:
                return entry["data"]
            else:
                del self._cache[key]
        return None

    def _set_cache(self, key: str, data: Any):
        self._cache[key] = {
            "data": data,
            "timestamp": time.time()
        }

    @staticmethod
    def _clean_html_text(raw_text: Optional[str]) -> str:
        if not raw_text:
            return ""
        soup = BeautifulSoup(raw_text, "html.parser")
        text = soup.get_text(" ")
        cleaned = re.sub(r"\s+", " ", text).strip()
        return cleaned

    @staticmethod
    def _normalize_url(url: Optional[str]) -> Optional[str]:
        if not url:
            return None
        url = url.strip()
        if url.startswith("//"):
            return f"https:{url}"
        if not url.startswith("http"):
            return f"https://data.riksdagen.se{url if url.startswith('/') else '/' + url}"
        return url

    def search_documents(
        self,
        query: str,
        doc_types: Optional[Union[List[str], str]] = None,
        limit: int = 5,
        page: int = 1
    ) -> Dict[str, Any]:
        """
        Söker efter riksdagsdokument, propositioner, utredningar och förarbeten.
        """
        query_str = (query or "").strip()
        if not query_str:
            return {
                "query": "",
                "total_hits": 0,
                "count": 0,
                "page": page,
                "documents": [],
                "source": "Riksdagens Öppna Data API (data.riksdagen.se)",
                "certainty": {
                    "score_pct": 100,
                    "badge": "🟢 100% — Riksdagens Officiella API",
                    "level": "OFFICIAL_API"
                }
            }

        if isinstance(doc_types, str):
            types_list = [t.strip().lower() for t in doc_types.split(",") if t.strip()]
        elif isinstance(doc_types, list):
            types_list = [str(t).strip().lower() for t in doc_types if str(t).strip()]
        else:
            types_list = ["prop", "sou", "bet", "sfs", "ds"]

        types_param = ",".join(types_list)
        limit_val = max(1, min(20, limit))

        cache_key = f"search:{query_str}:{types_param}:{limit_val}:{page}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        params = {
            "sok": query_str,
            "doktyp": types_param,
            "sz": str(limit_val),
            "p": str(page),
            "utformat": "json"
        }

        try:
            resp = httpx.get(self.BASE_SEARCH_URL, params=params, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                doc_list_root = data.get("dokumentlista", {})
                raw_docs = doc_list_root.get("dokument", [])
                total_traffar = int(doc_list_root.get("@traffar", len(raw_docs) if isinstance(raw_docs, list) else (1 if raw_docs else 0)))

                if isinstance(raw_docs, dict):
                    raw_docs = [raw_docs]
                elif not isinstance(raw_docs, list):
                    raw_docs = []

                parsed_docs = []
                for doc in raw_docs:
                    d_id = doc.get("id") or doc.get("dok_id")
                    d_type = (doc.get("doktyp") or doc.get("typ") or "").lower()
                    title = self._clean_html_text(doc.get("titel"))
                    rm = doc.get("rm", "")
                    bet = doc.get("beteckning", "")
                    designation = f"{rm}:{bet}" if rm and bet else (bet or rm or "")
                    pub_date = doc.get("datum") or doc.get("publicerad")
                    organ = doc.get("organ", "")
                    
                    summary = self._clean_html_text(doc.get("summary") or doc.get("notis") or "")
                    html_url = self._normalize_url(doc.get("dokument_url_html"))
                    text_url = self._normalize_url(doc.get("dokument_url_text"))

                    # Hitta PDF om tillgängligt
                    pdf_url = None
                    filbilaga = doc.get("filbilaga")
                    if isinstance(filbilaga, dict):
                        filer = filbilaga.get("fil", [])
                        if isinstance(filer, dict):
                            filer = [filer]
                        for f in filer:
                            if isinstance(f, dict) and f.get("typ") == "pdf":
                                pdf_url = self._normalize_url(f.get("url"))
                                break

                    parsed_docs.append({
                        "id": d_id,
                        "dok_id": (doc.get("dok_id") or d_id or "").upper(),
                        "title": title,
                        "doc_type": d_type,
                        "doc_type_name": self.DOKTYP_LABELS.get(d_type, d_type.upper()),
                        "designation": designation,
                        "date": pub_date,
                        "publisher_or_ministry": organ,
                        "summary": summary[:400] + ("..." if len(summary) > 400 else ""),
                        "url_html": html_url or f"https://data.riksdagen.se/dokument/{d_id}.html",
                        "url_text": text_url or f"https://data.riksdagen.se/dokument/{d_id}.text",
                        "pdf_url": pdf_url
                    })

                result = {
                    "query": query_str,
                    "doc_types": types_list,
                    "total_hits": total_traffar,
                    "count": len(parsed_docs),
                    "page": page,
                    "documents": parsed_docs,
                    "source": "Riksdagens Öppna Data API (data.riksdagen.se)",
                    "certainty": {
                        "score_pct": 100,
                        "badge": "🟢 100% — Riksdagens Officiella API",
                        "level": "OFFICIAL_API"
                    }
                }
                self._set_cache(cache_key, result)
                return result
        except Exception:
            pass

        # Return empty structured result on network error
        return {
            "query": query_str,
            "total_hits": 0,
            "count": 0,
            "page": page,
            "documents": [],
            "source": "Riksdagens Öppna Data API (data.riksdagen.se)",
            "error_note": "Kunde inte ansluta till Riksdagens API just nu eller ingen träff.",
            "certainty": {
                "score_pct": 90,
                "badge": "🟡 90% — API-anrop med fallback",
                "level": "OFFICIAL_API_FALLBACK"
            }
        }

    def get_document_details(self, dok_id: str) -> Dict[str, Any]:
        """
        Hämtar fullständig information, beslutsstatus, förslag och text för ett specifikt riksdagsdokument.
        """
        clean_id = (dok_id or "").strip().upper()
        if not clean_id:
            return {"error": "Dokument-ID krävs."}

        cache_key = f"details:{clean_id}"
        cached = self._get_from_cache(cache_key)
        if cached:
            return cached

        try:
            # 1. Hämta dokumentstatus (JSON)
            status_url = f"{self.BASE_DOCSTATUS_URL}{clean_id}.json"
            resp = httpx.get(status_url, timeout=10.0)
            
            doc_meta = {}
            proposals = []
            activities = []
            references = []
            attachments = []

            if resp.status_code == 200:
                status_json = resp.json().get("dokumentstatus", {})
                doc_meta = status_json.get("dokument", {}) or {}
                
                # Förslag
                forslag_data = status_json.get("dokforslag", {}).get("forslag", [])
                if isinstance(forslag_data, dict):
                    forslag_data = [forslag_data]
                for f in forslag_data:
                    if isinstance(f, dict):
                        proposals.append(self._clean_html_text(f.get("kammaren") or f.get("utskottet") or str(f)))

                # Aktiviteter
                akt_data = status_json.get("dokaktivitet", {}).get("aktivitet", [])
                if isinstance(akt_data, dict):
                    akt_data = [akt_data]
                for a in akt_data:
                    if isinstance(a, dict):
                        activities.append({
                            "code": a.get("kod"),
                            "name": a.get("namn"),
                            "date": a.get("datum"),
                            "status": a.get("status")
                        })

                # Referenser / relaterade dokument
                ref_data = status_json.get("dokreferens", {}).get("referens", [])
                if isinstance(ref_data, dict):
                    ref_data = [ref_data]
                for r in ref_data:
                    if isinstance(r, dict):
                        references.append({
                            "ref_type": r.get("referenstyp"),
                            "ref_id": r.get("ref_dok_id"),
                            "title": r.get("ref_dok_titel"),
                            "sub_type": r.get("ref_dok_subtyp")
                        })

                # Bilagor
                bilagor_data = status_json.get("dokbilaga", {}).get("bilaga", [])
                if isinstance(bilagor_data, dict):
                    bilagor_data = [bilagor_data]
                for b in bilagor_data:
                    if isinstance(b, dict):
                        attachments.append({
                            "title": b.get("dok_titel") or b.get("titel"),
                            "sub_type": b.get("subtyp"),
                            "url": self._normalize_url(b.get("fil_url"))
                        })

            # 2. Hämta textutdrag om möjligt
            text_content = ""
            try:
                text_resp = httpx.get(f"{self.BASE_DOC_URL}{clean_id}.text", timeout=10.0)
                if text_resp.status_code == 200:
                    text_content = text_resp.text
            except Exception:
                pass

            title = self._clean_html_text(doc_meta.get("titel")) or f"Dokument {clean_id}"
            doc_type = (doc_meta.get("doktyp") or "").lower()

            result = {
                "dok_id": clean_id,
                "title": title,
                "doc_type": doc_type,
                "doc_type_name": self.DOKTYP_LABELS.get(doc_type, doc_type.upper() if doc_type else "Dokument"),
                "designation": f"{doc_meta.get('rm', '')}:{doc_meta.get('beteckning', '')}" if doc_meta.get('rm') and doc_meta.get('beteckning') else doc_meta.get('beteckning', ''),
                "publication_date": doc_meta.get("datum") or doc_meta.get("publicerad"),
                "organ": doc_meta.get("organ"),
                "proposals": proposals,
                "activities_timeline": activities,
                "references": references,
                "attachments": attachments,
                "url_html": f"https://data.riksdagen.se/dokument/{clean_id}.html",
                "url_pdf": self._normalize_url(doc_meta.get("dokument_url_pdf")),
                "text_excerpt": text_content[:2000] if text_content else self._clean_html_text(doc_meta.get("notis")),
                "has_full_text": bool(len(text_content) > 0),
                "source": "Riksdagens Öppna Data API (data.riksdagen.se)",
                "certainty": {
                    "score_pct": 100,
                    "badge": "🟢 100% — Riksdagens Officiella API",
                    "level": "OFFICIAL_API"
                }
            }
            self._set_cache(cache_key, result)
            return result
        except Exception as e:
            return {
                "dok_id": clean_id,
                "title": f"Dokument {clean_id}",
                "url_html": f"https://data.riksdagen.se/dokument/{clean_id}.html",
                "error": str(e),
                "source": "Riksdagens Öppna Data API (data.riksdagen.se)",
                "certainty": {
                    "score_pct": 80,
                    "badge": "🟡 80% — Direktlänk till Riksdagen",
                    "level": "OFFICIAL_LINK_FALLBACK"
                }
            }

riksdagen_api_service = RiksdagenAPIService()
