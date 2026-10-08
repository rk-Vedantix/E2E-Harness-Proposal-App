"""
Rule-based proposal generation engine.

Takes every contribution filed against a project (structured form fields,
document text, pasted emails/notes, meeting notes from a BD manager,
engineering notes from multiple engineers/PMs) and turns it into a single
draft proposal: matched domain(s), standards, work packages with effort by
discipline, assumptions, risks and a list of open clarification questions
for anything the inputs didn't cover.

This is scripted/keyword logic, not an LLM call -- see the note at the top
of knowledge_base.py for where a real model call would plug in later.
"""
import re
from collections import defaultdict
from knowledge_base import DOMAINS, ADDON_SIGNALS, DISCIPLINES

VOLUME_PAT = re.compile(r"(\d[\d,]{2,})\s*(units?|vehicles?|pcs?|pieces?)\s*(per\s*year|/\s*yr|p\.?a\.?|annually)", re.I)


def _score_domains(text: str):
    scores = {}
    low = text.lower()
    for key, dom in DOMAINS.items():
        if key == "other":
            continue
        s = 0
        for kw, w in dom["keywords"].items():
            s += low.count(kw.lower()) * w
        scores[key] = s
    return scores


def _score_addons(text: str):
    low = text.lower()
    hits = {}
    for key, sig in ADDON_SIGNALS.items():
        s = sum(low.count(kw.lower()) * w for kw, w in sig["keywords"].items())
        if s > 0:
            hits[key] = s
    return hits


def _merge_work_packages(wp_lists):
    """Combine WPs from one or more domains, de-duplicating by name."""
    seen = {}
    order = []
    for wps in wp_lists:
        for wp in wps:
            name = wp[1]
            if name in seen:
                continue
            seen[name] = wp
            order.append(name)
    # renumber
    out = []
    for i, name in enumerate(order, 1):
        wp = seen[name]
        out.append([f"WP{i}", wp[1], wp[2], list(wp[3])])
    return out


def _detect_missing(text: str, checks):
    missing = []
    for check_id, pattern, question in checks:
        if not re.search(pattern, text, re.I):
            missing.append(question)
    return missing


