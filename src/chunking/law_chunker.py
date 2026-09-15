import re
import logging
from datetime import date
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

    # Riksdagen skriver ut bada lydelserna nar en paragraf har en beslutad men
    # annu inte ikrafttradd andring: den gallande markt "/Upphor att galla
    # I:<datum>/" och den kommande "/Trader i kraft I:<datum>/". Markningen ar
    # redaktionell, inte lagtext.
    VERSION_MARKER = re.compile(
        # Bokstaven före kolon skiljer sig åt: U för upphör, I för
        # ikraftträdande. Båda måste matcha — läses bara "I:" blir den
        # utgående lydelsen omarkerad och dess markeringsrad ligger kvar
        # överst i lagtexten.
        r'^\s*/\s*(träder i kraft|upphör att gälla)\s*[A-ZÅÄÖ]?\s*:\s*(\d{4}-\d{2}-\d{2})\s*/\s*',
        re.IGNORECASE
    )

    @classmethod
    def _read_version_marker(cls, text_after_section_sign: str):
        """('start'|'end', datum, antal tecken att klippa) eller (None, None, 0)."""
        m = cls.VERSION_MARKER.match(text_after_section_sign)
        if not m:
            return None, None, 0
        kind = 'start' if m.group(1).lower().startswith('träder') else 'end'
        try:
            when = date.fromisoformat(m.group(2))
        except ValueError:
            return None, None, 0
        return kind, when, m.end()

    @staticmethod
    def _version_in_force(versions, today: date) -> int:
        """Vilken av flera lydelser av samma paragraf galler i dag?

        versions: [(index, kind, datum)]. Returnerar index.

        En lydelse som tratt i kraft galler; har flera gjort det vinner den
        senaste. Har ingen gjort det ar det den utgaende ("upphor att galla"
        langre fram) som fortfarande galler. Faller allt annat bort tas den
        forsta - att lamna paragrafen helt utan text vore samre an att ta fel
        lydelse.
        """
        started = [(d, i) for i, k, d in versions if k == 'start' and d and d <= today]
        if started:
            return max(started)[1]
        still_running = [i for i, k, d in versions if k == 'end' and d and d > today]
        if still_running:
            return still_running[0]
        unmarked = [i for i, k, _ in versions if k is None]
        if unmarked:
            return unmarked[0]
        return versions[0][0]

    @staticmethod
    def _log_rejected(statute_id: str, match, reason: str) -> None:
        """En tyst filtrering göms tills den syns som konstiga svar.

        Loggas på DEBUG: vid en normal ingest av en hel lag förkastas
        korsreferenser i tiotal, och det är väntat — men när en paragraf
        saknas är det här spåret som visar varför.
        """
        logger.debug(
            "SFS %s: förkastade '%s §' som paragrafstart (%s).",
            statute_id, match.group(2).strip(), reason
        )

    @staticmethod
    def _order_key(sec_num: str):
        """'6 a' -> (6, 'a'), '6' -> (6, ''). Ger 6 < 6 a < 6 b < 7."""
        m = re.match(r'(\d+)\s*([a-zåäö]?)', sec_num.strip().lower())
        if not m:
            return (0, '')
        return (int(m.group(1)), m.group(2))

    @staticmethod
    def _longest_ascending_run(keys: List[Any]) -> Set[int]:
        """Index i den längsta strikt stigande delföljden av keys.

        O(n²) räcker gott: en lag har tiotal paragrafer, inte miljoner. Vid
        lika långa alternativ vinner det som börjar tidigast i texten, vilket
        gör resultatet oberoende av var i filen en dubblett råkar ligga.
        """
        n = len(keys)
        if n == 0:
            return set()
        best = [1] * n
        prev = [-1] * n
        for i in range(n):
            for j in range(i):
                if keys[j] < keys[i] and best[j] + 1 > best[i]:
                    best[i] = best[j] + 1
                    prev[i] = j
        end = max(range(n), key=lambda i: best[i])
        keep: Set[int] = set()
        while end != -1:
            keep.add(end)
            end = prev[end]
        return keep

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
                cls._log_rejected(statute_id, m, f"föregås av {last_w or last_pre_line[-1:]!r}")
                continue

            # Reject if post line starts with invalid continuation words
            if any(first_line.lower().startswith(prefix) for prefix in cls.INVALID_POST_STARTS):
                cls._log_rejected(statute_id, m, f"följs av {first_line[:24]!r}")
                continue

            # En paragraf börjar aldrig med gemen bokstav — lagtext inleds med
            # versal eller siffra. En korsreferens mitt i en mening gör det
            # aldrig. Regeln ersätter behovet av att fylla på INVALID_POST_STARTS
            # med ett ord per upptäckt bugg; listan ovan ligger kvar för de fall
            # där fortsättningen råkar vara versal.
            if first_line[:1].islower():
                cls._log_rejected(statute_id, m, f"gemen fortsättning {first_line[:24]!r}")
                continue

            valid_matches.append(m)

        if not valid_matches:
            return

        # Vilken lydelse gäller i dag? En paragraf med en beslutad men ännu
        # inte ikraftträdd ändring förekommer två gånger i källtexten. Den
        # icke gällande lydelsen tas bort HÄR, före ordningsfiltret, och dess
        # startposition sparas — annars sväljs dess text av paragrafen före,
        # som då innehåller två lydelser utan att något skiljer dem åt.
        today = date.today()
        markers = [
            cls._read_version_marker(block_text[m.end():m.end() + 80])
            for m in valid_matches
        ]

        groups: Dict[Any, List[int]] = {}
        for i, m in enumerate(valid_matches):
            groups.setdefault((m.group(1) or chapter, m.group(2).strip().lower()), []).append(i)

        superseded = set()
        for idxs in groups.values():
            if len(idxs) < 2 and markers[idxs[0]][0] is None:
                continue
            winner = cls._version_in_force(
                [(i, markers[i][0], markers[i][1]) for i in idxs], today
            )
            for i in idxs:
                if i != winner:
                    superseded.add(i)
                    cls._log_rejected(
                        statute_id, valid_matches[i],
                        f"ej gällande lydelse ({markers[i][0]} {markers[i][1]})"
                    )

        # Startpositionerna är gränser som klipper — till skillnad från en
        # förkastad korsreferens, vars text hör hemma i paragrafen före.
        cut_starts = sorted(valid_matches[i].start() for i in superseded)
        kept = [i for i in range(len(valid_matches)) if i not in superseded]
        marker_cuts = [markers[i][2] for i in kept]
        valid_matches = [valid_matches[i] for i in kept]

        # Paragrafnumren stiger genom en lag. En referens som tagit sig förbi
        # filtren ovan avslöjas av att den går baklänges.
        #
        # Filtreringen sker genom längsta strikt stigande delföljd, inte genom
        # att gå framåt och kasta allt som är lägre än det senast accepterade.
        # Det senare skulle göra en enstaka falsk "38 §" inne i 4 § till tyst
        # bortfall av alla paragrafer mellan 5 och 37 — ett värre fel än det
        # som skulle lagas. Delföljden behåller i stället den största mängd
        # träffar som faktiskt utgör en lag i ordning.
        keys = [cls._order_key(m.group(2)) for m in valid_matches]
        keep = cls._longest_ascending_run(keys)
        if len(keep) < len(valid_matches):
            for i, m in enumerate(valid_matches):
                if i not in keep:
                    cls._log_rejected(statute_id, m, "bryter paragrafordningen")
            marker_cuts = [c for i, c in enumerate(marker_cuts) if i in keep]
            valid_matches = [m for i, m in enumerate(valid_matches) if i in keep]

        pending_heading = None
        first_pre = block_text[:valid_matches[0].start()].strip()
        if first_pre:
            first_lines = [l.strip() for l in first_pre.split('\n') if l.strip()]
            if first_lines and cls._is_heading(first_lines[-1]):
                pending_heading = first_lines[-1]

        seen_doc_ids: Set[str] = {s.id for s in sections}

        for i, m in enumerate(valid_matches):
            start_idx = m.end() + marker_cuts[i]
            end_idx = valid_matches[i + 1].start() if i + 1 < len(valid_matches) else len(block_text)
            # En bortvald lydelse mellan den här paragrafen och nästa avslutar
            # innehållet här, i stället för att följa med in i det.
            for cut in cut_starts:
                if m.start() < cut < end_idx:
                    end_idx = cut
                    break

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

