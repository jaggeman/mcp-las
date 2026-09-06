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
        
        # Strip transitional provisions (övergångsbestämmelser) so they don't overwrite real sections
        trans_pattern = re.compile(
            r'(?:^|\n)\s*(?:övergångsbestämmelser|ikraftträdande-?\s*och övergångsbestämmelser)\b',
            re.IGNORECASE
        )
        trans_match = trans_pattern.search(cleaned)
        main_text = cleaned[:trans_match.start()] if trans_match else cleaned
        
        sections: List[StatuteSection] = []
        
        # Check for multi-chapter statutes
        chapter_splits = re.split(r'(?=(?:^|\n)\s*\d+\s*kap(?:\.|\s+))', main_text, flags=re.IGNORECASE)
        
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
                block_text=main_text,
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
        pos_pattern = re.compile(
            r'(?:^|\n)\s*(?:(\d+)\s*kap\.\s*)?(\d+\s*[a-z]?)\s*§',
            re.IGNORECASE
        )
        
        matches = list(pos_pattern.finditer(block_text))
        if not matches:
            return

        pending_heading = None
        # Extract initial heading for the very first section if present
        first_pre = block_text[:matches[0].start()].strip()
        if first_pre:
            first_lines = [l.strip() for l in first_pre.split('\n') if l.strip()]
            if first_lines:
                cand = first_lines[-1]
                if len(cand) < 100 and not cand.endswith(('.', ':', ';', ',')):
                    pending_heading = cand

        for i, m in enumerate(matches):
            start_idx = m.end()
            end_idx = matches[i + 1].start() if i + 1 < len(matches) else len(block_text)
            
            inline_chap = m.group(1)
            sec_num = m.group(2).strip().lower()
            block_between = block_text[start_idx:end_idx].strip()
            
            effective_chap = inline_chap if inline_chap else chapter
            
            lines = [l for l in block_between.split('\n')]
            while lines and not lines[-1].strip():
                lines.pop()
                
            curr_title = pending_heading
            pending_heading = None
            
            # Check if trailing lines belong to next section's heading
            if i + 1 < len(matches) and len(lines) > 1:
                last_line = lines[-1].strip()
                if (len(last_line) < 100 and 
                    not last_line.endswith(('.', ':', ';', ',')) and 
                    not last_line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '-', '–'))):
                    pending_heading = last_line
                    lines.pop()
                    while lines and not lines[-1].strip():
                        lines.pop()
                        
            content_cleaned = '\n'.join(lines).strip()
            
            safe_sfs = statute_id.replace(':', '_')
            chap_part = f"_k{effective_chap}" if effective_chap else ""
            doc_id = f"{safe_sfs}{chap_part}_s{sec_num}"

            keywords = cls._extract_keywords(content_cleaned + " " + (curr_title or ""), statute_short, sec_num)

            sections.append(StatuteSection(
                id=doc_id,
                statute_id=statute_id,
                statute_short=statute_short,
                chapter=effective_chap,
                section_number=sec_num,
                section_title=curr_title,
                content=content_cleaned,
                raw_text=f"{effective_chap + ' kap. ' if effective_chap else ''}{sec_num} § {content_cleaned}",
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
