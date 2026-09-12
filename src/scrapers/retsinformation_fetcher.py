"""Official Danish legislation adapter for Retsinformation's open APIs."""

import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from src.chunking.danish_law_chunker import DanishLawChunker
from src.chunking.law_chunker import StatuteSection


class RetsinformationFetcher:
    API_URL = "https://api.retsinformation.dk/v1/Documents"
    SOURCE_BASE = "https://www.retsinformation.dk"

    @classmethod
    def harvest_changes(cls, date: Optional[str] = None) -> List[Dict[str, Any]]:
        params = {"date": date} if date else None
        response = requests.get(cls.API_URL, params=params, timeout=20)
        response.raise_for_status()
        documents = response.json()
        if not isinstance(documents, list):
            raise ValueError("Retsinformation returned an unexpected document list")
        return documents

    @classmethod
    def fetch_document_xml(cls, href: str) -> str:
        response = requests.get(href, timeout=20)
        response.raise_for_status()
        return response.text

    @classmethod
    def parse_document_xml(cls, document_id: str, href: str, xml: str) -> Tuple[Dict[str, Any], str]:
        root = ET.fromstring(xml)

        def local_name(tag: str) -> str:
            return tag.rsplit("}", 1)[-1].lower()

        nodes = list(root.iter())
        title_node = next((node for node in nodes if local_name(node.tag) == "title"), None)
        date_node = next((node for node in nodes if local_name(node.tag) in {"date", "issued", "dateissued"}), None)
        body_node = next((node for node in nodes if local_name(node.tag) in {"body", "text", "content"}), None)
        title = " ".join((title_node.itertext() if title_node is not None else [])) or document_id
        date = " ".join((date_node.itertext() if date_node is not None else [])) or None
        text = "\n".join(body_node.itertext()) if body_node is not None else "\n".join(root.itertext())
        text = re.sub(r"\n{3,}", "\n\n", text)
        metadata = {
            "id": f"DK:{document_id}",
            "document_id": document_id,
            "title": title,
            "short_name": title,
            "statute_id": document_id,
            "source": "Retsinformation",
            "source_url": href,
            "document_url": href.rsplit("/xml", 1)[0],
            "valid_from": date,
            "jurisdiction": "DK",
            "language": "da",
            "in_force": True,
        }
        return metadata, text

    @classmethod
    def get_document(cls, document: Dict[str, Any]) -> Tuple[Dict[str, Any], List[StatuteSection]]:
        document_id = document.get("documentId") or document.get("document_id") or document.get("id")
        href = document.get("href") or document.get("source_url")
        if not document_id or not href:
            raise ValueError("Retsinformation document lacks documentId or href")
        metadata, text = cls.parse_document_xml(document_id, href, cls.fetch_document_xml(href))
        sections = DanishLawChunker.chunk_statute_text(
            statute_id=document_id,
            statute_short=metadata["short_name"],
            full_text=text,
        )
        metadata["total_sections"] = len(sections)
        metadata["document_type"] = (document.get("documentType") or {}).get("shortName")
        return metadata, sections

    @classmethod
    def get_changed_laws(cls, date: Optional[str] = None) -> Iterable[Dict[str, Any]]:
        for document in cls.harvest_changes(date):
            document_type = ((document.get("documentType") or {}).get("shortName") or "").upper()
            if document_type in {"LOV", "LBK", "LOV H", "LBK H"}:
                yield document
