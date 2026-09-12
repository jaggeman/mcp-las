"""Deterministic parser for Danish legislation from Retsinformation."""

import re
from typing import List, Optional

from src.chunking.law_chunker import StatuteSection


class DanishLawChunker:
    """Split Danish legal text on Kapitel and paragraph markers such as ``§ 1.``."""

    @staticmethod
    def clean_text(text: str) -> str:
        text = text.replace("\xa0", " ").replace("\r\n", "\n")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @classmethod
    def chunk_statute_text(
        cls,
        statute_id: str,
        statute_short: str,
        full_text: str,
        default_chapter: Optional[str] = None,
    ) -> List[StatuteSection]:
        text = cls.clean_text(full_text)
        transition = re.search(r"(?:^|\n\n+)(?:ikrafttrædelse|ikrafttrædelsesbestemmelser|overgangsbestemmelser)\b", text, re.IGNORECASE)
        if transition:
            text = text[:transition.start()].rstrip()

        chapter_matches = list(re.finditer(r"(?:^|\n)\s*Kapitel\s+(\d+)(?:\s*[-–:]?\s*([^\n]*))?", text, re.IGNORECASE))
        blocks = []
        if chapter_matches:
            for index, match in enumerate(chapter_matches):
                end = chapter_matches[index + 1].start() if index + 1 < len(chapter_matches) else len(text)
                blocks.append((match.group(1), text[match.end():end]))
        else:
            blocks.append((default_chapter, text))

        sections: List[StatuteSection] = []
        for chapter, block in blocks:
            matches = list(re.finditer(r"(?:^|\n)\s*§\s*(\d+\s*[a-z]?)\s*\.?(?=\s|$)", block, re.IGNORECASE))
            for index, match in enumerate(matches):
                end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
                content = block[match.end():end].strip()
                if not content:
                    continue
                section_number = re.sub(r"\s+", "", match.group(1).lower())
                safe_id = re.sub(r"[^a-z0-9_-]+", "-", statute_id.lower()).strip("-")
                chapter_part = f"_k{chapter}" if chapter else ""
                doc_id = f"dk-{safe_id}{chapter_part}_s{section_number}"
                sections.append(StatuteSection(
                    id=doc_id,
                    statute_id=statute_id,
                    statute_short=statute_short,
                    chapter=chapter,
                    section_number=section_number,
                    content=content,
                    raw_text=f"{f'Kapitel {chapter} ' if chapter else ''}§ {section_number}. {content}",
                    keywords=[statute_short.lower(), f"§ {section_number}", "dansk ret", "danmark"],
                ))
        return sections
