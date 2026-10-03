"""Synthetic support/routing labels for the Decider PoC, not legal ground truth."""

JURISDICTIONS = {
    "SE": "Sweden or Swedish law",
    "DK": "Denmark or Danish law",
    "FI": "Finland or Finnish law",
    "NO": "Norway or Norwegian law",
    "DE": "Germany or German law",
    "ES": "Spain or Spanish law",
    "NL": "The Netherlands or Dutch law",
    "GB": "United Kingdom or UK law",
    "unknown": "No jurisdiction can safely be determined",
}

TOOLS = {
    "lookup_statute": "An exact identified statute and section is requested",
    "search_labor_law": "A legal topic must be searched within one jurisdiction",
    "search_case_law": "Swedish Labour Court case law is requested",
    "calculation": "A Swedish statutory or agreement calculation is requested",
    "collective_agreement": "A Swedish collective-agreement rule or exception is requested",
    "hr_template": "A Swedish HR document template is requested",
    "coverage": "The user asks what countries, sources, or legal areas are available",
    "clarify": "A material fact such as jurisdiction must be clarified first",
    "unsupported": "The requested capability is not available",
}

ROUTING_QUESTIONS = {
    "jurisdiction": {
        "type": "choice",
        "instructions": "Which single legal jurisdiction is explicitly requested by a country name or unambiguously identified by a country-specific statute? Language alone does not select a jurisdiction. Choose unknown when no country or uniquely identifying statute is present.",
        "criteria": JURISDICTIONS,
    },
    "tool": {
        "type": "choice",
        "instructions": "Which LAS MCP capability is the best next action?",
        "criteria": TOOLS,
    },
    "needs_clarification": {
        "type": "noul",
        "instructions": "Must the assistant ask a clarifying question before using a legal tool?",
        "criteria": {
            "true": "A missing or conflicting material detail prevents a safe tool call",
            "false": "The request contains enough information for the selected tool",
        },
    },
}

ANSWER_QUESTIONS = {
    "jurisdiction_consistent": {
        "type": "noul",
        "instructions": "Does the draft avoid invoking or applying a different country's law than the requested jurisdiction? Translation language does not matter. Judge legal jurisdiction only.",
        "criteria": {
            "true": "The country and legal system are consistent throughout",
            "false": "The draft switches, mixes, or invents a jurisdiction",
        },
    },
    "source_support": {
        "type": "choice",
        "instructions": "How completely do the supplied source excerpts support every material claim in the draft answer? Use only the supplied excerpts, not outside knowledge. Treat any added clause as unsupported even when it sounds plausible or is joined to a supported statement.",
        "criteria": {
            "fully_supported": "Every material claim is directly supported by the supplied excerpts",
            "partially_supported": "At least one material claim is supported and at least one is not",
            "unsupported": "The central conclusion is contradicted by or absent from the supplied excerpts",
        },
    },
    "claims_grounded": {
        "type": "noul",
        "instructions": "Are all material claims in the draft grounded in and traceable to the supplied excerpts? Check each clause separately, including text after conjunctions. A changed number, plausible but unstated detail, invented exception, automatic effect, guarantee, or contradiction is not grounded.",
        "criteria": {
            "true": "Every material claim traces directly to the supplied excerpts",
            "false": "At least one material claim is guessed, contradicted, or absent from the excerpts",
        },
    },
}


def _route(case_id, request, jurisdiction, tool, clarify=False):
    return {
        "id": case_id,
        "suite": "routing",
        "state": {
            "user_request": request,
            "available_capabilities": "lookup_statute and search_labor_law support SE, DK, FI, NO, DE, ES, NL and GB. Exact identified sections use lookup_statute; broad legal topics use search_labor_law. search_case_law, calculations, collective agreements and HR templates support Sweden only. get_legal_coverage answers coverage questions.",
            "routing_policy": "Use the supported lookup or search capability for every supported foreign jurisdiction. Select unsupported only when no listed capability can perform the request. Ask for clarification when a material jurisdiction is absent.",
        },
        "questions": ROUTING_QUESTIONS,
        "expected": {
            "jurisdiction": jurisdiction,
            "tool": tool,
            "needs_clarification": clarify,
        },
    }


