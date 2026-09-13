"""Deterministic parser for Finnish Finlex legislation in Akoma Ntoso XML."""

import re
import xml.etree.ElementTree as ET
from typing import List, Optional

from src.chunking.law_chunker import StatuteSection


class FinnishLawChunker:
    """Split Finlex XML into chapter-aware paragraph sections."""

    @staticmethod
    def _local_name(tag: str) -> str:
        return tag.rsplit("}", 1)[-1].lower()

    @classmethod
    def _text(cls, node: Optional[ET.Element]) -> str:
        if node is None:
            return ""
        return " ".join(part.strip() for part in node.itertext() if part.strip())

    @classmethod
    def chunk_xml(cls, statute_id: str, statute_short: str, xml: str) -> List[StatuteSection]:
        root = ET.fromstring(xml)
        sections: List[StatuteSection] = []
        safe_id = re.sub(r"[^a-z0-9_-]+", "-", statute_id.lower()).strip("-")

        for chapter in (node for node in root.iter() if cls._local_name(node.tag) == "chapter"):
            chapter_num = cls._text(next((child for child in chapter if cls._local_name(child.tag) == "num"), None))
            chapter_match = re.search(r"(\d+)", chapter_num)
            chapter_value = chapter_match.group(1) if chapter_match else None
            for section in (node for node in chapter.iter() if cls._local_name(node.tag) in {"section", "article"}):
                cls._append_section(sections, section, safe_id, statute_id, statute_short, chapter_value)

        if not sections:
            for section in (node for node in root.iter() if cls._local_name(node.tag) in {"section", "article"}):
                cls._append_section(sections, section, safe_id, statute_id, statute_short, None)

        return sections

    @classmethod
    def _append_section(
        cls,
        sections: List[StatuteSection],
        node: ET.Element,
        safe_id: str,
        statute_id: str,
        statute_short: str,
        chapter: Optional[str],
    ) -> None:
        children = list(node)
        num_node = next((child for child in children if cls._local_name(child.tag) == "num"), None)
        number_text = cls._text(num_node)
        match = re.search(r"(\d+\s*[a-z]?)\s*§?", number_text, re.IGNORECASE)
        if not match:
            return
        section_number = re.sub(r"\s+", "", match.group(1).lower())
        title_node = next((child for child in children if cls._local_name(child.tag) in {"heading", "title"}), None)
        content_nodes = [child for child in children if cls._local_name(child.tag) not in {"num", "heading", "title"}]
        content = " ".join(cls._text(child) for child in content_nodes if cls._text(child)).strip()
        if not content:
            return
        doc_id = f"fi-{safe_id}{f'_k{chapter}' if chapter else ''}_s{section_number}"
        if any(section.id == doc_id for section in sections):
            return
        section_title = cls._text(title_node) or None
        raw_prefix = f"{f'{chapter} luku ' if chapter else ''}{section_number} §"
        keywords = [statute_short.lower(), f"{section_number} §", "suomen laki", "finland"]
        sections.append(StatuteSection(
            id=doc_id,
            statute_id=statute_id,
            statute_short=statute_short,
            chapter=chapter,
            section_number=section_number,
            section_title=section_title,
            content=content,
            raw_text=f"{raw_prefix} {content}",
            keywords=keywords,
        ))
