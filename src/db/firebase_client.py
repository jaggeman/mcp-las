import math
import os
import re
from typing import List, Dict, Any, Optional
from src.config import settings
from src.embeddings.embedder import Embedder
from src.db.ad_cases_data import AD_PRECEDENTS_DATA

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
        self._local_rules: Dict[str, Any] = {}
        self._cached_statute_sections: Optional[List[Dict[str, Any]]] = None
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
        if self.db:
            try:
                self.db.collection("statutes").document(doc_id).set(metadata)
            except Exception:
                pass

    def save_statute_section(self, section: Dict[str, Any]):
        doc_id = section.get("id")
        if not section.get("embedding"):
            section["embedding"] = Embedder.get_embedding(section.get("raw_text", ""))
        self._local_sections[doc_id] = section
        if self.db:
            try:
                self.db.collection("statute_sections").document(doc_id).set(section)
            except Exception:
                pass

    def _get_statute_items(self) -> List[Dict[str, Any]]:
        if self._cached_statute_sections is not None:
            return self._cached_statute_sections
        items = []
        if self.db:
            try:
                docs = self.db.collection("statute_sections").limit(1000).stream()
                items = [d.to_dict() for d in docs]
            except Exception:
                pass
        if not items:
            items = list(self._local_sections.values())
        if items:
            self._cached_statute_sections = items
        return items

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

    def get_statute_section(self, law: str, section: str, chapter: Optional[str] = None) -> Optional[Dict[str, Any]]:
        law_clean = law.strip().upper()
        sec_clean = section.strip().lower().replace("§", "").strip()
        
        items = self._get_statute_items()

        for s in items:
            short = s.get("statute_short", "").upper()
            sfs = s.get("statute_id", "")
            if (law_clean in short or law_clean in sfs) and s.get("section_number", "").lower() == sec_clean:
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

    def search_statute_sections(self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 5) -> List[Dict[str, Any]]:
        q_lower = query.lower()
        raw_tokens = re.findall(r'[a-zåäö0-9]+', q_lower)
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
            'uppsägningstid': ['uppsägningstider', 'minsta uppsägningstid'],
            'sakliga': ['sakliga skäl', 'saklig grund'],
            'visstidsanställning': ['särskild visstidsanställning', 'visstid', 'tidsbegränsad'],
            'lön': ['anställningsförmåner', 'förmåner', 'löneförmåner'],
            'förmåner': ['anställningsförmåner', 'lön'],
            'beräknas': ['beräkning', 'beräkna', 'procentregeln', 'tolv procent'],
            'diskriminering': ['aktiva åtgärder', 'likabehandling'],
            'åtgärder': ['aktiva åtgärder', 'riktlinjer'],
            'skriftlig': ['skriftlig information', 'skriftligt besked'],
            'anställningsvillkor': ['skriftlig information', 'villkor', 'skriftligt'],
            'återanställning': ['företrädesrätt', 'företrädesrätt till återanställning'],
            'förhandlingsskyldighet': ['primär förhandlingsskyldighet', 'förhandla', 'viktigare förändring'],
            'motivera': ['sakliga skäl', 'grovt åsidosatt', 'grundas'],
            'skäl': ['sakliga skäl', 'saklig grund', 'arbetsbrist', 'personliga skäl']
        }

        # Check explicit section number or statute in query
        sec_match = re.search(r'(\d+\s*[a-z]?)\s*(?:§|paragraf)', q_lower)
        target_sec = sec_match.group(1).replace(' ', '') if sec_match else None

        statute_hints = {
            'las': 'LAS', 'semesterlag': 'Semesterlagen', 'semesterlagen': 'Semesterlagen',
            'mbl': 'MBL', 'arbetstidslag': 'Arbetstidslagen', 'arbetstidslagen': 'Arbetstidslagen',
            'diskrimineringslag': 'Diskrimineringslagen', 'diskrimineringslagen': 'Diskrimineringslagen',
            'arbetsmiljölag': 'Arbetsmiljölagen', 'arbetsmiljölagen': 'Arbetsmiljölagen',
            'sjuklön': 'Sjuklönelagen', 'sjuklönelagen': 'Sjuklönelagen',
            'föräldraledighet': 'Föräldraledighetslagen', 'föräldraledighetslagen': 'Föräldraledighetslagen'
        }
        target_statute = next((statute_hints[k] for k in statute_hints if k in q_lower), None)

        expanded_query_terms = list(meaningful_q)
        for w in meaningful_q:
            if w in SYNONYMS:
                expanded_query_terms.extend(SYNONYMS[w])

        q_emb = Embedder.get_embedding(query + " " + " ".join(expanded_query_terms))

        items = self._get_statute_items()

        if not items:
            return []

        # Corpus stem frequencies for IDF
        N = len(items)
        doc_stem_freqs: Dict[str, int] = {}
        for s in items:
            all_text = (s.get('content', '') + ' ' + (s.get('section_title') or '') + ' ' + ' '.join(s.get('keywords', []))).lower()
            stems = set(self._stem_sv(w) for w in re.findall(r'[a-zåäö0-9]+', all_text))
            for st in stems:
                doc_stem_freqs[st] = doc_stem_freqs.get(st, 0) + 1

        scored_sections = []
        for s in items:
            content = s.get("content", "")
            title = s.get("section_title") or ""
            keywords = s.get("keywords", [])
            sec_num = str(s.get("section_number", "")).lower().replace(" ", "")
            statute_short = s.get("statute_short", "")

            doc_tokens = re.findall(r'[a-zåäö0-9]+', content.lower())
            doc_stems = [self._stem_sv(w) for w in doc_tokens]
            title_tokens = re.findall(r'[a-zåäö0-9]+', title.lower())
            title_stems = [self._stem_sv(w) for w in title_tokens]
            kw_tokens = re.findall(r'[a-zåäö0-9]+', ' '.join(keywords).lower())
            first_tokens = doc_tokens[:25]
            first_stems = doc_stems[:25]

            lex_score = 0.0
            title_matches_count = 0
            for w in meaningful_q:
                w_stem = self._stem_sv(w)
                df = doc_stem_freqs.get(w_stem, 1)
                idf = max(0.5, math.log(1.0 + (N - df + 0.5) / (df + 0.5)))

                c_count = doc_tokens.count(w) + 0.6 * doc_stems.count(w_stem)
                t_m = (title_tokens.count(w) + 1.2 * title_stems.count(w_stem))
                if t_m > 0:
                    title_matches_count += 1
                t_count = t_m * 10.0
                k_count = (kw_tokens.count(w) + 1.0 * kw_tokens.count(w)) * 5.0
                f_count = (first_tokens.count(w) + 1.0 * first_stems.count(w_stem)) * 5.0

                match_val = c_count + t_count + k_count + f_count
                if match_val > 0:
                    lex_score += math.log(1.0 + match_val) * idf

            if title_matches_count >= 2:
                lex_score += 20.0
            elif title_matches_count >= 1 and len(title_tokens) <= 2:
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
            if target_sec and target_sec == sec_num:
                boost += 30.0
            if target_statute and target_statute.lower() in statute_short.lower():
                boost += 6.0

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
                    "keywords": s.get("keywords")
                })

        scored_sections.sort(key=lambda x: x["score"], reverse=True)
        return scored_sections[:limit]


    # --- Precedents ---
    def save_precedent(self, precedent: Dict[str, Any]):
        doc_id = precedent.get("id")
        self._local_precedents[doc_id] = precedent
        if self.db:
            try:
                self.db.collection("precedents").document(doc_id).set(precedent)
            except Exception:
                pass

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
            full_text = f"{case_num} {title_text} {summary_text} {domskal_text}"
            
            # Extract search tokens
            tokens = [w for w in re.findall(r'[\w/]+', q_lower) if len(w) > 2]
            lex_score = 0.0
            for t in tokens:
                if t in title_text or t in case_num:
                    lex_score += 4.0
                elif t in summary_text:
                    lex_score += 2.5
                elif t in domskal_text:
                    lex_score += 1.5
            
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
        if self.db:
            try:
                self.db.collection("agreement_rules").document(doc_id).set(rule)
            except Exception:
                pass

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
