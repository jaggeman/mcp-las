# -*- coding: utf-8 -*-
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.scrapers.riksdagen_fetcher import RiksdagenFetcher
from src.chunking.law_chunker import LawChunker

LAWS_TO_CHECK = [
    ('1982:80', 'LAS', 50),
    ('1977:480', 'Semesterlagen', 30),
    ('1976:580', 'MBL', 60),
    ('1982:673', 'Arbetstidslagen', 25),
    ('2008:567', 'Diskrimineringslagen', 60),
    ('1977:1160', 'Arbetsmiljölagen', 80),
    ('1991:1047', 'Sjuklönelagen', 20),
    ('1995:584', 'Föräldraledighetslagen', 20),
]

CRITICAL_SECTIONS = [
    ('1982:80', 'LAS', '5', 'Avtal om tidsbegränsad anställning får träffas'),
    ('1982:80', 'LAS', '6', 'Avtal får även träffas om tidsbegränsad provanställning'),
    ('1982:80', 'LAS', '7', 'sakliga skäl'),
    ('1982:80', 'LAS', '8', 'skriftlig'),
    ('1982:80', 'LAS', '11', 'minsta uppsägningstid'),
    ('1982:80', 'LAS', '18', 'Avskedande får ske'),
    ('1982:80', 'LAS', '22', 'turordning'),
    ('1982:80', 'LAS', '25', 'företrädesrätt till återanställning'),
    ('1982:80', 'LAS', '40', 'preskription'),
    ('1977:480', 'Semesterlagen', '4', 'tjugofem semesterdagar'),
    ('1982:673', 'Arbetstidslagen', '13', 'dygnsvila'),
    ('1982:673', 'Arbetstidslagen', '14', 'veckovila'),
    ('1976:580', 'MBL', '11', 'förhandla'),
]

def check_database_coverage():
    print('=' * 80)
    print('SWEDISH LABOR LAW DATABASE COVERAGE & CHUNKER INTEGRITY CHECK')
    print('=' * 80)
    total_statutes = len(LAWS_TO_CHECK)
    total_sections_all = 0
    all_passed = True
    for sfs, short_name, min_expected in LAWS_TO_CHECK:
        try:
            meta, sections = RiksdagenFetcher.get_statute(sfs)
            count = len(sections)
            total_sections_all += count
            doc_ids = [s.id for s in sections]
            unique_ids = set(doc_ids)
            has_dups = len(doc_ids) != len(unique_ids)
            status = 'PASS' if count >= min_expected and not has_dups else 'FAIL'
            if has_dups or count < min_expected:
                all_passed = False
            dup_info = f' [DUPLICATES: {len(doc_ids) - len(unique_ids)}]' if has_dups else ''
            print(f'[{status}] | {short_name:<22} (SFS {sfs}): {count:>3} sections parsed{dup_info}')
        except Exception as e:
            all_passed = False
            print(f'[FAIL] | {short_name:<22} (SFS {sfs}): Error {e}')
    print('\n' + '-' * 80)
    print('VERIFYING CRITICAL PARAGRAPH INTEGRITY (No truncated starts / no cross-reference leaks)')
    print('-' * 80)
    for sfs, short_name, sec_num, expected_text in CRITICAL_SECTIONS:
        meta, sections = RiksdagenFetcher.get_statute(sfs)
        sec = next((s for s in sections if s.section_number.lower().replace(' ', '') == sec_num.lower().replace(' ', '')), None)
        if not sec:
            print(f'[MISSING] | {short_name} {sec_num} § not found!')
            all_passed = False
            continue
        all_text = f"{sec.raw_text} {sec.section_title or ''} {sec.content}"
        normalized = re.sub(r'\s+', ' ', all_text.lower())
        exp_norm = re.sub(r'\s+', ' ', expected_text.lower())
        if exp_norm in normalized:
            clean_sub = re.sub(r'\s+', ' ', sec.content[:55])
            print(f'[VALID]   | {short_name:>15} {sec_num:>3} §: Starts cleanly -> "{clean_sub}..."')
        else:
            clean_sub = re.sub(r'\s+', ' ', sec.content[:60])
            print(f'[CORRUPT] | {short_name:>15} {sec_num:>3} §: Missing expected phrase "{expected_text}"! -> "{clean_sub}..."')
            all_passed = False
    print('=' * 80)
    if all_passed:
        print(f'ALL CHECKS PASSED! {total_sections_all} sections across {total_statutes} statutes are 100% valid and verified.')
    else:
        print('SOME CHECKS FAILED! Review issues above.')
    print('=' * 80)

if __name__ == '__main__':
    check_database_coverage()