def generate(contributions):
    """
    contributions: list of dicts with keys
      contributor_name, contributor_role, discipline, input_type, content
    Returns a dict: the structured draft proposal.
    """
    combined_text = "\n".join(c.get("content", "") or "" for c in contributions)
    combined_text = combined_text.strip()

    domain_scores = _score_domains(combined_text)
    ranked = sorted(domain_scores.items(), key=lambda kv: kv[1], reverse=True)
    ranked = [(k, v) for k, v in ranked if v > 0]
    top = []
    if ranked:
        top.append(ranked[0][0])
        # only treat this as a hybrid scope if a second domain scores at least
        # 40% of the top domain's score -- otherwise a few incidental shared
        # words (e.g. "cable", "connector") shouldn't drag in a weak second match
        if len(ranked) > 1 and ranked[1][1] >= max(3, ranked[0][1] * 0.4):
            top.append(ranked[1][0])
    if not top:
        top = ["other"]

    matched_domains = [DOMAINS[k] for k in top]
    hybrid = len(top) > 1

    # Standards: union, de-duplicated by code
    standards = []
    seen_std = set()
    for dom in matched_domains:
        for code, reason in dom["standards"]:
            if code not in seen_std:
                seen_std.add(code)
                standards.append([code, reason])

    # Work packages: merged
    work_packages = _merge_work_packages([dom["work_packages"] for dom in matched_domains])

    # Add-on signals (functional safety, homologation) contribute an extra WP
    addon_hits = _score_addons(combined_text)
    addon_notes = []
    for key, score in addon_hits.items():
        sig = ADDON_SIGNALS[key]
        if sig["wp"] is not None:
            wpn = list(sig["wp"])
            wpn[0] = f"WP{len(work_packages) + 1}"
            # avoid duplicate add-on names
            if not any(w[1] == wpn[1] for w in work_packages):
                work_packages.append(wpn)
                addon_notes.append(f"Detected '{key.replace('_', ' ')}' language in the inputs — added \"{wpn[1]}\".")
        elif key == "low_volume_prototype":
            for wp in work_packages:
                if "manufactur" in wp[1].lower() or "industrial" in wp[1].lower():
                    wp[3] = [round(h * 0.6) for h in wp[3]]
            addon_notes.append("Detected low-volume / prototype-only language — scaled manufacturing-industrialisation effort down.")
        elif key == "high_volume":
            for wp in work_packages:
                if "manufactur" in wp[1].lower() or "industrial" in wp[1].lower():
                    wp[3] = [round(h * 1.3) for h in wp[3]]
            addon_notes.append("Detected high-volume / mass-production language — scaled manufacturing-industrialisation effort up.")

    # Effort totals
    col_totals = [0] * len(DISCIPLINES)
    for wp in work_packages:
        for i, h in enumerate(wp[3]):
            col_totals[i] += h
    base_hours = sum(col_totals)

    contingency_pct = max(dom["contingency"] for dom in matched_domains)
    uncertainty_bonus = 0

    # Missing-info clarifications from matched domains' own checklists
    clarifications = []
    for dom in matched_domains:
        clarifications.extend(_detect_missing(combined_text, dom["missing_checks"]))
    # de-dup while preserving order
    seen_q = set()
    clarifications = [q for q in clarifications if not (q in seen_q or seen_q.add(q))]

    if len(clarifications) >= 3:
        uncertainty_bonus = 3
    if len(contributions) < 2:
        uncertainty_bonus += 2
        clarifications.insert(0, "Only one contributor has provided input so far — consider adding notes from the other disciplines involved before this draft is reviewed.")

    contingency_pct += uncertainty_bonus
    contingency_hours = round(base_hours * contingency_pct / 100)

    # Volume detection for the summary line
    vol_match = VOLUME_PAT.search(combined_text)
    volume_note = vol_match.group(0) if vol_match else None

    # Assumptions / exclusions -- generic scaffolding, domain-flavoured
    assumptions = [
        "This draft is generated from the inputs on file at the time of generation; it has not yet been reviewed by an engineer.",
        "Where a contributor's structured fields conflict with free-text notes, the free-text note was treated as the more recent statement.",
    ]
    if hybrid:
        assumptions.append(f"Inputs matched more than one domain ({', '.join(d['label'] for d in matched_domains)}); work packages below are merged from both and should be checked for scope overlap.")

    exclusions = [
        "Anything not explicitly described in the contributions filed against this project.",
        "Commercial terms, pricing and payment structure (drafted separately once scope is confirmed).",
    ]

    risks = []
    for dom in matched_domains:
        risks.extend(dom["risks"])

    contributors_summary = []
    for c in contributions:
        contributors_summary.append({
            "name": c.get("contributor_name") or "Unnamed",
            "role": c.get("contributor_role") or "",
            "discipline": c.get("discipline") or "",
            "input_type": c.get("input_type") or "",
        })

    return {
        "matched_domains": [{"key": k, "label": DOMAINS[k]["label"], "score": domain_scores.get(k, 0)} for k in top],
        "hybrid": hybrid,
        "standards": standards,
        "work_packages": work_packages,
        "discipline_totals": col_totals,
        "base_hours": base_hours,
        "contingency_pct": contingency_pct,
        "contingency_hours": contingency_hours,
        "total_hours": base_hours + contingency_hours,
        "assumptions": assumptions,
        "exclusions": exclusions,
        "risks": risks,
        "clarifications": clarifications,
        "addon_notes": addon_notes,
        "volume_note": volume_note,
        "contributors": contributors_summary,
        "contribution_count": len(contributions),
    }
