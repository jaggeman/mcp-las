import os, re
from typing import List, Optional
from pydantic import BaseModel

class CBARule(BaseModel):
    id: str
    agreement_name: str
    sector: Optional[str] = None
    statute: str
    section: str
    topic: str
    rule_content: str
    statutory_deviation_ref: str
    page_number: Optional[int] = None
    embedding: Optional[List[float]] = None

class CBAParser:
    TOPIC_PATTERNS = [
        {"topic": "Uppsägningstid", "statute": "LAS", "section": "11", "keywords": ["uppsägningstid", "varseltid"]},
        {"topic": "Turordning (Avtalsturlista)", "statute": "LAS", "section": "22", "keywords": ["turordning", "avtalsturlista", "arbetsbrist"]},
        {"topic": "Anställningsformer", "statute": "LAS", "section": "5", "keywords": ["särskild visstid", "visstidsanställning", "provanställning"]},
        {"topic": "Semestervillkor", "statute": "Semesterlagen", "section": "16", "keywords": ["semesterlön", "semesterlönetillägg"]},
        {"topic": "Arbetstid & Övertid", "statute": "Arbetstidslagen", "section": "7", "keywords": ["övertid", "mertid", "dygnsvila", "schema"]}
    ]
