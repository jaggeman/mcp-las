import os
from typing import List, Dict, Any, Optional
from google.cloud.firestore_v1.base_query import FieldFilter
from src.config import settings
from src.embeddings.embedder import Embedder

class FirebaseLaborLawDB:
    """
    Firebase Firestore client for Swedish Labor Law.
    Includes in-memory cache/fallback for instant local testing when Firebase credentials are not yet set.
    """
    
    def __init__(self):
        self.db = None
        self._local_statutes: Dict[str, Any] = {}
        self._local_sections: Dict[str, Any] = {}
        self._local_precedents: Dict[str, Any] = {}
        self._local_agreements: Dict[str, Any] = {}
        self._local_rules: Dict[str, Any] = {}
        self._init_firebase()
        self._seed_default_cba_and_ad_data()

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
            print(f"Firestore not initialized ({e}). Using robust local memory store.")
            self.db = None

    def _seed_default_cba_and_ad_data(self):
        # Sample AD Precedents (Arbetsdomstolen)
        ad_cases = [
            {
                "id": "AD_2023_nr_45",
                "case_number": "AD 2023 nr 45",
                "year": 2023,
                "title": "Fråga om sakliga skäl för uppsägning vid bristande prestation och personliga skäl",
                "summary": "Arbetsdomstolen fann att arbetsgivaren uppfyllt sin omplaceringsskyldighet och att det förelåg sakliga skäl för uppsägning enligt 7 § LAS.",
                "legal_provisions_referenced": ["LAS 7 §", "LAS 7 a §"],
                "parties": "Unionen mot Almega Tjänsteföretagen",
                "domskal": "Enligt de ändringar i LAS som trädde i kraft 2022 krävs sakliga skäl...",
                "slut": "Käromålet avslås. Uppsägningen var giltig."
            },
            {
                "id": "AD_2022_nr_12",
                "case_number": "AD 2022 nr 12",
                "year": 2022,
                "title": "Fråga om avskedande eller uppsägning vid grov misskötsamhet",
                "summary": "Arbetstagaren hade agerat illojalt. AD fann att grund för avskedande enligt 18 § LAS inte förelåg men väl saklig grund för uppsägning.",
                "legal_provisions_referenced": ["LAS 7 §", "LAS 18 §"],
                "parties": "IF Metall mot Teknikföretagen",
                "domskal": "För avskedande krävs ett grovt åsidosättande av åligganden mot arbetsgivaren...",
                "slut": "Avskedandet ogiltigförklaras, men anställningen anses uppsagd."
            }
        ]
        for ad in ad_cases:
            ad["embedding"] = Embedder.get_embedding(ad["title"] + " " + ad["summary"])
            self.save_precedent(ad)

        # Sample CBA Rules (Teknikavtalet & Almega)
        cba_rules = [
            {
                "id": "teknikavtalet_uppsagningstid",
                "agreement_name": "Teknikavtalet",
                "statute": "LAS",
                "section": "11",
                "topic": "Uppsägningstid",
                "rule_content": "För tjänstemän med mer än 10 års sammanhängande anställning och som fyllt 55 år gäller 12 månaders uppsägningstid från arbetsgivarens sida vid arbetsbrist.",
                "statutory_deviation_ref": "Avviker förmånligare från LAS 11 § (max 6 månader)."
            },
            {
                "id": "teknikavtalet_turordning",
                "agreement_name": "Teknikavtalet",
                "statute": "LAS",
                "section": "22",
                "topic": "Turordning vid arbetsbrist (Avtalsturlista)",
                "rule_content": "Parterna kan genom lokal överenskommelse fastställa en avtalsturlista (undantag från strikt sist-in-först-ut) för att trygga företagets kompetens.",
                "statutory_deviation_ref": "Tillåtet enligt semidispositiva regeln i LAS 2 §."
            }
        ]
        for rule in cba_rules:
            rule["embedding"] = Embedder.get_embedding(rule["topic"] + " " + rule["rule_content"])
            self.save_cba_rule(rule)

    # --- Statutes & Sections ---
    def save_statute(self, metadata: Dict[str, Any]):
        doc_id = str(metadata.get("id", "")).replace(":", "_")
        self._local_statutes[doc_id] = metadata
        if self.db:
            try:
                self.db.collection("statutes").document(doc_id).set(metadata)
            except Exception as e:
                print(f"Firestore save_statute error: {e}")

    def save_statute_section(self, section: Dict[str, Any]):
        doc_id = section.get("id")
        if not section.get("embedding"):
            section["embedding"] = Embedder.get_embedding(section.get("raw_text", ""))
        self._local_sections[doc_id] = section
        if self.db:
            try:
                self.db.collection("statute_sections").document(doc_id).set(section)
            except Exception as e:
                print(f"Firestore save_statute_section error: {e}")

    def get_statute_section(self, law: str, section: str, chapter: Optional[str] = None) -> Optional[Dict[str, Any]]:
        law_clean = law.strip().upper()
        sec_clean = section.strip().lower().replace("§", "").strip()
        
        # 1. Search local / cached
        for s in self._local_sections.values():
            short = s.get("statute_short", "").upper()
            sfs = s.get("statute_id", "")
            if (law_clean in short or law_clean in sfs) and s.get("section_number", "").lower() == sec_clean:
                if chapter:
                    if str(s.get("chapter")) == str(chapter):
                        return s
                else:
                    return s

        # 2. Firestore query
        if self.db:
            try:
                query = self.db.collection("statute_sections").where(filter=FieldFilter("section_number", "==", sec_clean))
                docs = query.stream()
                for doc in docs:
                    data = doc.to_dict()
                    if law_clean in data.get("statute_short", "").upper() or law_clean in data.get("statute_id", ""):
                        return data
            except Exception as e:
                print(f"Firestore query error: {e}")

        return None

    def search_statute_sections(self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 5) -> List[Dict[str, Any]]:
        q_lower = query.lower()
        q_emb = Embedder.get_embedding(query)
        
        # Pull from local cache or Firestore
        items = list(self._local_sections.values())
        if not items and self.db:
            try:
                docs = self.db.collection("statute_sections").limit(500).stream()
                items = [d.to_dict() for d in docs]
            except Exception:
                pass

        scored_sections = []
        for s in items:
            lex_score = 0.0
            content = s.get("content", "").lower()
            title = (s.get("section_title") or "").lower()
            keywords = [k.lower() for k in s.get("keywords", [])]
            
            for word in q_lower.split():
                if word in content:
                    lex_score += 1.0
                if word in title:
                    lex_score += 2.0
                if any(word in kw for kw in keywords):
                    lex_score += 2.5
                    
            sem_score = 0.0
            if s.get("embedding"):
                sem_score = Embedder.cosine_similarity(q_emb, s["embedding"])
                
            total_score = (0.4 * lex_score) + (0.6 * sem_score)
            
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

    def search_precedents(self, query: str, statute_ref: Optional[str] = None, year_from: Optional[int] = None, limit: int = 5) -> List[Dict[str, Any]]:
        q_emb = Embedder.get_embedding(query)
        items = list(self._local_precedents.values())
        if not items and self.db:
            try:
                docs = self.db.collection("precedents").stream()
                items = [d.to_dict() for d in docs]
            except Exception:
                pass

        results = []
        for p in items:
            if year_from and p.get("year") and p["year"] < year_from:
                continue
            if statute_ref and not any(statute_ref.lower() in ref.lower() for ref in p.get("legal_provisions_referenced", [])):
                continue
                
            score = Embedder.cosine_similarity(q_emb, p.get("embedding", []))
            results.append({
                "score": round(score, 3),
                "case_number": p.get("case_number"),
                "year": p.get("year"),
                "title": p.get("title"),
                "summary": p.get("summary"),
                "parties": p.get("parties"),
                "provisions": p.get("legal_provisions_referenced"),
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
        
        items = list(self._local_rules.values())
        if not items and self.db:
            try:
                docs = self.db.collection("agreement_rules").stream()
                items = [d.to_dict() for d in docs]
            except Exception:
                pass

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
        
        items = list(self._local_rules.values())
        if not items and self.db:
            try:
                docs = self.db.collection("agreement_rules").stream()
                items = [d.to_dict() for d in docs]
            except Exception:
                pass

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
