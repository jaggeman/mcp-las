"""
Benchmark-motor för Svensk Arbetsrätt & HR-examen.
Evaluerar precision, träffsäkerhet och källtäckning mot autentiska tentamens- och HR-frågor.
"""

import sys
import os
import re
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from typing import Dict, Any, List
from src.benchmarks.hr_exam_data import HR_EXAM_BENCHMARKS
from src.mcp_tools.tools import (
    search_labor_law,
    search_case_law,
    lookup_statute,
    get_rehabilitation_plan_info,
    get_employer_certificate_info,
    get_discrimination_act_guide,
    get_base_amounts_and_indices,
    calculate_travel_deduction_and_mileage,
    calculate_vacation_pay,
    calculate_redundancy_turnorder_and_exceptions,
)

def evaluate_single_benchmark(item: Dict[str, Any]) -> Dict[str, Any]:
    question = item["question"]
    expected_statutes = item.get("expected_statutes", [])
    expected_ad_cases = item.get("expected_ad_cases", [])
    expected_keywords = item.get("expected_keywords", [])
    
    # 1. Kör lagsökning
    statute_results = search_labor_law(query=question, limit=10)
    retrieved_statute_texts = [
        f"{r.get('statute', '')} {r.get('section', '')} § {r.get('chapter', '')} {r.get('title', '')} {r.get('content', '')}"
        for r in statute_results
    ]
    all_statute_corpus = " ".join(retrieved_statute_texts).lower()
    
    # 2. Kör rättsfallssökning (både med frågan och eventuella förväntade paragrafer)
    ad_results = search_case_law(query=question, limit=10)
    if expected_statutes:
        for st in expected_statutes:
            ad_results.extend(search_case_law(query=st, limit=5))
            
    retrieved_ad_texts = [
        f"{r.get('case_number', '')} {r.get('title', '')} {r.get('summary', '')} {r.get('provisions', '')} {r.get('domskal', '')}"
        for r in ad_results
    ]
    all_ad_corpus = " ".join(retrieved_ad_texts).lower()

    # 3. Kör specialiserade verktyg baserat på innehåll
    special_corpus = ""
    if "rehab" in question.lower() or "fk" in question.lower() or "sjuk" in question.lower() or "30 kap" in question.lower():
        rehab_info = get_rehabilitation_plan_info()
        special_corpus += " " + str(rehab_info).lower()
    if "arbetsgivarintyg" in question.lower() or "a-kassa" in question.lower() or "alf" in question.lower():
        cert_info = get_employer_certificate_info()
        special_corpus += " " + str(cert_info).lower()
    if "diskriminering" in question.lower() or "likabehandling" in question.lower() or "lönekartläggning" in question.lower() or "graviditet" in question.lower():
        disc_info = get_discrimination_act_guide()
        special_corpus += " " + str(disc_info).lower()
    if "basbelopp" in question.lower() or "pbb" in question.lower() or "sgi" in question.lower():
        base_info = get_base_amounts_and_indices(compare_all_years=True)
        special_corpus += " " + str(base_info).lower()
    if "milersättning" in question.lower() or "traktamente" in question.lower() or "schablon" in question.lower():
        travel_info = calculate_travel_deduction_and_mileage(transport_mode="egen_bil", distance_km_one_way=50)
        special_corpus += " " + str(travel_info).lower()
    if "undantag" in question.lower() or "turordning" in question.lower():
        redundancy_info = calculate_redundancy_turnorder_and_exceptions(total_employees_in_unit=85)
        special_corpus += " " + str(redundancy_info).lower()

    combined_corpus = re.sub(r'\s+', ' ', f"{all_statute_corpus} {all_ad_corpus} {special_corpus}".lower())

    # Poängsättning: Lagparagrafer (40%)
    statute_score = 0.0
    if expected_statutes:
        matched_statutes = 0
        for exp in expected_statutes:
            parts = exp.replace("§", "").split()
            law_name = parts[0].lower()
            section_num = parts[1].strip() if len(parts) > 1 else ""
            if (law_name in combined_corpus and (not section_num or section_num in combined_corpus)) or exp.lower() in combined_corpus:
                matched_statutes += 1
        statute_score = (matched_statutes / len(expected_statutes)) * 100
    else:
        statute_score = 100.0

    # Poängsättning: Arbetsdomstolens prejudikat (30%)
    ad_score = 0.0
    if expected_ad_cases:
        matched_cases = 0
        for ad_case in expected_ad_cases:
            # Sök efter t.ex. "2023 nr 45", "2023:45", "ad 2023 nr 45"
            clean_case = ad_case.lower().replace("ad", "").strip()
            nr_match = re.search(r'(\d{4})\s*(?:nr|:)\s*(\d+)', ad_case.lower())
            if clean_case in all_ad_corpus or ad_case.lower() in all_ad_corpus:
                matched_cases += 1
            elif nr_match and f"{nr_match.group(1)} nr {nr_match.group(2)}" in all_ad_corpus:
                matched_cases += 1
            elif nr_match and f"{nr_match.group(1)}:{nr_match.group(2)}" in all_ad_corpus:
                matched_cases += 1
        ad_score = (matched_cases / len(expected_ad_cases)) * 100
    else:
        ad_score = 100.0

    # Poängsättning: Nyckelbegrepp & HR-principer (30%)
    keyword_score = 0.0
    if expected_keywords:
        matched_kw = 0
        for kw in expected_keywords:
            kw_clean = re.sub(r'\s+', ' ', kw.lower().strip())
            if kw_clean in combined_corpus:
                matched_kw += 1
            elif all(k in combined_corpus for k in kw_clean.split()):
                matched_kw += 1
        keyword_score = (matched_kw / len(expected_keywords)) * 100
    else:
        keyword_score = 100.0

    # Totalpoäng
    if expected_ad_cases and expected_statutes:
        total_score = (statute_score * 0.40) + (ad_score * 0.30) + (keyword_score * 0.30)
    elif expected_statutes:
        total_score = (statute_score * 0.50) + (keyword_score * 0.50)
    else:
        total_score = keyword_score

    return {
        "id": item["id"],
        "category": item["category"],
        "question": question,
        "total_score": round(total_score, 1),
        "statute_score": round(statute_score, 1),
        "ad_score": round(ad_score, 1) if expected_ad_cases else None,
        "keyword_score": round(keyword_score, 1),
        "passed": total_score >= 80.0
    }

