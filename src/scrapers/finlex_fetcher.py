"""Official Finnish legislation adapter for Finlex open data."""

import html as html_lib
import json
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests

from src.chunking.finnish_law_chunker import FinnishLawChunker
from src.chunking.law_chunker import StatuteSection
from src.data.finnish_labor_law_catalog import FINNISH_LABOR_LAW_CATALOG


class FinlexFetcher:
    API_URL = "https://opendata.finlex.fi/finlex/avoindata/v1"
    STATUTE_LIST_URL = f"{API_URL}/akn/fi/act/statute/list"
    USER_AGENT = "MCP-LAS/1.0 (legal-source-sync)"

    @classmethod
    def catalog_documents(cls) -> List[Dict[str, Any]]:
        documents = []
        for entry in FINNISH_LABOR_LAW_CATALOG:
            number, year = entry["act_number"].split("/", 1)
            # The ``act/statute`` endpoint is the originally enacted text.  It
            # silently left old wording in production for amended laws.  The
            # public legislation page is Finlex's current consolidated view.
            current_url = f"https://data.finlex.fi/fi/lainsaadanto/{year}/{number}"
            original_akn_uri = f"{cls.API_URL}/akn/fi/act/statute/{year}/{number}/fin@"
            documents.append({
                "id": entry["act_number"],
                "documentId": entry["act_number"],
                "statute_id": entry["act_number"],
                "akn_uri": original_akn_uri,
                "url": current_url,
                "xmlUrl": current_url,
                "title": entry["name"],
                "language": "fi",
                "format": "finlex-current-html",
                "category": entry.get("category"),
                "priority": entry.get("priority"),
            })
        return documents

    @staticmethod
    def _flight_records(page_html: str) -> Dict[str, Any]:
        """Decode the React Flight records embedded in a Finlex document page."""
        chunks: List[str] = []
        pattern = re.compile(
            r"<script[^>]*>\s*self\.__next_f\.push\((.*?)\)\s*</script>",
            re.DOTALL | re.IGNORECASE,
        )
        for match in pattern.finditer(page_html):
            try:
                payload = json.loads(html_lib.unescape(match.group(1)))
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(payload, list) and len(payload) >= 2 and payload[0] == 1:
                chunks.append(payload[1])

        records: Dict[str, Any] = {}
        for line in "".join(chunks).splitlines():
            record_id, separator, payload = line.partition(":")
            if not separator or not re.fullmatch(r"[0-9a-f]+", record_id):
                continue
            try:
                records[record_id] = json.loads(payload)
            except json.JSONDecodeError:
                continue
        return records

    @classmethod
    def _react_text(cls, value: Any, records: Dict[str, Any], seen=None) -> List[str]:
        """Resolve visible text while ignoring component names and CSS metadata."""
        seen = set() if seen is None else seen
        if isinstance(value, str):
            reference = re.fullmatch(r"\$L?([0-9a-f]+)", value)
            if reference:
                record_id = reference.group(1)
                if record_id in seen or record_id not in records:
                    return []
                return cls._react_text(records[record_id], records, seen | {record_id})
            return [] if value.startswith("$") else [value]
        if isinstance(value, dict):
            return cls._react_text(value.get("children"), records, seen)
        if isinstance(value, list):
            if len(value) >= 4 and value[0] == "$" and isinstance(value[3], dict):
                return cls._react_text(value[3].get("children"), records, seen)
            result: List[str] = []
            for child in value:
                result.extend(cls._react_text(child, records, seen))
            return result
        return []

    @classmethod
    def parse_current_page(
        cls, statute_id: str, statute_short: str, html: str,
    ) -> List[StatuteSection]:
        """Parse the Finnish view of a current Finlex consolidated-law page."""
        records = cls._flight_records(html)
        parsed: List[Dict[str, Any]] = []
        current_chapter: Optional[str] = None
        current_section: Optional[Dict[str, Any]] = None
        started = False

        for value in records.values():
            if not (isinstance(value, list) and len(value) >= 4 and value[0] == "$"
                    and isinstance(value[1], str) and isinstance(value[3], dict)):
                continue
            tag, props = value[1], value[3]
            element_id = str(props.get("id") or "")
            chapter_match = re.fullmatch(r"chp_(\d+)", element_id)
            section_match = re.fullmatch(r"chp_(\d+)__sec_([0-9a-z]+)", element_id)
            chapterless_match = re.fullmatch(r"sec_([0-9a-z]+)", element_id)

            if tag == "h3" and chapterless_match:
                section_number = chapterless_match.group(1)
                if any(row["chapter"] is None and row["section_number"] == section_number
                       for row in parsed):
                    break
                started = True
                heading_parts = [
                    re.sub(r"\s+", " ", part).strip()
                    for part in cls._react_text(props.get("children"), records)
                    if str(part).strip()
                ]
                title = next((part for part in reversed(heading_parts)
                              if not re.fullmatch(r"\d+\s*[a-z]?\s*§", part, re.I)
                              and not re.fullmatch(r"\([^)]*\)", part)), None)
                current_chapter = None
                current_section = {
                    "chapter": None,
                    "section_number": section_number,
                    "section_title": title,
                    "content_parts": [],
                }
                parsed.append(current_section)
                continue

            if tag == "h3" and chapter_match:
                chapter = chapter_match.group(1)
                if parsed and chapter == "1":
                    break  # the following document view is Swedish
                started = True
                current_chapter = chapter
                current_section = None
                continue

            if tag == "h4" and section_match and started:
                chapter, section_number = section_match.groups()
                if any(row["chapter"] == chapter and row["section_number"] == section_number
                       for row in parsed):
                    break  # duplicate IDs begin the parallel Swedish document view
                heading_parts = [
                    re.sub(r"\s+", " ", part).strip()
                    for part in cls._react_text(props.get("children"), records)
                    if str(part).strip()
                ]
                title = next((part for part in reversed(heading_parts)
                              if not re.fullmatch(r"\d+\s*[a-z]?\s*§", part, re.I)
                              and not re.fullmatch(r"\([^)]*\)", part)), None)
                current_chapter = chapter
                current_section = {
                    "chapter": chapter,
                    "section_number": section_number,
                    "section_title": title,
                    "content_parts": [],
                }
                parsed.append(current_section)
                continue

            if (tag == "section" and current_section is not None
                    and "subsection" in str(props.get("className") or "")):
                text = " ".join(cls._react_text(props.get("children"), records))
                text = re.sub(r"\s+", " ", text).strip()
                if text:
                    current_section["content_parts"].append(text)

        safe_id = re.sub(r"[^a-z0-9_-]+", "-", statute_id.lower()).strip("-")
        sections: List[StatuteSection] = []
        for row in parsed:
            content = " ".join(row["content_parts"]).strip()
            if not content:
                continue
            chapter = row["chapter"]
            number = row["section_number"]
            sections.append(StatuteSection(
                id=f"fi-{safe_id}{f'_k{chapter}' if chapter else ''}_s{number}",
                statute_id=statute_id,
                statute_short=statute_short,
                chapter=chapter,
                section_number=number,
                section_title=row["section_title"],
                content=content,
                raw_text=f"{f'{chapter} luku ' if chapter else ''}{number} § {content}",
                keywords=[statute_short.lower(), f"{number} §", "suomen laki", "finland"],
            ))
        if not sections:
            raise ValueError("Finlex current page did not contain Finnish legal sections")
        return sections

    @classmethod
    def harvest_statutes(
        cls,
        start_year: Optional[int] = None,
        end_year: Optional[int] = None,
        page: int = 1,
        limit: int = 5,
        language: str = "fin",
    ) -> List[Dict[str, Any]]:
        current_year = datetime.now().year
        explicit_range = start_year is not None or end_year is not None
        year_ranges = (
            [(start_year or current_year, end_year or current_year)]
            if explicit_range
            else [(year, year) for year in range(current_year, max(current_year - 4, 2000), -1)]
        )
        last_error: Optional[Exception] = None

        for range_start, range_end in year_ranges:
            params: Dict[str, Any] = {
                "format": "json",
                "page": page,
                "limit": limit,
                "sortBy": "dateIssued",
                "langAndVersion": f"{language}@",
                "typeStatute": "act",
                "categoryStatute": "new-statute",
                "startYear": range_start,
                "endYear": range_end,
            }
            response = requests.get(
                cls.STATUTE_LIST_URL,
                params=params,
                headers={"User-Agent": cls.USER_AGENT, "Accept": "application/json"},
                timeout=30,
            )
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                last_error = exc
                if explicit_range:
                    raise
                continue

            payload = response.json()
            if isinstance(payload, list):
                return payload
            for key in ("results", "items", "documents"):
                if isinstance(payload.get(key), list):
                    return payload[key]
            raise ValueError("Finlex returned an unexpected statute list")

        raise last_error or RuntimeError("Finlex returned no usable statute year")

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
        xml = cls.fetch_document_xml(xml_url)
        if document.get("format") == "finlex-current-html":
            statute_id = document.get("statute_id") or cls._statute_id(str(document_id))
            title = document.get("title") or document.get("name") or statute_id
            sections = cls.parse_current_page(statute_id, title, xml)
            metadata = {
                "id": f"FI:{statute_id}", "document_id": document_id,
                "statute_id": statute_id, "title": title, "short_name": title,
                "source": "Finlex", "source_url": document_url or xml_url,
                "document_url": document_url or xml_url, "valid_from": None,
                "jurisdiction": "FI", "language": document.get("language", "fi"),
                "in_force": True, "total_sections": len(sections),
                "category": document.get("category"), "priority": document.get("priority"),
            }
            return metadata, sections
        metadata, sections = cls.parse_document(
            document_id=document_id,
            document_url=document_url or xml_url,
            xml=xml,
            title=document.get("title") or document.get("name"),
            language=document.get("language", "fi"),
        )
        statute_id = document.get("statute_id")
        if statute_id and statute_id != metadata["statute_id"]:
            metadata["id"] = f"FI:{statute_id}"
            metadata["statute_id"] = statute_id
            sections = FinnishLawChunker.chunk_xml(
                statute_id, metadata["short_name"], xml
            )
        metadata["category"] = document.get("category")
        metadata["priority"] = document.get("priority")
        return metadata, sections

    @classmethod
    def get_changed_laws(cls, **kwargs: Any) -> Iterable[Dict[str, Any]]:
        return cls.harvest_statutes(**kwargs)

    @staticmethod
    def _statute_id(document_id: str) -> str:
        match = re.search(r"/(\d{4})/(\d+)(?:/[^/]+)?/?$", document_id)
        if match:
            return f"{match.group(1)}/{match.group(2)}"
        return document_id.rsplit("/", 1)[-1]
