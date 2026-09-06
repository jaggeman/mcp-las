import os
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.scrapers.riksdagen_fetcher import RiksdagenFetcher
from src.db.firebase_client import db_client
from src.embeddings.embedder import Embedder

DEFAULT_LAWS = [
    "1982:80",   # LAS
    "1977:480",  # Semesterlagen
    "1976:580",  # MBL
    "1982:673",  # Arbetstidslagen
    "2008:567",  # Diskrimineringslagen
]

def run_ingestion(laws=None):
    if laws is None:
        laws = DEFAULT_LAWS
        
    print(f"Starting ingestion for {len(laws)} statutes from Riksdagens API...")
    
    total_sections_count = 0
    statutes_summary = []
    
    for sfs in laws:
        try:
            print(f"\n--> Fetching SFS {sfs}...")
            metadata, sections = RiksdagenFetcher.get_statute(sfs)
            print(f"    Fetched {metadata.title}: parsed {len(sections)} sections.")
            
            # Save metadata
            db_client.save_statute(metadata.model_dump())
            
            # Save sections
            for sec in sections:
                sec_dict = sec.model_dump()
                sec_dict["embedding"] = Embedder.get_embedding(sec.raw_text)
                db_client.save_statute_section(sec_dict)
                total_sections_count += 1
                
            statutes_summary.append({
                "sfs": sfs,
                "short": metadata.short_name,
                "sections": len(sections)
            })
        except Exception as e:
            print(f"    Error processing SFS {sfs}: {e}")
            
    print(f"\n==========================================")
    print(f"Ingestion completed! Total sections indexed: {total_sections_count}")
    for s in statutes_summary:
        print(f" - {s['short']} ({s['sfs']}): {s['sections']} paragrafer")
    print(f"==========================================")

if __name__ == "__main__":
    target = sys.argv[1:] if len(sys.argv) > 1 else None
    run_ingestion(target)