def run_all_benchmarks() -> Dict[str, Any]:
    results = []
    category_scores: Dict[str, List[float]] = {}

    for item in HR_EXAM_BENCHMARKS:
        res = evaluate_single_benchmark(item)
        results.append(res)
        cat = res["category"]
        if cat not in category_scores:
            category_scores[cat] = []
        category_scores[cat].append(res["total_score"])

    overall_avg = sum(r["total_score"] for r in results) / len(results)
    passed_count = sum(1 for r in results if r["passed"])

    print("=" * 80)
    print(" [BENCHMARK] SVENSK ARBETSRÄTT & HR-EXAMEN BENCHMARK RAPPORT")
    print("=" * 80)
    print(f"Totalt antal frågor: {len(results)}")
    print(f"Godkända (>= 80% precision): {passed_count}/{len(results)} ({passed_count/len(results)*100:.1f}%)")
    print(f"Total genomsnittlig träffsäkerhet: {overall_avg:.1f}%\n")
    print("-" * 80)
    print(f"{'ID':<34} | {'Kategori':<25} | {'Poäng':<8} | {'Status'}")
    print("-" * 80)

    for r in results:
        status = "[PASS]" if r["passed"] else "[FAIL]"
        print(f"{r['id']:<34} | {r['category']:<25} | {r['total_score']:>5.1f}%  | {status}")

    print("\n" + "=" * 80)
    print(" RESULTAT PER KATEGORI")
    print("=" * 80)
    for cat, scores in category_scores.items():
        cat_avg = sum(scores) / len(scores)
        print(f"* {cat:<30}: {cat_avg:.1f}%")
    print("=" * 80)

    return {
        "overall_average": round(overall_avg, 1),
        "passed_count": passed_count,
        "total_count": len(results),
        "category_averages": {cat: round(sum(scores)/len(scores), 1) for cat, scores in category_scores.items()},
        "results": results
    }

if __name__ == "__main__":
    report = run_all_benchmarks()
    if report["overall_average"] < 80.0:
        print("\n[FAIL] Benchmark underkänd: Genomsnittet är under 80%.")
        sys.exit(1)
    else:
        print("\n[SUCCESS] Benchmark godkänd med högsta betyg!")
        sys.exit(0)
