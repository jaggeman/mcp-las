"""Bounded NL/GB labour-law adapters backed by official consolidated XML."""

import re
import xml.etree.ElementTree as ET
from datetime import date
from typing import Dict, Iterable, List, Tuple

import requests

from src.chunking.law_chunker import StatuteSection


DUTCH_LAWS = (
    ("BWBR0005290", "Burgerlijk Wetboek Boek 7 — arbeidsovereenkomst", "/Titeldeel10/"),
    ("BWBR0002638", "Wet minimumloon en minimumvakantiebijslag", None),
    ("BWBR0007671", "Arbeidstijdenwet", None),
    ("BWBR0010346", "Arbeidsomstandighedenwet", None),
    ("BWBR0013008", "Wet arbeid en zorg", None),
    ("BWBR0006502", "Algemene wet gelijke behandeling", None),
    ("BWBR0002747", "Wet op de ondernemingsraden", None),
    ("BWBR0009616", "Wet allocatie arbeidskrachten door intermediairs", None),
    ("BWBR0011173", "Wet flexibel werken", None),
)

UK_LAWS = (
    ("ukpga", 1996, 18, "Employment Rights Act 1996", 145),
    ("ukpga", 2010, 15, "Equality Act 2010"),
    ("uksi", 1998, 1833, "Working Time Regulations 1998"),
    ("ukpga", 1998, 39, "National Minimum Wage Act 1998"),
    ("ukpga", 1974, 37, "Health and Safety at Work etc. Act 1974"),
    ("uksi", 1999, 3312, "Maternity and Parental Leave etc. Regulations 1999"),
    ("uksi", 2006, 246, "Transfer of Undertakings (Protection of Employment) Regulations 2006"),
    ("uksi", 2010, 93, "Agency Workers Regulations 2010"),
    ("uksi", 2000, 1551, "Part-time Workers Regulations 2000"),
    ("uksi", 2002, 2034, "Fixed-term Employees Regulations 2002"),
)


