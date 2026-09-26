import math
import os
import re
import logging
import time
import json
import uuid
from collections import Counter, OrderedDict
from threading import RLock
from typing import List, Dict, Any, Optional
from src.config import settings
from src.embeddings.embedder import Embedder
from src.db.ad_cases_data import AD_PRECEDENTS_DATA
from src.db.cba_data import CBA_RULES_DATA

logger = logging.getLogger(__name__)


def firestore_document_id(value: Any) -> str:
    """Return one Firestore document path segment for an external identifier."""
    return str(value).replace(":", "_").replace("/", "_").replace("\\", "_")


class FirebaseLaborLawDB:
    def __init__(self):
        self.db = None
        self._local_statutes: Dict[str, Any] = {}
        self._local_sections: Dict[str, Any] = {}
        self._local_precedents: Dict[str, Any] = {}
        for c in AD_PRECEDENTS_DATA:
            c_copy = dict(c)
            if not c_copy.get("embedding"):
                c_copy["embedding"] = Embedder.get_embedding(c_copy.get("title", "") + " " + c_copy.get("summary", "") + " " + c_copy.get("domskal", ""))
            self._local_precedents[c_copy["id"]] = c_copy
        # Sas har, som _local_precedents ovan. Utan detta ar fallbacken i
        # get_cba_exception och compare_statute_vs_cba dod utanfor en
        # ingestionskorning. Ingen embedding behovs - bada metoderna
        # matchar pa strangar, aldrig pa vektor.
        self._local_rules: Dict[str, Any] = {r["id"]: dict(r) for r in CBA_RULES_DATA}
        self._cached_statute_sections: Optional[List[Dict[str, Any]]] = None
        self._cached_statute_sections_by_country = {}
        self._country_cache_at = {}
        self._country_cache_version = {}
        self._country_full_read_at = {}
        self._coverage_cache = None
        self._coverage_cache_at = 0
        self._sync_status_cache = None
        self._sync_status_cache_at = 0
        self._statute_cache_lock = RLock()
        self._cached_precedents: Optional[List[Dict[str, Any]]] = None
        self._init_firebase()

    def _init_firebase(self):
        if settings.USE_FIRESTORE_EMULATOR:
            os.environ["FIRESTORE_EMULATOR_HOST"] = settings.FIRESTORE_EMULATOR_HOST

        try:
            import firebase_admin
            from firebase_admin import credentials, firestore

            if not firebase_admin._apps:
                if settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                    cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                    firebase_admin.initialize_app(cred)
                elif settings.FIREBASE_PROJECT_ID:
                    firebase_admin.initialize_app(options={'projectId': settings.FIREBASE_PROJECT_ID})
                else:
                    firebase_admin.initialize_app()

            self.db = firestore.client()
            print("Successfully connected to Firebase Firestore.")
        except Exception as e:
            print(f"Firestore not initialized ({e}).")
            self.db = None

    def save_statute(self, metadata: Dict[str, Any]):
        doc_id = str(metadata.get("id", "")).replace(":", "_")
        self._local_statutes[doc_id] = metadata
        if not self.db:
            # Ingen databas: raden finns bara i minnet och forsvinner med
            # processen. Returnera det, sa anroparen inte rapporterar succe.
            return False
        try:
            self.db.collection("statutes").document(doc_id).set(metadata)
            return True
        except Exception as e:
            # Tidigare "pass". En svald skrivning gjorde att ingestionen
            # rapporterade rader den aldrig sparat.
            logger.warning("Kunde inte spara %s/%s: %s", "statutes", doc_id, e)
            return False

    def save_statute_section(self, section: Dict[str, Any]):
        section.setdefault("jurisdiction", "SE")
        section.setdefault("language", "sv")
        doc_id = section.get("id")
        if not section.get("embedding"):
            section["embedding"] = Embedder.get_embedding(section.get("raw_text", ""))
        self._local_sections[doc_id] = section
        with self._statute_cache_lock:
            self._cached_statute_sections = None
            self._cached_statute_sections_by_country = {}
            self._country_cache_at = {}
            self._coverage_cache = None
            self._search_indexes = OrderedDict()
        if not self.db:
            # Ingen databas: raden finns bara i minnet och forsvinner med
            # processen. Returnera det, sa anroparen inte rapporterar succe.
            return False
        try:
            self.db.collection("statute_sections").document(doc_id).set(section)
            return True
        except Exception as e:
            # Tidigare "pass". En svald skrivning gjorde att ingestionen
            # rapporterade rader den aldrig sparat.
            logger.warning("Kunde inte spara %s/%s: %s", "statute_sections", doc_id, e)
            return False

    def get_sync_state(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Read the last successful or failed synchronization state for a source."""
        if self.db:
            try:
                doc = self.db.collection("source_sync_state").document(source_id).get()
                if doc.exists:
                    return doc.to_dict()
            except Exception:
                pass
        return getattr(self, "_local_sync_state", {}).get(source_id)

    def get_sync_status_by_jurisdiction(self) -> Dict[str, Dict[str, Any]]:
        now = time.monotonic()
        if self._sync_status_cache is not None and now - self._sync_status_cache_at < 60:
            return {key: dict(value) for key, value in self._sync_status_cache.items()}
        countries = ("SE", "DK", "FI", "NO", "DE", "ES")
        statuses = {}
        if self.db:
            try:
                refs = [self.db.collection("source_sync_state").document(f"coverage:{code}")
                        for code in countries]
                for doc in self.db.get_all(refs):
                    if doc.exists:
                        code = str(doc.id).removeprefix("coverage:").upper()
                        if code in countries:
                            statuses[code] = doc.to_dict()
            except Exception:
                logger.warning("Synchronization status unavailable")
                statuses = self._sync_status_cache or {}
        else:
            local = getattr(self, "_local_sync_state", {})
            statuses = {code: dict(local[f"coverage:{code}"]) for code in countries
                        if f"coverage:{code}" in local}
        self._sync_status_cache = statuses
        self._sync_status_cache_at = now
        return {key: dict(value) for key, value in statuses.items()}

    def publish_statute(self, source_id, metadata, rows, statute_id, jurisdiction, state):
        """Atomically publish one bounded statute, retirement, metadata and state.

        Refuse oversized publications before writing; never split a law into commits.
        """
        if not self.db:
            raise RuntimeError('Database required for publication')
        from google.cloud.firestore_v1 import transactional
        from google.cloud.firestore_v1.base_query import FieldFilter
        if not rows or len(rows) > 447 or len(json.dumps(rows, ensure_ascii=False).encode('utf-8')) > 7_000_000:
            raise ValueError('Statute exceeds atomic publication limits')
        collection = self.db.collection('statute_sections')
        ids = {row['id'] for row in rows}
        if len(ids) != len(rows):
            raise ValueError('Duplicate section IDs')

        @transactional
        def publish(transaction):
            old = list(transaction.get(collection.where(filter=FieldFilter('statute_id', '==', statute_id))))
            retired = [doc for doc in old if doc.to_dict().get('jurisdiction', 'SE') == jurisdiction and doc.id not in ids and doc.to_dict().get('active', True)]
            if len(rows) + len(retired) + 3 > 450:
                raise ValueError('Statute exceeds atomic publication write limit')
            for row in rows:
                transaction.set(collection.document(row['id']), row)
            for doc in retired:
                transaction.update(doc.reference, {'active': False})
            transaction.set(self.db.collection('statutes').document(firestore_document_id(metadata['id'])), metadata)
            transaction.set(self.db.collection('source_sync_state').document(source_id), state)
            transaction.set(self.db.collection('cache_versions').document('statutes'), {'version': uuid.uuid4().hex})

        publish(self.db.transaction())
        with self._statute_cache_lock:
            self._cached_statute_sections = None
            self._cached_statute_sections_by_country = {}
            self._country_cache_at = {}
            self._coverage_cache = None
        return True

    def save_sync_state(self, source_id: str, state: Dict[str, Any]) -> bool:
        if not hasattr(self, "_local_sync_state"):
            self._local_sync_state = {}
        if self.db:
            try:
                self.db.collection("source_sync_state").document(source_id).set(state)
                self._local_sync_state[source_id] = dict(state)
                self._sync_status_cache = None
                return True
            except Exception:
                logger.exception('Could not persist sync state %s', source_id)
        return False

    def _get_statute_items(self, jurisdiction=None) -> List[Dict[str, Any]]:
        with self._statute_cache_lock:
            if jurisdiction:
                return self._refresh_country_items(str(jurisdiction).upper())
            return self._refresh_statute_items()

    def _statute_version_marker(self):
        marker = self.db.collection('cache_versions').document('statutes').get()
        return marker.to_dict().get('version') if marker.exists else None

    def _refresh_country_items(self, jurisdiction):
        now = time.monotonic()
        cache = getattr(self, '_cached_statute_sections_by_country', {})
        cache_at = getattr(self, '_country_cache_at', {})
        if jurisdiction in cache and now - cache_at.get(jurisdiction, 0) < 60:
            return cache[jurisdiction]
        if self.db:
            try:
                version = self._statute_version_marker()
                versions = getattr(self, '_country_cache_version', {})
                full_at = getattr(self, '_country_full_read_at', {})
                if (jurisdiction in cache and version is not None
                        and version == versions.get(jurisdiction)
                        and now - full_at.get(jurisdiction, 0) < 300):
                    cache_at[jurisdiction] = now
                    return cache[jurisdiction]
                from google.cloud.firestore_v1.base_query import FieldFilter
                query = self.db.collection('statute_sections').where(
                    filter=FieldFilter('jurisdiction', '==', jurisdiction))
                items = [doc.to_dict() for doc in query.stream()]
                versions[jurisdiction] = version
                full_at[jurisdiction] = now
                self._country_cache_version = versions
                self._country_full_read_at = full_at
            except Exception:
                raise RuntimeError('Statute database unavailable') from None
        else:
            items = [row for row in self._local_sections.values()
                     if str(row.get('jurisdiction', 'SE')).upper() == jurisdiction]
        items = [row for row in items if row.get('active', True)]
        cache[jurisdiction] = items
        cache_at[jurisdiction] = now
        self._cached_statute_sections_by_country = cache
        self._country_cache_at = cache_at
        return items

    def _refresh_statute_items(self) -> List[Dict[str, Any]]:
        if self._cached_statute_sections is not None and time.monotonic() - getattr(self, '_statute_cache_at', 0) < 60:
            return self._cached_statute_sections
        items = []
        if self.db:
            try:
                version = self._statute_version_marker()
                if (version is not None and self._cached_statute_sections is not None
                        and version == getattr(self, '_statute_version', None)
                        and time.monotonic() - getattr(self, '_statute_full_read_at', 0) < 300):
                    self._statute_cache_at = time.monotonic()
                    return self._cached_statute_sections
                docs = self.db.collection("statute_sections").stream()
                items = [d.to_dict() for d in docs]
                self._statute_version = version
                self._statute_full_read_at = time.monotonic()
            except Exception:
                raise RuntimeError('Statute database unavailable') from None
        else:
            items = list(self._local_sections.values())
        items = [row for row in items if row.get('active', True)]
        self._cached_statute_sections = items
        self._statute_cache_at = time.monotonic()
        return items

    def retire_missing_sections(self, statute_id, jurisdiction, active_ids):
        """Retain old records for recovery, but exclude them from active queries."""
        if not self.db or not active_ids:
            return False
        try:
            from google.cloud.firestore_v1.base_query import FieldFilter
            docs = self.db.collection('statute_sections').where(filter=FieldFilter('statute_id', '==', statute_id)).stream()
            for doc in docs:
                row = doc.to_dict()
                if row.get('jurisdiction', 'SE') == jurisdiction and doc.id not in active_ids:
                    doc.reference.update({'active': False})
            for row in self._local_sections.values():
                if row.get('statute_id') == statute_id and row.get('jurisdiction','SE') == jurisdiction and row['id'] not in active_ids:
                    row['active'] = False
            self._cached_statute_sections = None
            self._cached_statute_sections_by_country = {}
            self._country_cache_at = {}
            self._coverage_cache = None
            self._search_indexes = OrderedDict()
            return True
        except Exception:
            logger.exception('Could not retire stale sections for %s/%s', jurisdiction, statute_id)
            return False

    def _get_precedent_items(self) -> List[Dict[str, Any]]:
        if self._cached_precedents is not None:
            return self._cached_precedents
        items = []
        if self.db:
            try:
                docs = self.db.collection("precedents").stream()
                items = [d.to_dict() for d in docs]
            except Exception:
                pass
        if not items:
            items = list(self._local_precedents.values())
        if items:
            self._cached_precedents = items
        return items

    def count_sections_by_jurisdiction(self) -> Dict[str, int]:
        """Hur många ingesterade paragrafer finns per land, faktiskt.

        Anvands av get_legal_coverage sa att verktyget beskriver vad
        databasen innehaller istallet for vad koden i teorin stodjer -
        "SE" och "DK" ar bada kodade sedan lange, men bara SE har nagonsin
        fatt en fullstandig ingestion kord mot paygap-prod.

        Poster utan ett lagrat jurisdiction-falt rakans som SE, samma
        standardval som get_statute_section redan anvander for aldre
        poster som ingesterades innan faltet fanns.
        """
        if self.db:
            now = time.monotonic()
            coverage_cache = getattr(self, '_coverage_cache', None)
            coverage_cache_at = getattr(self, '_coverage_cache_at', 0)
            if coverage_cache is not None and now - coverage_cache_at < 60:
                return dict(coverage_cache)
            try:
                counts = {country: self._aggregate_country_count(country)
                          for country in ('SE', 'DK', 'FI', 'NO', 'DE', 'ES')}
                counts = {country: count for country, count in counts.items() if count}
                self._coverage_cache, self._coverage_cache_at = counts, now
                return dict(counts)
            except Exception:
                raise RuntimeError('Statute database unavailable') from None
        counts: Dict[str, int] = {}
        for s in self._get_statute_items():
            j = str(s.get("jurisdiction") or "SE").upper()
            counts[j] = counts.get(j, 0) + 1
        return counts

    def _aggregate_country_count(self, country):
        from google.cloud.firestore_v1.base_query import FieldFilter
        query = self.db.collection('statute_sections').where(
            filter=FieldFilter('jurisdiction', '==', country))
        total = query.count(alias='total').get()[0][0].value
        inactive = query.where(filter=FieldFilter('active', '==', False))
        retired = inactive.count(alias='total').get()[0][0].value
        return int(total - retired)

    def get_statute_section(self, law: str, section: str, chapter: Optional[str] = None, jurisdiction: str = "SE") -> Optional[Dict[str, Any]]:
        if not law.strip() or not section.strip():
            raise ValueError('Law and section must not be empty')
        law_clean = law.strip().upper()
        sec_clean = section.strip().lower().replace("§", "").strip()
        jurisdiction_clean = jurisdiction.strip().upper()

        items = self._get_statute_items(jurisdiction_clean)

        for s in items:
            short = s.get("statute_short", "").upper()
            sfs = s.get("statute_id", "").upper()
            stored_jurisdiction = str(s.get("jurisdiction", "SE")).upper()
            if (law_clean in short or law_clean in sfs) and stored_jurisdiction == jurisdiction_clean and s.get("section_number", "").lower() == sec_clean:
                if chapter:
                    if str(s.get("chapter")) == str(chapter):
                        return s
                else:
                    return s
        return None

    @staticmethod
    def _stem_sv(w: str) -> str:
        w = w.lower()
        for suffix in ('ingarna', 'ingens', 'ingen', 'ingar', 'arnas', 'ernas', 'ornas', 'arna', 'erna', 'orna', 'andet', 'anden', 'andes', 'ande', 'ades', 'ade', 'ats', 'tas', 'ets', 'ens', 'het', 'iga', 'igt', 'are', 'ast', 'ern', 'en', 'et', 'na', 'ar', 'er', 'or', 'at', 'ad', 'as', 'es', 'is', 'an', 'a', 'e'):
            if len(w) > len(suffix) + 3 and w.endswith(suffix):
                return w[:-len(suffix)]
        return w

    def _prepare_search_row(self, row):
        tokens = re.findall(r'[^\W_]+', row.get('content', '').lower())
        stems = [self._stem_sv(w) for w in tokens]
        title = re.findall(r'[^\W_]+', (row.get('section_title') or '').lower())
        keywords = re.findall(r'[^\W_]+', ' '.join(row.get('keywords', [])).lower())
        return tuple(Counter(values) for values in (tokens, stems, title,
            [self._stem_sv(w) for w in title], keywords, tokens[:25], stems[:25]))

    def _search_index(self, snapshot, filters):
        country = str(filters.get('jurisdiction') or filters.get('country') or '').upper()
        language = str(filters.get('language') or '').lower()
        key = (id(snapshot), country, language)
        with self._statute_cache_lock:
            indexes = getattr(self, '_search_indexes', None)
            if not isinstance(indexes, OrderedDict):
                indexes = OrderedDict(indexes or {})
                self._search_indexes = indexes
            entry = indexes.get(key)
            # Keeping the snapshot in the entry prevents Python from reusing an
            # object id and also lets several country caches remain warm.
            if entry is None or entry[0] is not snapshot:
                rows = [s for s in snapshot if
                    (not country or str(s.get('jurisdiction', 'SE')).upper() == country) and
                    (not language or str(s.get('language', 'sv')).lower() == language)]
                prepared = {id(s): self._prepare_search_row(s) for s in rows}
                frequencies = Counter()
                for s in rows:
                    counters = prepared[id(s)]
                    frequencies.update(set(counters[1]) | set(counters[3]) |
                        {self._stem_sv(w) for w in counters[4]})
                indexes[key] = snapshot, rows, frequencies, prepared
                indexes.move_to_end(key)
                while len(indexes) > 16:
                    indexes.popitem(last=False)
            else:
                indexes.move_to_end(key)
            _, rows, frequencies, prepared = indexes[key]
            return rows, frequencies, prepared

    def search_statute_sections(self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 5) -> List[Dict[str, Any]]:
        if not isinstance(query, str) or not query.strip() or len(query) > 2000:
            raise ValueError('Query must contain 1–2000 characters')
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ValueError('Limit must be an integer from 1 to 50')
        if filters is not None and not isinstance(filters, dict):
            raise ValueError('Filters must be an object')
        q_lower = query.lower()
        raw_tokens = re.findall(r'[^\W_]+', q_lower)
        from src.embeddings.embedder import SWEDISH_STOPWORDS
        meaningful_q = [w for w in raw_tokens if w not in SWEDISH_STOPWORDS and len(w) >= 2]
        if not meaningful_q:
            meaningful_q = raw_tokens

        SYNONYMS = {
            'avskeda': ['avskedande', 'avskedas', 'avsked'],
            'avsked': ['avskedande', 'avskeda'],
            'avskedande': ['avskeda', 'avskedas'],
            'anställd': ['arbetstagare', 'anställning', 'anställda'],
            'varsel': ['varsla', 'underrättelse', 'underrätta'],
            'varsla': ['varsel', 'underrätta', 'underrättelse'],
            'semesterdagar': ['semesterdag', 'semester', 'semesterledighet', 'tjugofem'],
            'dygnsvilan': ['dygnsvila'],
            'dygnsvila': ['elva timmars', 'sammanhängande ledighet', 'arbetstidslag'],
            'veckovilan': ['veckovila'],
            'veckovila': ['trettiosex timmars', 'arbetstidslag'],
            'övertid': ['allmän övertid', 'övertidstimmar', '200 timmar'],
            'uppsägningstid': ['uppsägningstider', 'minsta uppsägningstid', 'anställningstid', '11 §'],
            'sakliga': ['sakliga skäl', 'saklig grund'],
            'visstidsanställning': ['särskild visstidsanställning', 'visstid', 'tidsbegränsad', '5 a §', '12 månader', 'inlasning'],
            'inlasning': ['särskild visstidsanställning', '5 a §', '12 månader', 'tillsvidareanställning'],
            'hyvling': ['7 b §', 'omreglering', 'sysselsättningsgrad', 'turordning vid omreglering'],
            'driftsenhet': ['22 §', 'turordningskrets', 'arbetsställe', 'samma ort'],
            'lön': ['anställningsförmåner', 'förmåner', 'löneförmåner', 'ersättning'],
            'förmåner': ['anställningsförmåner', 'lön'],
            'beräknas': ['beräkning', 'beräkna', 'procentregeln', 'tolv procent'],
            'diskriminering': ['aktiva åtgärder', 'likabehandling', 'bristande tillgänglighet', 'missgynnande'],
            'åtgärder': ['aktiva åtgärder', 'riktlinjer'],
            'skriftlig': ['skriftlig information', 'skriftligt besked', '6 c §', 'anställningsvillkor'],
            'anställningsvillkor': ['skriftlig information', 'villkor', 'skriftligt', '6 c §'],
            'återanställning': ['företrädesrätt', 'företrädesrätt till återanställning', '25 §', 'nio månader'],
            'förhandlingsskyldighet': ['primär förhandlingsskyldighet', 'förhandla', 'viktigare förändring', '11 §'],
            'motivera': ['sakliga skäl', 'grovt åsidosatt', 'grundas'],
            'skäl': ['sakliga skäl', 'saklig grund', 'arbetsbrist', 'personliga skäl'],
            'lojalitetsplikt': ['bisyssla', 'konkurrerande verksamhet', 'förtroendeskada', 'illojal'],
            'bisyssla': ['lojalitetsplikt', 'konkurrerande verksamhet', 'förtroende'],
            'karensavdrag': ['sjuklön', '20 procent', 'sjuklönelagen 6 §', 'karensdag', '80 procent'],
            'skyddsombudsstopp': ['6 kap. 7 §', 'arbetsmiljölagen', 'skyddsombud', 'omedelbar och allvarlig fara'],
            'studieledighet': ['studieledighetslagen', '1974:981', 'rätt till ledighet för utbildning', 'uppskjuta'],
            'kvittning': ['kvittningslagen', '1970:215', 'otillåten kvittning', 'motfordran'],
            'verksamhetsövergång': ['6 b §', 'övergång av verksamhet', '28 § mbl', 'oförändrade villkor'],
            'föräldraledighet': ['föräldraledig', '11 §', '16 § föräldraledighetslagen', 'börjar löpa'],
            'drogtestning': ['drogtest', 'alkoholtest', 'kroppslig integritet', 'intresseavvägning', 'säkerhetskänslig']
        }

        # Check explicit chapter and section number or statute in query
        chap_sec_match = re.search(r'(\d+)\s*kap\.?\s*(\d+\s*[a-z]?)\s*(?:§|paragraf)', q_lower)
        target_chap = chap_sec_match.group(1) if chap_sec_match else None
        target_chap_sec = chap_sec_match.group(2).replace(' ', '') if chap_sec_match else None

        sec_match = re.search(r'(\d+\s*[a-z]?)\s*(?:§|paragraf)', q_lower)
        target_sec = sec_match.group(1).replace(' ', '') if sec_match else None

        statute_hints = {
            'las': 'LAS', 'semesterlag': 'Semesterlagen', 'semesterlagen': 'Semesterlagen',
            'mbl': 'MBL', 'arbetstidslag': 'Arbetstidslagen', 'arbetstidslagen': 'Arbetstidslagen',
            'diskrimineringslag': 'Diskrimineringslagen', 'diskrimineringslagen': 'Diskrimineringslagen',
            'arbetsmiljölag': 'Arbetsmiljölagen', 'arbetsmiljölagen': 'Arbetsmiljölagen', 'aml': 'Arbetsmiljölagen',
            'sjuklön': 'Sjuklönelagen', 'sjuklönelagen': 'Sjuklönelagen',
            'föräldraledighet': 'Föräldraledighetslagen', 'föräldraledighetslagen': 'Föräldraledighetslagen',
            'kvittning': '1970:215', 'kvittningslagen': '1970:215',
            'studieledighet': '1974:981', 'studieledighetslagen': '1974:981'
        }
        target_statute = next((statute_hints[k] for k in statute_hints if k in q_lower), None)

        # A few foundational questions have a single governing provision but
        # share many words with adjacent exception/remedy sections. Treat the
        # user's explicit legal concept as a citation hint, while keeping the
        # ordinary hybrid ranking for broader questions.
        intent_target = None
        if 'uppsägn' in q_lower and 'avsked' in q_lower:
            intent_target = ('LAS', None, '18')
        elif 'diskrimineringsgrund' in q_lower:
            intent_target = ('Diskrimineringslagen', '1', '5')
        elif re.search(r'\brast(?:en|er)?\b', q_lower) and 'paus' not in q_lower:
            intent_target = ('Arbetstidslagen', None, '15')
        elif ('förhandla' in q_lower and ('fack' in q_lower or 'arbetstagarorganisation' in q_lower)
              and any(word in q_lower for word in ('före', 'innan', 'viktig'))):
            intent_target = ('MBL', None, '11')
        elif (any(word in q_lower for word in ('löpande', 'fortlöpande', 'informationsskyldighet'))
              and ('fack' in q_lower or 'arbetstagarorganisation' in q_lower)):
            intent_target = ('MBL', None, '19')
        elif 'allmän övertid' in q_lower and any(word in q_lower for word in ('kalenderår', 'hur många', 'max')):
            intent_target = ('Arbetstidslagen', None, '8')
        elif ('sjuklön' in q_lower and any(word in q_lower for word in ('hur stor', 'procent', 'betala'))):
            intent_target = ('Sjuklönelagen', None, '6')
        elif 'semesterdag' in q_lower and any(word in q_lower for word in ('spara', 'sparas', 'sparad')):
            intent_target = ('Semesterlagen', None, '18')
        elif 'jourtid' in q_lower:
            intent_target = ('Arbetstidslagen', None, '6')
        elif ('semesterdag' in q_lower and not any(w in q_lower for w in ('spara', 'sparad'))
              and any(phrase in q_lower for phrase in ('hur många', 'rätt till', 'per år', 'varje år'))):
            intent_target = ('Semesterlagen', None, '4')

        expanded_query_terms = list(meaningful_q)
        for w in meaningful_q:
            if w in SYNONYMS:
                expanded_query_terms.extend(SYNONYMS[w])

        q_emb = Embedder.get_embedding(query + " " + " ".join(expanded_query_terms))

        requested_country = (filters or {}).get('jurisdiction') or (filters or {}).get('country')
        items, doc_stem_freqs, prepared = self._search_index(
            self._get_statute_items(requested_country), filters or {})
        if not items:
            return []
        N = len(items)

        scored_sections = []
        for s in items:
            if filters:
                requested_jurisdiction = filters.get("jurisdiction") or filters.get("country")
                requested_language = filters.get("language")
                if requested_jurisdiction and str(s.get("jurisdiction", "SE")).upper() != str(requested_jurisdiction).upper():
                    continue
                if requested_language and str(s.get("language", "sv")).lower() != str(requested_language).lower():
                    continue
            content = s.get("content", "")
            title = s.get("section_title") or ""
            keywords = s.get("keywords", [])
            sec_num = str(s.get("section_number", "")).lower().replace(" ", "")
            sec_chap = str(s.get("chapter", "")).lower().replace(" ", "") if s.get("chapter") else None
            statute_short = s.get("statute_short", "")

            doc_tokens, doc_stems, title_tokens, title_stems, kw_tokens, first_tokens, first_stems = prepared[id(s)]

            lex_score = 0.0
            title_matches_count = 0
            for w in meaningful_q:
                w_stem = self._stem_sv(w)
                df = doc_stem_freqs.get(w_stem, 1)
                idf = max(0.5, math.log(1.0 + (N - df + 0.5) / (df + 0.5)))

                c_count = doc_tokens[w] + 0.6 * doc_stems[w_stem]
                t_m = (title_tokens[w] + 1.2 * title_stems[w_stem])
                if t_m > 0:
                    title_matches_count += 1
                t_count = t_m * 10.0
                k_count = (kw_tokens[w] + 1.0 * kw_tokens[w]) * 5.0
                f_count = (first_tokens[w] + 1.0 * first_stems[w_stem]) * 5.0

                match_val = c_count + t_count + k_count + f_count
                if match_val > 0:
                    lex_score += math.log(1.0 + match_val) * idf

            if title_matches_count >= 2:
                lex_score += 20.0
            elif title_matches_count >= 1 and sum(title_tokens.values()) <= 2:
                lex_score += 15.0

            for i in range(len(meaningful_q) - 1):
                phrase = f'{meaningful_q[i]} {meaningful_q[i+1]}'
                if phrase in title.lower():
                    lex_score += 25.0
                elif phrase in ' '.join(keywords).lower():
                    lex_score += 12.0
                elif phrase in content.lower():
                    lex_score += 6.0

            sem_score = 0.0
            if s.get("embedding"):
                sem_score = Embedder.cosine_similarity(q_emb, s["embedding"])

            # Exception & citation de-weighting
            if '69 år' in content.lower() and '69' not in q_lower:
                lex_score *= 0.1
                sem_score *= 0.1
            if ('skadestånd enligt' in content.lower() or 'ogiltigförklarats och ersättning' in content.lower() or 'har ogiltigförklarats' in content.lower()):
                if 'skadestånd' not in q_lower and 'ogiltig' not in q_lower and 'domstol' not in q_lower:
                    lex_score *= 0.3
                    sem_score *= 0.3
            if any(content.lower().strip().startswith(p) for p in ['om flera arbetstagare har företrädesrätt enligt', 'har besked om företrädesrätt till återanställning lämnats enligt', 'ett yrkande om beslut enligt']):
                lex_score *= 0.3
                sem_score *= 0.3

            boost = 0.0
            if target_chap and target_chap_sec and target_chap == sec_chap and target_chap_sec == sec_num:
                boost += 45.0
            elif target_sec and target_sec == sec_num:
                boost += 30.0

            if target_statute and (target_statute.lower() in statute_short.lower() or target_statute in s.get("statute_id", "")):
                boost += 10.0

            if intent_target:
                intent_statute, intent_chapter, intent_section = intent_target
                chapter_matches = ((intent_chapter is None and sec_chap is None)
                                   or str(intent_chapter) == sec_chap)
                if (intent_statute.lower() == statute_short.lower()
                        and chapter_matches and intent_section == sec_num):
                    boost += 35.0

            total_score = (0.4 * lex_score) + (0.6 * (sem_score * 30.0)) + boost

            if total_score > 0.05 or lex_score > 0:
                scored_sections.append({
                    "score": round(total_score, 3),
                    "statute": s.get("statute_short"),
                    "sfs_number": s.get("statute_id"),
                    "chapter": s.get("chapter"),
                    "section": s.get("section_number"),
                    "title": s.get("section_title"),
                    "content": s.get("content"),
                    "keywords": s.get("keywords"),
                    "jurisdiction": s.get("jurisdiction", "SE"),
                    "language": s.get("language", "sv"),
                    "source": s.get("source"),
                    "source_url": s.get("source_url"),
                    "license": s.get("license"),
                    "attribution": s.get("attribution"),
                })

        scored_sections.sort(key=lambda x: x["score"], reverse=True)
        return scored_sections[:limit]


    # --- Precedents ---
    def save_precedent(self, precedent: Dict[str, Any]):
        doc_id = precedent.get("id")
        self._local_precedents[doc_id] = precedent
        if not self.db:
            # Ingen databas: raden finns bara i minnet och forsvinner med
            # processen. Returnera det, sa anroparen inte rapporterar succe.
            return False
        try:
            self.db.collection("precedents").document(doc_id).set(precedent)
            return True
        except Exception as e:
            # Tidigare "pass". En svald skrivning gjorde att ingestionen
            # rapporterade rader den aldrig sparat.
            logger.warning("Kunde inte spara %s/%s: %s", "precedents", doc_id, e)
            return False

    def search_precedents(self, query: str, statute_ref: Optional[str] = None, year_from: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        q_emb = Embedder.get_embedding(query)
        q_lower = query.lower()
        items = self._get_precedent_items()

        results = []
        for p in items:
            # Flexible year filter
            if year_from and p.get("year") and int(p["year"]) < int(year_from):
                continue

            # Flexible statute reference matching
            if statute_ref:
                ref_clean = re.sub(r'[^a-zA-Z0-9]', '', statute_ref.lower())
                prov_text = "".join(p.get("legal_provisions_referenced", [])).lower()
                prov_clean = re.sub(r'[^a-zA-Z0-9]', '', prov_text)

                # Check if digits match (e.g. '7' in '7')
                digits_ref = re.findall(r'\d+', statute_ref)
                if digits_ref and not any(d in prov_clean for d in digits_ref):
                    continue

            # Calculate semantic & keyword relevance
            sem_score = Embedder.cosine_similarity(q_emb, p.get("embedding", []))
            title_text = p.get("title", "").lower()
            summary_text = p.get("summary", "").lower()
            case_num = p.get("case_number", "").lower()
            domskal_text = p.get("domskal", "").lower()
            keywords_text = " ".join(p.get("legal_keywords", [])).lower()
            prov_text = " ".join(p.get("legal_provisions_referenced", [])).lower()
            full_text = f"{case_num} {title_text} {summary_text} {domskal_text} {keywords_text} {prov_text}"

            # Extract search tokens
            tokens = [w for w in re.findall(r'[\w/]+', q_lower) if len(w) > 2]
            lex_score = 0.0
            for t in tokens:
                if t in case_num:
                    lex_score += 8.0
                elif t in title_text:
                    lex_score += 5.0
                elif t in keywords_text:
                    lex_score += 4.0
                elif t in summary_text:
                    lex_score += 2.5
                elif t in domskal_text:
                    lex_score += 1.5

            # Statute reference match boost
            q_secs = re.findall(r'(\d+\s*[a-z]?)\s*(?:§|paragraf)', q_lower)
            for qs in q_secs:
                clean_qs = qs.replace(' ', '')
                if clean_qs in prov_text:
                    lex_score += 6.0

            total_score = (0.3 * sem_score) + (0.7 * lex_score)

            results.append({
                "score": round(total_score, 3),
                "case_number": p.get("case_number"),
                "year": p.get("year"),
                "title": p.get("title"),
                "summary": p.get("summary"),
                "parties": p.get("parties"),
                "provisions": p.get("legal_provisions_referenced"),
                "domskal": p.get("domskal"),
                "slut": p.get("slut")
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    # --- CBA Rules ---
    def save_cba_rule(self, rule: Dict[str, Any]):
        doc_id = rule.get("id")
        self._local_rules[doc_id] = rule
        if not self.db:
            # Ingen databas: raden finns bara i minnet och forsvinner med
            # processen. Returnera det, sa anroparen inte rapporterar succe.
            return False
        try:
            self.db.collection("agreement_rules").document(doc_id).set(rule)
            return True
        except Exception as e:
            # Tidigare "pass". En svald skrivning gjorde att ingestionen
            # rapporterade rader den aldrig sparat.
            logger.warning("Kunde inte spara %s/%s: %s", "agreement_rules", doc_id, e)
            return False

    def get_cba_exception(self, statute: str, section: str, agreement_name: str) -> Optional[Dict[str, Any]]:
        statute_clean = statute.strip().upper()
        sec_clean = section.strip().lower().replace("§", "").strip()
        ag_clean = agreement_name.strip().lower()

        items = []
        if self.db:
            try:
                docs = self.db.collection("agreement_rules").stream()
                items = [d.to_dict() for d in docs]
            except Exception:
                pass
        if not items:
            items = list(self._local_rules.values())

        for r in items:
            if (ag_clean in r.get("agreement_name", "").lower() and
                statute_clean in r.get("statute", "").upper() and
                sec_clean == r.get("section", "").lower()):
                return r
        return None

    def compare_statute_vs_cba(self, topic: str, agreement_name: str) -> Dict[str, Any]:
        matched_rules = []
        ag_clean = agreement_name.strip().lower()
        top_clean = topic.strip().lower()

        items = []
        if self.db:
            try:
                docs = self.db.collection("agreement_rules").stream()
                items = [d.to_dict() for d in docs]
            except Exception:
                pass
        if not items:
            items = list(self._local_rules.values())

        for r in items:
            if ag_clean in r.get("agreement_name", "").lower():
                if top_clean in r.get("topic", "").lower() or top_clean in r.get("rule_content", "").lower():
                    matched_rules.append(r)

        statute_baseline = None
        if matched_rules:
            first = matched_rules[0]
            statute_baseline = self.get_statute_section(first.get("statute", "LAS"), first.get("section", "11"))

        return {
            "topic": topic,
            "agreement_name": agreement_name,
            "cba_rules": matched_rules,
            "statute_baseline": statute_baseline,
            "summary": f"Jämförelse mellan lag och {agreement_name} för ämnet '{topic}'."
        }

db_client = FirebaseLaborLawDB()