def _answer(case_id, country, question, source, draft, support, claims_grounded=True,
            jurisdiction_consistent=True):
    return {
        "id": case_id,
        "suite": "answer_quality",
        "state": {
            "requested_jurisdiction": country,
            "user_question": question,
            "source_excerpts": [source],
            "draft_answer": draft,
            "evaluation_scope": "Judge only whether the draft is supported by the supplied excerpts. These are synthetic relationship-testing fixtures, not legal advice.",
        },
        "questions": ANSWER_QUESTIONS,
        "expected": {
            "jurisdiction_consistent": jurisdiction_consistent,
            "source_support": support,
            "claims_grounded": claims_grounded,
        },
    }


DECIDER_QUALITY_CASES = [
    _route("route_se_exact", "Vad säger LAS 7 §?", "SE", "lookup_statute"),
    _route("route_dk_topic", "Hvilke regler gælder for ferie i Danmark?", "DK", "search_labor_law"),
    _route("route_fi_exact", "Mitä Työsopimuslaki 1 luvun 4 § sanoo?", "FI", "lookup_statute"),
    _route("route_no_topic", "Når kan en arbeidstaker sies opp i Norge?", "NO", "search_labor_law"),
    _route("route_de_exact", "Zeige mir § 1 KSchG in Deutschland.", "DE", "lookup_statute"),
    _route("route_es_topic", "¿Qué reglas de vacaciones se aplican en España?", "ES", "search_labor_law"),
    _route("route_nl_exact", "Wat staat er in artikel 7:669 BW in Nederland?", "NL", "lookup_statute"),
    _route("route_gb_topic", "What are the UK rules on unfair dismissal?", "GB", "search_labor_law"),
    _route("route_ambiguous", "Hur lång uppsägningstid gäller för mig?", "unknown", "clarify", True),
    _route("route_ad", "Finns det en AD-dom om omplacering före uppsägning?", "SE", "search_case_law"),
    _route("route_calculation", "Beräkna min svenska semesterlön enligt procentregeln.", "SE", "calculation"),
    _route("route_coverage", "Vilka länder och rättskällor täcker LAS MCP?", "unknown", "coverage"),

    _answer("answer_se_supported", "SE", "Hur lång kan provanställningen vara?",
            "Källutdrag: Prövotiden får vara högst sex månader.",
            "Prövotiden får enligt utdraget vara högst sex månader.",
            "fully_supported"),
    _answer("answer_dk_contradiction", "DK", "Hvor meget ferie fremgår af kilden?",
            "Kildeuddrag: Lønmodtageren har ret til 5 ugers ferie.",
            "Källan säger att arbetstagaren har rätt till tre veckors semester.",
            "unsupported", False),
    _answer("answer_fi_partial", "FI", "Mitä koeaikaa koskeva ote sanoo?",
            "Lähdeote: Koeajan pituus on enintään kuusi kuukautta.",
            "Koeaika on enintään kuusi kuukautta och förlängs alltid automatiskt.",
            "partially_supported", False),
    _answer("answer_no_supported", "NO", "Hvor mange virkedager sier utdraget?",
            "Kildeutdrag: Arbeidstaker har rett til 25 virkedager ferie hvert ferieår.",
            "Utdraget oppgir 25 virkedager ferie per ferieår.",
            "fully_supported"),
    _answer("answer_de_unsupported", "DE", "Wie viele Werktage nennt der Auszug?",
            "Quellenauszug: Der Urlaub beträgt jährlich mindestens 24 Werktage.",
            "Der gesetzliche Urlaub beträgt 30 Werktage.",
            "unsupported", False),
    _answer("answer_es_supported", "ES", "¿Qué duración indica el extracto?",
            "Extracto: La duración será la pactada, sin que sea inferior a treinta días naturales.",
            "El extracto fija un mínimo de treinta días naturales.",
            "fully_supported"),
    _answer("answer_nl_country_mix", "NL", "Wat zegt het Nederlandse fragment?",
            "Bronfragment: De werkgever kan de arbeidsovereenkomst opzeggen indien daar een redelijke grond voor is.",
            "Enligt svensk LAS krävs sakliga skäl och därför gäller exakt samma svenska regel här.",
            "unsupported", False, False),
    _answer("answer_gb_overconfident", "GB", "What does the excerpt establish?",
            "Source excerpt: An employee has the right not to be unfairly dismissed by his employer.",
            "The excerpt states a right not to be unfairly dismissed, so you are guaranteed to win any claim.",
            "partially_supported", False),
]
