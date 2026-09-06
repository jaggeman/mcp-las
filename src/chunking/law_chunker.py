import re
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class StatuteSection(BaseModel):
    id: str
    statute_id: str
    statute_short: str
    chapter: Optional[str] = None
    section_number: str
    section_title: Optional[str] = None
    content: str
    raw_text: str
    keywords: List[str] = Field(default_factory=list)
    embedding: Optional[List[float]] = None

class LawChunker:
    """
    Deterministic chunker for Swedish legal statutes (SFS).
    Splits strictly by Chapter (kapitel) and Section (paragraf / §),
    preserving legal context and hierarchy.
    """
    
    CHAPTER_HEADER_REGEX = re.compile(
        r'(?:^|\n)\s*(\d+)\s*kap(?:\.|\s+)(?:([^\n]+))?',
        re.IGNORECASE
    )

    @staticmethod
    def clean_text(text: str) -> str:
        text = text.replace('\xa0', ' ')
        text = re.sub(r'\r\n', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    @classmethod
    def chunk_statute_text(
        cls,
        statute_id: str,
        statute_short: str,
        full_text: str,
        default_chapter: Optional[str] = None
    ) -> List[StatuteSection]:
        cleaned = cls.clean_text(full_text)
        sections: List[StatuteSection] = []
        
        # Check for multi-chapter statutes
        chapter_splits = re.split(r'(?=(?:^|\n)\s*\d+\s*kap(?:\.|\s+))', cleaned, flags=re.IGNORECASE)
        
        if len(chapter_splits) > 1:
            for split in chapter_splits:
                if not split.strip():
                    continue
                chap_match = cls.CHAPTER_HEADER_REGEX.search(split)
                curr_chapter = chap_match.group(1) if chap_match else default_chapter
                cls._extract_sections_from_block(
                    statute_id=statute_id,
                    statute_short=statute_short,
                    block_text=split,
                    chapter=curr_chapter,
                    sections=sections
                )
        else:
            cls._extract_sections_from_block(
                statute_id=statute_id,
                statute_short=statute_short,
                block_text=cleaned,
                chapter=default_chapter,
                sections=sections
            )
            
        return sections

    @classmethod
    def _extract_sections_from_block(
        cls,
        statute_id: str,
        statute_short: str,
        block_text: str,
        chapter: Optional[str],
        sections: List[StatuteSection]
    ) -> None:
        # Match sections with optional preceding heading and inline chapter
        # Pattern captures:
        # group 1: optional inline chapter e.g. "2"
        # group 2: section number e.g. "7" or "7 a"
        # group 3: content until next section or end
        sec_split_pattern = re.compile(
            r'(?:^|\n)(?:([^\n]+)\n+)?(?:(\d+)\s*kap\.\s*)?(\d+\s*[a-z]?)\s*§\s*(.*?)(?=(?:\n(?:[^\n]+\n+)?(?:(?:\d+\s*kap\.\s*)?\d+\s*[a-z]?\s*§))|\Z)',
            re.DOTALL | re.IGNORECASE
        )
        
        # Simpler and more robust: find positions of all § occurrences
        pos_pattern = re.compile(
            r'(?:^|\n)\s*(?:(\d+)\s*kap\.\s*)?(\d+\s*[a-z]?)\s*§',
            re.IGNORECASE
        )
        
        matches = list(pos_pattern.finditer(block_text))
        for i, m in enumerate(matches):
            start_idx = m.end()
            end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(block_text)
            
            inline_chap = m.group(1)
            sec_num = m.group(2).strip().lower()
            content_raw = block_text[start_idx:end_idx].strip()
            
            effective_chap = inline_chap if inline_chap else chapter
            
            # Find heading preceding this section
            prev_end = matches[i - 1].end() if i > 0 else 0
            preceding_text = block_text[prev_end:m.start()].strip()
            
            sec_title = None
            if preceding_text:
                candidate_lines = [l.strip() for l in preceding_text.split('\n') if l.strip()]
                if candidate_lines:
                    last_line = candidate_lines[-1]
                    if len(last_line) < 80 and not last_line.endswith(('.', ':', ';')):
                        sec_title = last_line
            
            safe_sfs = statute_id.replace(':', '_')
            chap_part = f"_k{effective_chap}" if effective_chap else ""
            doc_id = f"{safe_sfs}{chap_part}_s{sec_num}"

            keywords = cls._extract_keywords(content_raw + " " + (sec_title or ""), statute_short, sec_num)

            sections.append(StatuteSection(
                id=doc_id,
                statute_id=statute_id,
                statute_short=statute_short,
                chapter=effective_chap,
                section_number=sec_num,
                section_title=sec_title,
                content=content_raw,
                raw_text=f"{effective_chap + ' kap. ' if effective_chap else ''}{sec_num} § {content_raw}",
                keywords=keywords
            ))

    @staticmethod
    def _extract_keywords(text: str, statute_short: str, sec_num: str) -> List[str]:
        base_keywords = [statute_short.lower(), f"{statute_short.lower()} {sec_num} §", f"{sec_num} §"]
        legal_terms = [
            "uppsägning", "avskedande", "sakliga skäl", "saklig grund", "turordning",
            "anställningsavtal", "provanställning", "visstidsanställning", "tillsvidareanställning",
            "varsel", "underrättelse", "företrädesrätt", "återanställning", "skadestånd",
            "uppsägningstid", "lön", "semester", "semesterersättning", "mbl", "kollektivavtal",
            "förhandling", "arbetstid", "övertid", "föräldraledighet", "diskriminering"
        ]
        text_lower = text.lower()
        found = [term for term in legal_terms if term in text_lower]
        return list(set(base_keywords + found))
