import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.db.firebase_client import FirebaseLaborLawDB
from src.scrapers.riksdagen_fetcher import RiksdagenFetcher

BENCHMARK_QUESTIONS = [
    ('hur länge kan man ha provanställning?', 'LAS', '6'),
    ('när övergår särskild visstidsanställning till tillsvidareanställning?', 'LAS', '5 a'),
    ('hur lång är dygnsvilan enligt lag?', 'Arbetstidslagen', '13'),
    ('vad gäller för veckovila?', 'Arbetstidslagen', '14'),
    ('hur många semesterdagar har man rätt till?', 'Semesterlagen', '4'),
    ('vad gäller vid turordning vid arbetsbrist och undantag?', 'LAS', '22'),
    ('vad krävs för sakliga skäl vid uppsägning?', 'LAS', '7'),
    ('när får man avskeda en anställd?', 'LAS', '18'),
    ('hur lång är lagstadgad uppsägningstid?', 'LAS', '11'),
    ('vad gäller om företrädesrätt till återanställning?', 'LAS', '25'),
    ('hur ska arbetsgivaren underrätta och varsla vid uppsägning?', 'LAS', '30'),
    ('hur mycket övertid får man arbeta per år?', 'Arbetstidslagen', '8'),
    ('vad är reglerna för sparad semester?', 'Semesterlagen', '18'),
    ('vilka skäl kan motivera avskedande jämfört med uppsägning?', 'LAS', '18'),
    ('vad har man för lön och förmåner under uppsägningstiden?', 'LAS', '12'),
    ('hur fungerar förhandlingsskyldighet enligt MBL?', 'MBL', '11'),
    ('vad innebär primär förhandlingsskyldighet innan viktiga beslut?', 'MBL', '11'),
    ('vad gäller vid övergång av verksamhet?', 'LAS', '6 b'),
    ('när måste arbetsgivaren lämna skriftlig information om anställningsvillkor?', 'LAS', '6 c'),
    ('hur beräknas semesterlön och semesterersättning?', 'Semesterlagen', '16'),
    ('vad gäller vid preskription av krav enligt LAS?', 'LAS', '40'),
    ('vilka aktiva åtgärder mot diskriminering ska en arbetsgivare genomföra?', 'Diskrimineringslagen', '1')
]

def run_benchmark():
    print('Initializing FirebaseLaborLawDB and loading statutes...')
    db = FirebaseLaborLawDB()
    
    if not db._local_sections:
        laws = ['1982:80', '1977:480', '1976:580', '1982:673', '2008:567', '1977:1160', '1991:1047', '1995:584']
        for sfs in laws:
            try:
                meta, secs = RiksdagenFetcher.get_statute(sfs)
                for s in secs:
                    db.save_statute_section(s.model_dump())
            except Exception as e:
                print(f'Error fetching {sfs}: {e}')
                
    print(f'Indexed {len(db._local_sections)} sections in local DB.')
    print('\n' + '=' * 80)
    print(f'SEARCH BENCHMARK EVALUATION ({len(BENCHMARK_QUESTIONS)} Questions)')
    print('=' * 80)
    
    top1_hits = 0
    top3_hits = 0
    
    for i, (q, exp_law, exp_sec) in enumerate(BENCHMARK_QUESTIONS, 1):
        results = db.search_statute_sections(q, limit=3)
        in_top1 = False
        in_top3 = False
        for rank, res in enumerate(results):
            if exp_law.lower() in res['statute'].lower() and res['section'].lower().replace(' ', '') == exp_sec.lower().replace(' ', ''):
                if rank == 0:
                    in_top1 = True
                in_top3 = True
                break
        if in_top1:
            top1_hits += 1
        if in_top3:
            top3_hits += 1
            
        hit_label = 'TOP 1' if in_top1 else ('TOP 3' if in_top3 else 'MISS ')
        res_summary = ', '.join([r['statute'] + ' ' + r['section'] + ' §' for r in results])
        print(f'{i:>2}. [{hit_label}] Q: {q[:42]:<42} -> Expected: {exp_law} {exp_sec} § | Found: {res_summary}')
        
    print('=' * 80)
    print(f'Top-1 Accuracy: {top1_hits}/{len(BENCHMARK_QUESTIONS)} ({top1_hits/len(BENCHMARK_QUESTIONS)*100:.1f}%)')
    print(f'Top-3 Accuracy: {top3_hits}/{len(BENCHMARK_QUESTIONS)} ({top3_hits/len(BENCHMARK_QUESTIONS)*100:.1f}%)')
    print('=' * 80)

if __name__ == '__main__':
    run_benchmark()
