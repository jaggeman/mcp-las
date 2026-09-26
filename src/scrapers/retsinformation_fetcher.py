"""Official Danish legislation adapter for Retsinformation's open APIs."""

import re
import unicodedata
import xml.etree.ElementTree as ET
from typing import Any, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from src.chunking.danish_law_chunker import DanishLawChunker
from src.chunking.law_chunker import StatuteSection
from src.data.danish_labor_law_catalog import DANISH_LABOR_LAW_CATALOG


class RetsinformationFetcher:
    API_URL = "https://api.retsinformation.dk/v1/Documents"
    SOURCE_BASE = "https://www.retsinformation.dk"
    CATALOG_URL = DANISH_LABOR_LAW_CATALOG[0]["source_listing_url"]

    @staticmethod
    def _key(value: str) -> str:
        value = unicodedata.normalize("NFKC", value or "").casefold()
        return re.sub(r"[^a-z0-9æøå]+", " ", value).strip()

    @staticmethod
    def _slug(value: str) -> str:
        value = unicodedata.normalize("NFKC", value or "").casefold()
        value = value.replace("æ", "ae").replace("ø", "o").replace("å", "a")
        return re.sub(r"[^a-z0-9]+", "-", value).strip("-")

    @classmethod
    def catalog_documents(cls) -> List[Dict[str, Any]]:
        """Resolve the bounded ministry catalogue to official XML documents.

        The Retsinformation change feed contains every changed Danish legal
        document.  It must therefore only be used for change detection, never
        as the initial labour-law catalogue.
        """
        response = requests.get(cls.CATALOG_URL, timeout=30)
        response.raise_for_status()
        response.encoding = "utf-8"
        soup = BeautifulSoup(response.text, "html.parser")
        entries = {cls._key(item["name"]): item for item in DANISH_LABOR_LAW_CATALOG}
        documents: List[Dict[str, Any]] = []
        seen = set()
        for anchor in soup.select("a[href]"):
            href = anchor.get("href", "")
            if "retsinformation.dk/eli/" not in href:
                continue
            anchor_key = cls._key(anchor.get_text(" ", strip=True))
            entry = entries.get(anchor_key)
            if not entry:
                entry = next((item for key, item in entries.items()
                              if anchor_key.startswith(key) or key.startswith(anchor_key)), None)
            if not entry:
                continue
            statute_id = cls._slug(entry["name"])
            if statute_id in seen:
                continue
            seen.add(statute_id)
            parts = urlsplit(href)
            clean = urlunsplit((parts.scheme or "https", parts.netloc, parts.path.rstrip("/"), "", ""))
            documents.append({
                "id": statute_id,
                "documentId": statute_id,
                "statute_id": statute_id,
                "catalog_name": entry["name"],
                "title": entry["name"],
                "aliases": entry.get("aliases", []),
                "category": entry.get("category"),
                "priority": entry.get("priority"),
                "href": f"{clean}/xml",
                "source_url": clean,
            })
        if not documents:
            raise ValueError("No Danish labour-law catalogue links found")
        return documents

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
    def fetch_document_html_text(cls, href: str) -> Tuple[Dict[str, Any], str]:
        """Read document HTML from Retsinformation's own web application API.

        A minority of older ELI ``/xml`` resources only contain metadata.  The
        official site still renders their full text through this endpoint, so
        use it as a bounded fallback rather than silently publishing zero
        sections.
        """
        path = urlsplit(href.removesuffix("/xml")).path.lstrip("/")
        response = requests.post(
            f"{cls.SOURCE_BASE}/api/document/{path}",
            json={"isRawHtml": False},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or not payload or not payload[0].get("documentHtml"):
            raise ValueError("Retsinformation returned no document text")
        document = payload[0]
        soup = BeautifulSoup(document["documentHtml"], "html.parser")
        main_nodes = []
        for node in soup.find_all(recursive=False):
            classes = set(node.get("class") or [])
            if classes.intersection({"IKraftStreg", "IkraftTekst", "Fodnote"}):
                break
            main_nodes.append(node.get_text("\n", strip=True))
        text = "\n".join(part for part in main_nodes if part)
        return document, text

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
        statute_id = document.get("statute_id") or document_id
        title = document.get("catalog_name") or document.get("title") or metadata["title"]
        metadata.update({
            "id": f"DK:{statute_id}",
            "statute_id": statute_id,
            "title": title,
            "short_name": title,
            "source_url": document.get("source_url") or href.removesuffix("/xml"),
            "document_url": document.get("source_url") or href.removesuffix("/xml"),
            "aliases": document.get("aliases", []),
            "category": document.get("category"),
            "priority": document.get("priority"),
        })
        sections = DanishLawChunker.chunk_statute_text(
            statute_id=statute_id,
            statute_short=metadata["short_name"],
            full_text=text,
        )
        section_ids = [section.id for section in sections]
        if not sections or len(section_ids) != len(set(section_ids)):
            web_metadata, text = cls.fetch_document_html_text(href)
            sections = DanishLawChunker.chunk_statute_text(
                statute_id=statute_id,
                statute_short=metadata["short_name"],
                full_text=text,
            )
            metadata["document_id"] = str(web_metadata.get("id") or metadata["document_id"])
            metadata["document_type"] = web_metadata.get("documentTypeId")
        metadata["total_sections"] = len(sections)
        metadata.setdefault("document_type", (document.get("documentType") or {}).get("shortName"))
        return metadata, sections

    @classmethod
    def get_changed_laws(cls, date: Optional[str] = None) -> Iterable[Dict[str, Any]]:
        for document in cls.harvest_changes(date):
            document_type = ((document.get("documentType") or {}).get("shortName") or "").upper()
            if document_type in {"LOV", "LBK", "LOV H", "LBK H"}:
                yield document
