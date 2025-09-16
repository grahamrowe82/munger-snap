"""Logic for Munger Snap heuristics."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple


MOAT_KEYWORDS: Dict[str, str] = {
    "network effect": "Network effects",
    "network effects": "Network effects",
    "switching cost": "Switching costs",
    "switching costs": "Switching costs",
    "brand": "Brand strength",
    "flywheel": "Flywheel",
    "scale": "Scale advantage",
    "cost advantage": "Cost advantage",
    "distribution": "Distribution reach",
    "regulation": "Regulatory license",
}

MANAGEMENT_POSITIVE: Dict[str, str] = {
    "founder-led": "Founder-led",
    "founder led": "Founder-led",
    "owner-operator": "Owner-operator",
    "owner operator": "Owner-operator",
    "insider ownership": "Insider ownership",
    "insider-owned": "Insider ownership",
    "buyback": "Buybacks",
    "buybacks": "Buybacks",
    "roic": "High ROIC",
    "return on capital": "Returns on capital",
    "capital allocator": "Capital allocation",
    "capital allocation": "Capital allocation",
    "skin in the game": "Skin in the game",
}

MANAGEMENT_RED_FLAGS: Dict[str, str] = {
    "restatement": "Accounting restatement",
    "probe": "Regulatory probe",
    "investigation": "Investigation",
    "fraud": "Fraud mention",
    "lawsuit": "Shareholder lawsuit",
    "sec": "SEC scrutiny",
    "resignation": "Leadership turnover",
}

BIAS_KEYWORDS: Dict[str, Tuple[str, List[str]]] = {
    "Incentives": (
        "Incentives",
        [
            "bonus",
            "commission",
            "fees",
            "subsidy",
            "rebate",
            "kickback",
            "option",
            "equity comp",
            "stock grant",
            "performance pay",
            "founder-led",
            "founder led",
            "founder",
            "buyback",
            "buybacks",
            "yield",
            "fcf",
            "owner-operator",
            "owner operator",
            "insider ownership",
        ],
    ),
    "Social-Proof": (
        "Social-Proof",
        [
            "customers",
            "peers",
            "trend",
            "hype",
            "viral",
            "adoption",
            "reference",
            "case study",
            "industry standard",
            "partnership",
            "network effect",
            "network effects",
            "switching cost",
            "switching costs",
            "integrations",
            "integration",
            "community",
        ],
    ),
    "Commitment/Consistency": (
        "Commitment/Consistency",
        [
            "long-term contract",
            "multi-year",
            "switching cost",
            "switching costs",
            "integrations",
            "installed base",
            "locked in",
            "legacy system",
            "prior investment",
        ],
    ),
    "Authority": (
        "Authority",
        [
            "regulator",
            "regulators",
            "regulation",
            "mandate",
            "government",
            "board approval",
            "expert",
            "advisor",
            "consultant",
        ],
    ),
}

INVERSION_RULES: List[Tuple[List[str], str]] = [
    (
        ["network effect", "network effects"],
        "What breaks network effects? (regulatory fee caps, platform API changes, competitor subsidies).",
    ),
    (
        ["switching cost", "switching costs"],
        "What erodes switching costs? (migration tooling, interoperability mandates, bundled pricing).",
    ),
    (
        ["brand"],
        "Where does the brand lose trust? (quality lapses, pricing power pushback, reputational hits).",
    ),
    (
        ["cost advantage", "scale"],
        "Who undercuts the cost advantage? (input inflation, vertical integration, price wars).",
    ),
    (
        ["regulation", "license"],
        "How could regulation flip? (license removal, new entrants approved, compliance burdens).",
    ),
]


@dataclass
class FilterResult:
    status: str
    details: str = ""
    hits: List[str] | None = None


@dataclass
class Snapshot:
    filters: Dict[str, FilterResult]
    invert: str
    biases: List[str]
    posture: str
    copy_text: str


def _tokenize_words(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9']+", text.lower())


def _count_sentences(text: str) -> List[str]:
    parts = re.split(r"[.!?]+", text)
    return [p.strip() for p in parts if p.strip()]


def _count_paragraphs(text: str) -> int:
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    return len(paragraphs) if paragraphs else (1 if text.strip() else 0)


def _parse_number(raw: str | None) -> float | None:
    if raw is None:
        return None
    text = raw.strip().lower()
    if not text:
        return None
    text = text.replace("%", "")
    text = text.replace("~", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _score_understandable(thesis: str) -> FilterResult:
    cleaned = thesis.strip()
    if not cleaned:
        return FilterResult("Fail", "Add a concise thesis summary.")

    sentences = _count_sentences(cleaned)
    words = _tokenize_words(cleaned)
    first_sentence_words = _tokenize_words(sentences[0]) if sentences else []
    long_words = [w for w in words if len(w) > 12]
    long_word_ratio = len(long_words) / max(len(words), 1)
    paragraphs = _count_paragraphs(cleaned)

    conditions = {
        "summary": len(first_sentence_words) <= 30,
        "jargon": long_word_ratio <= 0.2,
        "segments": paragraphs <= 2,
    }

    if all(conditions.values()):
        return FilterResult("Pass", "Clear one-sentence hook; jargon in check.")

    misses: List[str] = []
    if not conditions["summary"]:
        misses.append("Add a <=30 word summary line up top.")
    if not conditions["jargon"]:
        misses.append("High jargon density—clarify plain language.")
    if not conditions["segments"]:
        misses.append("Too many disjoint segments—tighten focus.")
    return FilterResult("Fail", " ".join(misses))


def _score_moat(thesis: str) -> FilterResult:
    text = thesis.lower()
    hits: List[str] = []
    for keyword, label in MOAT_KEYWORDS.items():
        if keyword in text and label not in hits:
            hits.append(label)
    if hits:
        return FilterResult("Pass", ", ".join(hits), hits=hits)
    return FilterResult("Fail", "Spell out the moat (network effects, switching costs, brand, cost advantage).")


def _score_management(thesis: str) -> FilterResult:
    text = thesis.lower()
    positives: List[str] = []
    for keyword, label in MANAGEMENT_POSITIVE.items():
        if keyword in text and label not in positives:
            positives.append(label)
    negatives: List[str] = []
    for keyword, label in MANAGEMENT_RED_FLAGS.items():
        if keyword in text and label not in negatives:
            negatives.append(label)

    if negatives:
        return FilterResult("Fail", f"Red flags: {', '.join(negatives)}")
    if positives:
        return FilterResult("Pass", ", ".join(positives))
    return FilterResult("Fail", "Note owner-operator traits, insider ownership, or capital allocation history.")


def _score_margin_of_safety(pe_text: str | None, fcf_yield_text: str | None) -> FilterResult:
    pe = _parse_number(pe_text)
    fcf_yield = _parse_number(fcf_yield_text)

    if pe is not None and pe <= 15:
        return FilterResult("Pass", f"P/E {pe:.1f} within <=15 guardrail.")
    if fcf_yield is not None and fcf_yield >= 6:
        return FilterResult("Pass", f"FCF yield {fcf_yield:.1f}% clears >=6% bar.")

    if pe is not None or fcf_yield is not None:
        details: List[str] = []
        if pe is not None:
            details.append(f"P/E {pe:.1f} > 15")
        if fcf_yield is not None:
            details.append(f"FCF yield {fcf_yield:.1f}% < 6%")
        return FilterResult("Fail", "; ".join(details))

    return FilterResult("Needs Data", "— add P/E or FCF-yield to judge MOS.")


def _rank_biases(thesis: str) -> List[str]:
    text = thesis.lower()
    ordered_biases: List[str] = []
    triggered: List[str] = []
    for _, (display, keywords) in BIAS_KEYWORDS.items():
        ordered_biases.append(display)
        if any(keyword in text for keyword in keywords):
            triggered.append(display)

    final: List[str] = []
    for bias in ordered_biases:
        if bias in triggered and bias not in final:
            final.append(bias)
    for bias in ordered_biases:
        if bias not in final:
            final.append(bias)
    return final[:3]


def _invert_question(thesis: str, moat_result: FilterResult) -> str:
    text = thesis.lower()
    if moat_result.hits:
        moat_hits = [hit.lower() for hit in moat_result.hits]
    else:
        moat_hits = []
    for keywords, prompt in INVERSION_RULES:
        if any(k in text for k in keywords):
            return prompt
        if moat_hits and any(any(k in hit for k in keywords) for hit in moat_hits):
            return prompt
    return "What would have to be true for this to fail? Pressure-test customer churn, pricing power, and management behavior."


def _posture(filters: Dict[str, FilterResult]) -> str:
    passes = sum(1 for f in filters.values() if f.status == "Pass")
    fails = sum(1 for f in filters.values() if f.status == "Fail")
    needs = sum(1 for f in filters.values() if f.status == "Needs Data")

    if fails >= 2:
        return "No"
    if fails == 0 and needs == 0 and passes >= 3:
        return "Go"
    return "Wait"


def _build_copy(filters: Dict[str, FilterResult], invert: str, biases: List[str], posture: str) -> str:
    lines = ["Four-Filters Snapshot"]
    for name, result in filters.items():
        detail = f" — {result.details}" if result.details else ""
        lines.append(f"{name}: {result.status}{detail}")
    lines.append(f"Invert: {invert}")
    lines.append("Bias Risks: " + ", ".join(biases))
    lines.append(f"Posture: {posture}")
    return "\n".join(lines)


def four_filters(thesis: str, pe_text: str | None = None, fcf_yield_text: str | None = None) -> Snapshot:
    filters = {
        "Understandable": _score_understandable(thesis),
        "Moat": _score_moat(thesis),
        "Management": _score_management(thesis),
        "Margin of Safety": _score_margin_of_safety(pe_text, fcf_yield_text),
    }
    invert = _invert_question(thesis, filters["Moat"])
    biases = _rank_biases(thesis)
    posture = _posture(filters)
    copy_text = _build_copy(filters, invert, biases, posture)
    return Snapshot(filters=filters, invert=invert, biases=biases, posture=posture, copy_text=copy_text)


__all__ = ["four_filters", "Snapshot", "FilterResult"]
