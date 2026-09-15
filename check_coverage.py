# -*- coding: utf-8 -*-
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from src.scrapers.riksdagen_fetcher import RiksdagenFetcher
from src.chunking.law_chunker import LawChunker
from src.services.sync_service import DEFAULT_STATUTES

LAWS_TO_CHECK = [
    ('1982:80', 'LAS', 50),
    ('1977:480', 'Semesterlagen', 30),
    ('1976:580', 'MBL', 60),
    ('1982:673', 'Arbetstidslagen', 25),
    ('2008:567', 'Diskrimineringslagen', 60),
    ('1977:1160', 'Arbetsmiljölagen', 80),
    ('1991:1047', 'Sjuklönelagen', 20),
    ('1995:584', 'Föräldraledighetslagen', 20),
    ('1974:981', 'Studieledighetslagen', 10),
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

def _where(sec):
    """'2 kap. 6 §' i flerkapitellagar, '6 §' i ovriga."""
    return f"{sec.chapter} kap. {sec.section_number} §" if sec.chapter else f"{sec.section_number} §"

_STATUTE_CACHE = {}

def fetch_statute(sfs):
    """Hamtar en lag en gang per korning, inte en gang per slinga."""
    if sfs not in _STATUTE_CACHE:
        _STATUTE_CACHE[sfs] = RiksdagenFetcher.get_statute(sfs)
    return _STATUTE_CACHE[sfs]

def check_database_coverage():
    print('=' * 80)
    print('SWEDISH LABOR LAW DATABASE COVERAGE & CHUNKER INTEGRITY CHECK')
    print('=' * 80)
    total_statutes = len(LAWS_TO_CHECK)
    total_sections_all = 0
    all_passed = True

    # En lag som ingesteras men saknas har blir aldrig tackningsverifierad.
    # Studieledighetslagen foll ur pa precis det sattet.
    unchecked = [s for s in DEFAULT_STATUTES if s not in {x[0] for x in LAWS_TO_CHECK}]
    if unchecked:
        all_passed = False
        print(f'[FAIL] | Ingesteras men tackningskontrolleras inte: {", ".join(unchecked)}')
        print('        Lagg till dem i LAWS_TO_CHECK med ett rimligt minimiantal paragrafer.\n')

    for sfs, short_name, min_expected in LAWS_TO_CHECK:
        try:
            meta, sections = fetch_statute(sfs)
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
        try:
            meta, sections = fetch_statute(sfs)
        except Exception as e:
            all_passed = False
            print(f'[FAIL]    | {short_name:>15} {sec_num:>3} §: Kunde inte hamta SFS {sfs} ({e})')
            continue
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
    print('\n' + '-' * 80)
    print('INVARIANTS ACROSS EVERY PARSED SECTION (not just the sampled ones)')
    print('-' * 80)
    # Stickproven ovan tacker 13 paragrafer. Felklassen i #6 - korsreferenser
    # som blir paragrafer - drabbar alla lagar, sa invarianterna kors over
    # allt som parsas. Ingen av dem kraver att nagon kan lagarnas
    # paragrafuppsattning utantill.
    for sfs, short_name, _min in LAWS_TO_CHECK:
        try:
            meta, sections = fetch_statute(sfs)
        except Exception as e:
            all_passed = False
            print(f'[FAIL] | {short_name:<22}: kunde inte hamtas ({e})')
            continue

        problems = []

        # Lagtext borjar med versal eller siffra. Gemen bokstav betyder att
        # sektionen borjar mitt i en mening - en korsreferens, inte en rubrik.
        for sec in sections:
            head = sec.content.lstrip()[:1]
            if head.islower():
                problems.append(f'{_where(sec)} borjar gement: "{sec.content[:60]}..."')

        # Ikrafttradandepunkter ska ha klippts bort med overgangsbestammelserna.
        # Riksdagens redaktionella markering ar inte lagtext. Den star forst i
        # paragrafen och inleds med snedstreck: "/Upphor att galla U:.../".
        # Den forsta versionen av den har kontrollen letade bara efter
        # "trader i kraft" och sag darfor inte den UTGAENDE markeringen alls -
        # CI rapporterade ALL CHECKS PASSED medan fem paragrafer i databasen
        # borjade med en markeringsrad.
        for sec in sections:
            if sec.content.lstrip().startswith('/'):
                forsta = re.sub(r'\s+', ' ', sec.content.lstrip()[:70])
                problems.append(f'{_where(sec)}: borjar med redaktionell markering -> "{forsta}..."')
                continue
            low = sec.content.lower()
            for marker in ('träder i kraft', 'upphör att gälla', 'i den äldre lydelsen'):
                at = low.find(marker)
                if at >= 0:
                    # Utdraget runt traffen ar hela diagnosen: det avgor om
                    # overgangsbestammelserna lackt in, eller om paragrafen
                    # sjalv legitimt talar om ikrafttradande.
                    snippet = re.sub(r'\s+', ' ', sec.content[max(0, at - 60):at + 80])
                    problems.append(
                        f'{_where(sec)}: mojlig overgangsbestammelse -> "...{snippet}..."'
                    )
                    break

        # En paragraf far inte innehalla nasta paragrafs rubrik. Det ar exakt
        # vad som hander nar en akta paragrafstart forkastas av filtret: dess
        # text hamnar inuti paragrafen fore, och den forsvinner ur databasen.
        # LAS 34 § innehall hela 35 § pa det sattet, och lookup_statute for
        # 35 § fanns inte alls - osynligt for bade antalskontrollen (antalet
        # ser rimligt ut) och stickproven (34 § innehaller ratt text OCKSA).
        for sec in sections:
            svald = re.search(r'\n\s*(\d+\s*[a-z]?)\s*§\s+[A-ZÅÄÖ]', sec.content)
            if svald:
                problems.append(
                    f'{_where(sec)}: innehaller rubriken for {svald.group(1).strip()} § '
                    f'- den paragrafen har sannolikt forkastats och forsvunnit'
                )

        # Paragrafnumren stiger inom ett kapitel.
        by_chapter = {}
        for sec in sections:
            by_chapter.setdefault(sec.chapter, []).append(sec)
        for chap, secs in by_chapter.items():
            keys = [LawChunker._order_key(x.section_number) for x in secs]
            for a, b in zip(keys, keys[1:]):
                if b <= a:
                    where = f'{chap} kap. ' if chap else ''
                    problems.append(f'{where}{a[0]}{a[1]} § foljs av {b[0]}{b[1]} § - fel ordning')

        # Dubbletter skrivs inte over langre, de hoppas over - och da
        # forsvinner den riktiga paragrafens innehall tyst.
        ids = [x.id for x in sections]
        if len(ids) != len(set(ids)):
            problems.append(f'{len(ids) - len(set(ids))} dubbletter bland doc_id')

        if problems:
            all_passed = False
            print(f'[FAIL] | {short_name:<22}: {len(problems)} problem')
            for line in problems[:8]:
                print(f'        - {line}')
            if len(problems) > 8:
                print(f'        ... och {len(problems) - 8} till')
        else:
            print(f'[OK]   | {short_name:<22}: {len(sections)} paragrafer, inga invariantbrott')

    print('=' * 80)
    if all_passed:
        print(f'ALL CHECKS PASSED! {total_sections_all} sections across {total_statutes} statutes are 100% valid and verified.')
    else:
        print('SOME CHECKS FAILED! Review issues above.')
    print('=' * 80)
    return all_passed

if __name__ == '__main__':
    # Utan exitkod var det har steget en utskrift, inte en kontroll: CI
    # rapporterade gront aven nar utskriften sa SOME CHECKS FAILED.
    sys.exit(0 if check_database_coverage() else 1)
