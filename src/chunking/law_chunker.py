import re
import logging
from typing import List, Dict, Any, Optional, Set
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

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
    preserving legal context and hierarchy while strictly rejecting
    inline line-broken cross-references and transitional provisions.
    """

    NON_START_PREV_WORDS: Set[str] = {
        'enligt', 'i', 'av', 'till', 'eller', 'och', 'samt', 'om', 'mot', 'från', 'under', 'med', 'på',
        'jfr', 'se', 'kap', 'kap.', 'paragraf', 'paragrafen', 'respektive', 'samtliga', 'mellan', 'hos', 'för',
        'strid', 'avseende', 'utan', 'efter', 'genom', 'vid', 'lydelse', 'lydelsen', 'nya', 'äldre', 'samtidigt'
    }

    INVALID_POST_STARTS = (
        ',', ';', '.', '–', '-', 'och ', 'eller ', 'samt ', 'som ', 'ska ', 'skall ', 'har ', 'hade ', 'kan ',
        'andra stycket', 'tredje stycket', 'fjärde stycket', 'femte stycket', 'punkten', 'stycket', 'meningen',
        'ogiltigförklarats', 'socialförsäkringsbalken', 'brottsbalken', 'skadeståndslagen', 'förvaltningsprocesslagen'
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

        # Strip transitional provisions (övergångsbestämmelser)
        trans_pattern = re.compile(
            r'(?:^|\n\n+)\s*(?:övergångsbestämmelser|ikraftträdande-?\s*och övergångsbestämmelser|ikraftträdandebestämmelser|föreskrifter om ikraftträdande)\b',
            re.IGNORECASE
        )
        trans_match = trans_pattern.search(cleaned)
        main_text = cleaned[:trans_match.start()] if trans_match else cleaned

        sections: List[StatuteSection] = []

        # Check for multi-chapter statutes
        chap_header_pattern = re.compile(r'(?:^|\n\n+)\s*(\d+)\s*kap(?:\.|\s+)([^\n]*)', re.IGNORECASE)
        chap_matches = list(chap_header_pattern.finditer(main_text))

        if len(chap_matches) > 1:
            for ci, cm in enumerate(chap_matches):
                curr_chapter = cm.group(1)
                c_start = cm.end()
                c_end = chap_matches[ci + 1].start() if ci + 1 < len(chap_matches) else len(main_text)
                c_block = main_text[c_start:c_end]
                cls._extract_sections_from_block(
                    statute_id=statute_id,
                    statute_short=statute_short,
                    block_text=c_block,
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

    @staticmethod
    def _is_heading(line: str) -> bool:
        line = line.strip()
        if not line or len(line) > 120:
            return False
        if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '-', '–', '(', '/')):
            return False
        if line.lower().endswith(('m.m.', 'm.fl.', 'm.m', 'm.fl', 'o.s.v.')):
            return True
        if line.endswith(('.', ':', ';', ',')):
            return False
        return True

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

        all_matches = list(pos_pattern.finditer(block_text))
        if not all_matches:
            return

        # Filter out false matches (line-broken cross references)
        valid_matches = []
        for m in all_matches:
            start_idx = m.start()
            pre_text = block_text[:start_idx].rstrip()
            pre_lines = pre_text.split('\n')
            last_pre_line = pre_lines[-1].strip() if pre_lines else ''
            last_words = re.findall(r'[a-zA-ZåäöÅÄÖ]+', last_pre_line.lower())
            last_w = last_words[-1] if last_words else ''

            # Check line after §
            post_chunk = block_text[m.end():m.end() + 120].lstrip()
            first_line = post_chunk.split('\n')[0] if post_chunk else ''

            # Reject if previous line ends with preposition, conjunction, comma, hyphen, etc.
            if last_pre_line.endswith((',', '-', '–', '(', '/')) or last_w in cls.NON_START_PREV_WORDS:
                continue

            # Reject if post line starts with invalid continuation words
            if any(first_line.lower().startswith(prefix) for prefix in cls.INVALID_POST_STARTS):
                continue

            valid_matches.append(m)

        if not valid_matches:
            return

        pending_heading = None
        first_pre = block_text[:valid_matches[0].start()].strip()
        if first_pre:
            first_lines = [l.strip() for l in first_pre.split('\n') if l.strip()]
            if first_lines and cls._is_heading(first_lines[-1]):
                pending_heading = first_lines[-1]

        seen_doc_ids: Set[str] = {s.id for s in sections}

        for i, m in enumerate(valid_matches):
            start_idx = m.end()
            end_idx = valid_matches[i + 1].start() if i + 1 < len(valid_matches) else len(block_text)

            inline_chap = m.group(1)
            sec_num = m.group(2).strip().lower()
            effective_chap = inline_chap if inline_chap else chapter

            safe_sfs = statute_id.replace(':', '_')
            chap_part = f"_k{effective_chap}" if effective_chap else ""
            doc_id = f"{safe_sfs}{chap_part}_s{sec_num}"

            # If this section was already added (e.g. future amendment vs current), handle cleanly
            if doc_id in seen_doc_ids:
                logger.warning(f"Duplicate doc_id {doc_id} skipped in SFS {statute_id}.")
                continue

            block_between = block_text[start_idx:end_idx].strip()
            lines = [l for l in block_between.split('\n')]
            while lines and not lines[-1].strip():
                lines.pop()

            curr_title = pending_heading
            pending_heading = None

            # Check if trailing lines belong to next section's heading
            if i + 1 < len(valid_matches) and len(lines) > 1:
                last_line = lines[-1].strip()
                if cls._is_heading(last_line):
                    pending_heading = last_line
                    lines.pop()
                    while lines and not lines[-1].strip():
                        lines.pop()


            content_cleaned = '\n'.join(lines).strip()
            if not content_cleaned:
                continue

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
            seen_doc_ids.add(doc_id)

    @staticmethod
    def _extract_keywords(text: str, statute_short: str, sec_num: str) -> List[str]:
        base_keywords = [
            statute_short.lower(),
            f"{statute_short.lower()} {sec_num} §",
            f"{sec_num} §",
            f"{sec_num} paragraf"
        ]
        legal_terms = [
            "uppsägning", "avskedande", "sakliga skäl", "saklig grund", "turordning",
            "anställningsavtal", "provanställning", "visstidsanställning", "tillsvidareanställning",
            "särskild visstidsanställning", "säsongsanställning", "vikariat", "undantag från turordning",
            "varsel", "underrättelse", "företrädesrätt", "återanställning", "skadestånd",
            "uppsägningstid", "lön", "semester", "semesterlön", "semesterersättning", "sparad semester",
            "mbl", "kollektivavtal", "primär förhandlingsskyldighet", "förhandlingsskyldighet",
            "arbetstid", "övertid", "mertid", "dygnsvila", "veckovila", "rast", "paus",
            "föräldraledighet", "föräldrapenning", "sjuklön", "karensavdrag", "arbetsmiljö",
            "skyddsombud", "skyddskommitté", "diskriminering", "repressalier", "aktiva åtgärder",
            "preskription", "tidsfrist", "ogiltigförklaring", "ogiltighet", "övergång av verksamhet"
        ]
        text_lower = text.lower()
        found = [term for term in legal_terms if term in text_lower]
        return list(set(base_keywords + found))

