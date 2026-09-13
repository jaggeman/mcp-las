"""Official Finnish legislation adapter for Finlex open data."""

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from src.chunking.finnish_law_chunker import FinnishLawChunker
from src.chunking.law_chunker import StatuteSection


class FinlexFetcher:
    API_URL = "https://opendata.finlex.fi/finlex/avoindata/v1"
    STATUTE_LIST_URL = f"{API_URL}/akn/fi/act/statute/list"
    USER_AGENT = "MCP-LAS/1.0 (legal-source-sync)"

    @classmethod
    def harvest_statutes(
        cls,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        page: int = 1,
        limit: int = 100,
        language: str = "fin",
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {
            "format": "json",
            "page": page,
            "limit": limit,
            "sortBy": "dateIssued",
            "langAndVersion": f"{language}@",
            "typeStatute": "act",
            "categoryStatute": "new-statute",
        }
        if start_year is not None:
            params["startYear"] = start_year
        if end_year is not None:
            params["endYear"] = end_year
        response = requests.get(
            cls.STATUTE_LIST_URL,
            params=params,
            headers={"User-Agent": cls.USER_AGENT, "Accept": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return payload
        for key in ("results", "items", "documents"):
            if isinstance(payload.get(key), list):
                return payload[key]
        raise ValueError("Finlex returned an unexpected statute list")

    @classmethod
    def fetch_document_xml(cls, url: str) -> str:
        response = requests.get(url, headers={"User-Agent": cls.USER_AGENT}, timeout=30)
        response.raise_for_status()
        return response.text

    @classmethod
    def parse_document(
        cls,
        document_id: str,
        document_url: str,
        xml: str,
        title: Optional[str] = None,
        language: str = "fi",
    ) -> Tuple[Dict[str, Any], List[StatuteSection]]:
        root = ET.fromstring(xml)
        def local_name(tag: str) -> str:
            return tag.rsplit("}", 1)[-1].lower()

        nodes = list(root.iter())
        if not title:
            title_node = next((node for node in nodes if local_name(node.tag) in {"frbrname", "title", "doctitle"}), None)
            title = title_node.attrib.get("value") if title_node is not None else None
            if not title and title_node is not None:
                title = " ".join(part.strip() for part in title_node.itertext() if part.strip())
            title = title or document_id
        date_node = next((node for node in nodes if local_name(node.tag) in {"frbrdate", "date"}), None)
        valid_from = date_node.attrib.get("date") if date_node is not None else None
        if not valid_from and date_node is not None:
            valid_from = " ".join(date_node.itertext()).strip() or None
        statute_id = cls._statute_id(document_id)
        sections = FinnishLawChunker.chunk_xml(statute_id, title, xml)
        metadata = {
            "id": f"FI:{statute_id}",
            "document_id": document_id,
            "statute_id": statute_id,
            "title": title,
            "short_name": title,
            "source": "Finlex",
            "source_url": document_url,
            "document_url": document_url,
            "valid_from": valid_from,
            "jurisdiction": "FI",
            "language": language,
            "in_force": True,
            "total_sections": len(sections),
        }
        return metadata, sections

    @classmethod
    def get_document(cls, document: Dict[str, Any]) -> Tuple[Dict[str, Any], List[StatuteSection]]:
        document_id = (
            document.get("id")
            or document.get("documentId")
            or document.get("document_id")
            or document.get("akn_uri")
        )
        document_url = (
            document.get("url")
            or document.get("href")
            or document.get("documentUrl")
            or document.get("akn_uri")
        )
        xml_url = document.get("xmlUrl") or document.get("xml_url") or document_url
        if not document_id or not xml_url:
            raise ValueError("Finlex document lacks id and XML URL")
        return cls.parse_document(
            document_id=document_id,
            document_url=document_url or xml_url,
            xml=cls.fetch_document_xml(xml_url),
            title=document.get("title") or document.get("name"),
            language=document.get("language", "fi"),
        )

    @classmethod
    def get_changed_laws(cls, **kwargs: Any) -> Iterable[Dict[str, Any]]:
        return cls.harvest_statutes(**kwargs)

    @staticmethod
    def _statute_id(document_id: str) -> str:
        match = re.search(r"/(\d{4})/(\d+)(?:/[^/]+)?/?$", document_id)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
        return document_id.rsplit("/", 1)[-1]
