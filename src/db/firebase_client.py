import os
import re
from typing import List, Dict, Any, Optional
from src.config import settings
from src.embeddings.embedder import Embedder

class FirebaseLaborLawDB:
    def __init__(self):
        self.db = None
        self._local_statutes: Dict[str, Any] = {}
        self._local_sections: Dict[str, Any] = {}
        self._local_precedents: Dict[str, Any] = {}
        self._local_rules: Dict[str, Any] = {}
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

    def get_statute_section(self, law: str, section: str, chapter: Optional[str] = None) -> Optional[Dict[str, Any]]:
        law_clean = law.strip().upper()
        sec_clean = section.strip().lower().replace("§", "").strip()
        
        items = []
        if self.db:
            try:
                docs = self.db.collection("statute_sections").stream()
                items = [d.to_dict() for d in docs]
            except Exception:
                pass
        if not items:
            items = list(self._local_sections.values())

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

    def search_statute_sections(self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 5) -> List[Dict[str, Any]]:
        q_lower = query.lower()
        q_emb = Embedder.get_embedding(query)
        
        items = []
        if self.db:
            try:
                docs = self.db.collection("statute_sections").limit(500).stream()
                items = [d.to_dict() for d in docs]
            except Exception:
                pass
        if not items:
            items = list(self._local_sections.values())

        scored_sections = []
        for s in items:
            lex_score = 0.0
            content = s.get("content", "").lower()
            title = (s.get("section_title") or "").lower()
            keywords = [k.lower() for k in s.get("keywords", [])]
            
            for word in q_lower.split():
                if len(word) < 2:
                    continue
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

    def search_precedents(self, query: str, statute_ref: Optional[str] = None, year_from: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        q_emb = Embedder.get_embedding(query)
        q_lower = query.lower()
        items = []
        if self.db:
            try:
                docs = self.db.collection("precedents").stream()
                items = [d.to_dict() for d in docs]
            except Exception:
                pass
        if not items:
            items = list(self._local_precedents.values())

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
            full_text = (p.get("title", "") + " " + p.get("summary", "") + " " + p.get("domskal", "")).lower()
            
            words = [w for w in q_lower.split() if len(w) > 2]
            matched_words = [w for w in words if w in full_text]
            lex_score = len(matched_words) * 2.0
            
            total_score = (0.5 * sem_score) + (0.5 * lex_score)
            
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