def _local_name(element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _safe_id(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", value.casefold()).strip("-")


class OfficialLaborFetcher:
    NL_BASE = "https://repository.officiele-overheidspublicaties.nl/bwb"
    GB_BASE = "https://www.legislation.gov.uk"
    HEADERS = {"User-Agent": "MCP-LAS/1.0 (legal-source-sync)"}

    @classmethod
    def _download(cls, url: str) -> str:
        response = requests.get(url, timeout=90, headers=cls.HEADERS)
        response.raise_for_status()
        if len(response.content) > 25_000_000:
            raise ValueError("Official source document exceeds download limit")
        return response.content.decode(response.encoding or "utf-8", errors="replace")

    @staticmethod
    def select_dutch_item(manifest: str, today: date | None = None) -> str:
        today = today or date.today()
        root = ET.fromstring(manifest)
        candidates: List[Tuple[date, str]] = []
        for expression in root.findall("expression"):
            metadata = expression.find("metadata")
            if metadata is None:
                continue
            start_text = metadata.findtext("datum_inwerkingtreding")
            end_text = metadata.findtext("einddatum")
            if not start_text:
                continue
            start = date.fromisoformat(start_text)
            end = date.fromisoformat(end_text) if end_text else None
            if start <= today and (end is None or end >= today):
                manifestation = next((node for node in expression.findall("manifestation")
                                      if node.get("label") == "xml"), None)
                item = manifestation.find("item") if manifestation is not None else None
                if item is not None and item.get("label") and item.get("_deleted") != "true":
                    label = expression.get("label")
                    candidates.append((start, f"{label}/xml/{item.get('label')}"))
        if not candidates:
            raise ValueError("No Dutch statute version is currently in force")
        return max(candidates, key=lambda candidate: candidate[0])[1]

    @classmethod
    def parse_dutch(cls, document: Dict, payload: str):
        root = ET.fromstring(payload)
        sections = []
        seen = set()
        path_prefix = document.get("path_prefix")
        for article in (node for node in root.iter() if _local_name(node) == "artikel"):
            path = article.get("bwb-ng-variabel-deel", "")
            if path_prefix and path_prefix not in path:
                continue
            heading = next((node for node in article if _local_name(node) == "kop"), None)
            heading_children = list(heading) if heading is not None else []
            number_node = next((node for node in heading_children if _local_name(node) == "nr"), None)
            title_node = next((node for node in heading_children if _local_name(node) == "titel"), None)
            number = _clean_text("".join(number_node.itertext()) if number_node is not None else "")
            number = number.removeprefix("Artikel ").strip()
            if not number or number in seen:
                continue
            seen.add(number)
            content_parts = []
            for child in article:
                if _local_name(child) in {"kop", "meta-data"}:
                    continue
                value = _clean_text(" ".join(child.itertext()))
                if value:
                    content_parts.append(value)
            content = "\n".join(content_parts)
            if not content:
                continue
            chapter_match = re.search(r"/Hoofdstuk([^/]+)", path, re.I)
            chapter = chapter_match.group(1).replace("_", " ") if chapter_match else None
            title = _clean_text("".join(title_node.itertext()) if title_node is not None else "")
            sections.append(StatuteSection(
                id=f"nl-{document['id'].lower()}_s{_safe_id(number)}",
                statute_id=document["id"], statute_short=document["name"],
                chapter=chapter, section_number=number, section_title=title or None,
                content=content, raw_text=f"Artikel {number} {title}\n{content}".strip(),
                keywords=[document["name"].lower(), f"artikel {number}", "nederland", "arbeidsrecht"],
            ))
        if not sections:
            raise ValueError(f"No Dutch articles parsed for {document['id']}")
        metadata = {
            "id": f"NL:{document['id']}", "statute_id": document["id"],
            "short_name": document["name"], "title": document["name"],
            "source": "KOOP Basiswettenbestand", "source_url": f"https://wetten.overheid.nl/{document['id']}",
            "jurisdiction": "NL", "language": "nl", "total_sections": len(sections),
        }
        return metadata, sections

    @staticmethod
    def _akn_text(node) -> str:
        excluded = {"note", "commentary", "authorialNote", "meta"}
        parts = []
        if node.text and _clean_text(node.text):
            parts.append(node.text)
        for child in node:
            if _local_name(child) not in excluded:
                parts.append(OfficialLaborFetcher._akn_text(child))
            if child.tail and _clean_text(child.tail):
                parts.append(child.tail)
        return _clean_text(" ".join(parts))

    @classmethod
    def parse_uk(cls, document: Dict, payload: str):
        root = ET.fromstring(payload)
        sections = []
        seen = set()
        def is_provision(node):
            name = _local_name(node)
            return name in {"section", "article"} or (name == "hcontainer" and node.get("name") == "regulation")

        for section in (node for node in root.iter() if is_provision(node)):
            number_node = next((node for node in section if _local_name(node) == "num"), None)
            heading_node = next((node for node in section if _local_name(node) == "heading"), None)
            number = _clean_text("".join(number_node.itertext()) if number_node is not None else "")
            number = number.rstrip(".")
            if not number or number in seen:
                continue
            numeric = re.match(r"\d+", number)
            if document.get("max_section") and numeric and int(numeric.group()) > document["max_section"]:
                continue
            seen.add(number)
            title = _clean_text("".join(heading_node.itertext()) if heading_node is not None else "")
            content_parts = [cls._akn_text(child) for child in section
                             if _local_name(child) not in {"num", "heading", "note", "commentary", "authorialNote", "meta"}]
            content = _clean_text(" ".join(content_parts))
            if not content or re.fullmatch(r"(?:repealed|revoked|omitted)\.?", content, re.I):
                continue
            e_id = section.get("eId", "")
            part_match = re.search(r"(?:part|chapter)-([A-Za-z0-9]+)", e_id, re.I)
            chapter = part_match.group(1) if part_match else re.split(r"[A-Za-z]", number, maxsplit=1)[0].rstrip(".-") or None
            sections.append(StatuteSection(
                id=f"gb-{_safe_id(document['id'])}_s{_safe_id(number)}",
                statute_id=document["id"], statute_short=document["name"],
                chapter=chapter, section_number=number, section_title=title or None,
                content=content, raw_text=f"Provision {number} {title}\n{content}".strip(),
                keywords=[document["name"].lower(), f"provision {number}", "united kingdom", "employment law"],
            ))
        if not sections:
            raise ValueError(f"No UK provisions parsed for {document['id']}")
        metadata = {
            "id": f"GB:{document['id']}", "statute_id": document["id"],
            "short_name": document["name"], "title": document["name"],
            "source": "legislation.gov.uk", "source_url": document["url"],
            "jurisdiction": "GB", "language": "en", "total_sections": len(sections),
            "license": "OGL-3.0", "attribution": "Crown copyright",
        }
        return metadata, sections

    @classmethod
    def iter_documents(cls, jurisdiction: str) -> Iterable:
        if jurisdiction == "NL":
            for bwb_id, name, path_prefix in DUTCH_LAWS:
                document = {"id": bwb_id, "name": name, "path_prefix": path_prefix}
                try:
                    base = f"{cls.NL_BASE}/{bwb_id}/"
                    manifest = cls._download(base)
                    item = cls.select_dutch_item(manifest)
                    yield cls.parse_dutch(document, cls._download(base + item))
                except Exception as exc:
                    yield {"id": f"NL:{bwb_id}"}, exc
        elif jurisdiction == "GB":
            for entry in UK_LAWS:
                kind, year, number, name, *bounds = entry
                base = f"{cls.GB_BASE}/{kind}/{year}/{number}"
                document = {"id": f"{kind}-{year}-{number}", "name": name, "url": base}
                if bounds:
                    document["max_section"] = bounds[0]
                try:
                    yield cls.parse_uk(document, cls._download(base + "/data.akn"))
                except Exception as exc:
                    yield {"id": f"GB:{document['id']}"}, exc
        else:
            raise ValueError("Only NL and GB are supported by this adapter")
