"""
score_signals.py

Individual scoring functions for each signal dimension.
All scores returned are normalized to [0, 1] unless noted.
"""

import math
import re
from datetime import datetime, date

from skills_taxonomy import (
    TIER1_SKILLS, TIER2_SKILLS, TIER3_SKILLS,
    TIER1_WEIGHT, TIER2_WEIGHT, TIER3_WEIGHT,
    PROFICIENCY_WEIGHTS,
    PRODUCTION_KEYWORDS, RESEARCH_KEYWORDS,
    HIGHLY_RELEVANT_TITLES, RELEVANT_TITLES, IRRELEVANT_TITLES,
    HRTECH_KEYWORDS, OPENSOURCE_KEYWORDS,
    COMPANY_SIZE_SCORES,
)

TODAY = date(2026, 6, 15)


def _normalize(val: float, max_val: float) -> float:
    """Clamp and normalize to [0, 1]."""
    return min(1.0, max(0.0, val / max_val))


def _text_keyword_score(text: str, keywords: list[str]) -> float:
    """Count keyword hits in lowercased text, return hits / len(keywords) clamped at 1."""
    if not text:
        return 0.0
    text_lower = text.lower()
    hits = sum(1 for kw in keywords if kw in text_lower)
    return min(1.0, hits / max(1, len(keywords) * 0.15))  # 15% coverage = full score


def _get_tier(skill_name: str) -> tuple[float, float]:
    """
    Return (tier_weight, found) for a skill name.
    Checks all tiers and returns the highest matching tier.
    """
    name_lower = skill_name.lower().strip()
    if name_lower in TIER1_SKILLS:
        return TIER1_WEIGHT, True
    if name_lower in TIER2_SKILLS:
        return TIER2_WEIGHT, True
    if name_lower in TIER3_SKILLS:
        return TIER3_WEIGHT, True

    # Partial match fallback for compound skills
    for ts in TIER1_SKILLS:
        if ts in name_lower or name_lower in ts:
            return TIER1_WEIGHT * 0.7, True
    for ts in TIER2_SKILLS:
        if ts in name_lower or name_lower in ts:
            return TIER2_WEIGHT * 0.7, True

    return 0.0, False


# ===========================================================================
# SIGNAL 1: Core AI/ML Skills Match (35%)
# ===========================================================================
def score_skills(candidate: dict) -> float:
    """
    Score how well candidate's listed skills match the JD requirements.
    Uses proficiency, endorsements, duration, and tier weighting.
    Returns normalized score [0, 1].
    """
    skills = candidate.get("skills", [])
    if not skills:
        return 0.0

    raw_total = 0.0
    max_possible = TIER1_WEIGHT * 10  # theoretical max if 10 tier1 expert skills

    for skill in skills:
        name = skill.get("name", "")
        proficiency = skill.get("proficiency", "beginner")
        endorsements = skill.get("endorsements", 0)
        duration_months = skill.get("duration_months", 0)

        tier_w, found = _get_tier(name)
        if not found:
            continue

        prof_w = PROFICIENCY_WEIGHTS.get(proficiency, 0.35)

        # Duration factor: ramps up to 1.0 at 24 months
        dur_factor = min(1.0, duration_months / 24.0)

        # Endorsement factor: log-scaled, caps at 50 endorsements
        end_factor = min(1.0, math.log1p(endorsements) / math.log1p(50))

        skill_score = tier_w * prof_w * (0.6 + 0.25 * dur_factor + 0.15 * end_factor)
        raw_total += skill_score

    # Also check platform skill assessment scores
    assessment_scores = candidate.get("redrob_signals", {}).get("skill_assessment_scores", {})
    for skill_name, score in assessment_scores.items():
        tier_w, found = _get_tier(skill_name)
        if found and tier_w >= TIER2_WEIGHT:
            # Bonus for having taken the assessment at 70%+
            if score >= 70:
                raw_total += tier_w * 0.3

    return _normalize(raw_total, max_possible)


def score_skill_text(candidate: dict) -> float:
    """
    Scan career history descriptions for AI/ML technical keywords.
    This catches candidates whose skills list doesn't fully reflect expertise.
    Returns normalized score [0, 1].
    """
    all_text = " ".join(
        role.get("description", "") for role in candidate.get("career_history", [])
    )
    summary = candidate.get("profile", {}).get("summary", "")
    headline = candidate.get("profile", {}).get("headline", "")
    all_text = f"{headline} {summary} {all_text}"

    # Combine tier1 and tier2 as the important signal here
    combined_keywords = list(TIER1_SKILLS)[:25] + [
        "embeddings", "retrieval", "ranking", "vector", "semantic search",
        "machine learning", "deep learning", "transformer", "bert",
        "pytorch", "tensorflow", "nlp", "recommendation", "fine-tuning",
        "model serving", "production", "a/b test",
    ]
    return _text_keyword_score(all_text, combined_keywords)


# ===========================================================================
# SIGNAL 2: Experience Fit (20%)
# ===========================================================================
def score_experience(candidate: dict) -> float:
    """
    Score experience fit for 5-9 years target range.
    Uses a Gaussian-like function peaking at 7 years.
    """
    profile = candidate.get("profile", {})
    years = profile.get("years_of_experience", 0)

    # Gaussian peak at 7 years, standard deviation = 3
    # Score drops but doesn't reach 0 outside range
    ideal = 7.0
    sigma = 3.0
    yrs_score = math.exp(-0.5 * ((years - ideal) / sigma) ** 2)

    # Slight penalty for very junior or very senior
    if years < 3:
        yrs_score *= 0.5
    elif years > 18:
        yrs_score *= 0.7

    # Title relevance
    title = profile.get("current_title", "").lower().strip()
    title_score = 0.3  # default neutral
    for t in HIGHLY_RELEVANT_TITLES:
        if t in title:
            title_score = 1.0
            break
    else:
        for t in RELEVANT_TITLES:
            if t in title:
                title_score = 0.6
                break
        else:
            for t in IRRELEVANT_TITLES:
                if t in title:
                    title_score = 0.1
                    break

    # Industry bonus
    industry = profile.get("current_industry", "").lower()
    industry_score = 0.5
    if any(kw in industry for kw in ["software", "tech", "it", "ai", "ml", "saas", "fintech"]):
        industry_score = 1.0
    elif any(kw in industry for kw in ["consulting", "services"]):
        industry_score = 0.7

    return yrs_score * 0.5 + title_score * 0.3 + industry_score * 0.2


# ===========================================================================
# SIGNAL 3: Career Depth / Production Score (15%)
# ===========================================================================
def score_career_depth(candidate: dict) -> float:
    """
    Score based on depth of production ML experience in career history.
    Rewards production deployment language; penalizes pure-research language.
    """
    career = candidate.get("career_history", [])
    if not career:
        return 0.0

    total_production = 0.0
    total_research_penalty = 0.0
    total_company_score = 0.0
    n_roles = len(career)

    # Duration of most recent roles matters more
    for i, role in enumerate(career):
        desc = role.get("description", "").lower()
        recency_weight = 1.0 if i == 0 else max(0.3, 1.0 - i * 0.2)

        # Production signal
        prod_score = _text_keyword_score(desc, PRODUCTION_KEYWORDS)
        total_production += prod_score * recency_weight

        # Research penalty
        research_score = _text_keyword_score(desc, RESEARCH_KEYWORDS)
        total_research_penalty += research_score * recency_weight

        # Company size proxy for scale
        csize = role.get("company_size", "1-10")
        total_company_score += COMPANY_SIZE_SCORES.get(csize, 0.3)

    avg_production = total_production / n_roles
    avg_research = total_research_penalty / n_roles
    avg_company = total_company_score / n_roles

    # Net production score — penalized by research signals
    net_production = max(0.0, avg_production - avg_research * 0.5)

    # Check for recent activity (last_active_date)
    signals = candidate.get("redrob_signals", {})
    last_active_str = signals.get("last_active_date", "")
    recency_score = 0.5
    if last_active_str:
        try:
            last_active = date.fromisoformat(last_active_str)
            days_since = (TODAY - last_active).days
            if days_since <= 30:
                recency_score = 1.0
            elif days_since <= 90:
                recency_score = 0.8
            elif days_since <= 180:
                recency_score = 0.6
            elif days_since <= 365:
                recency_score = 0.4
            else:
                recency_score = 0.2
        except (ValueError, TypeError):
            pass

    return net_production * 0.5 + avg_company * 0.3 + recency_score * 0.2


# ===========================================================================
# SIGNAL 4: Platform / Behavioral Signals (15%)
# ===========================================================================
def score_behavioral(candidate: dict) -> float:
    """
    Score platform engagement and behavioral signals from redrob_signals.
    """
    sig = candidate.get("redrob_signals", {})

    # Profile completeness (0-100 → 0-1)
    completeness = sig.get("profile_completeness_score", 0) / 100.0

    # Open to work
    open_to_work = 1.0 if sig.get("open_to_work_flag", False) else 0.4

    # Recruiter response rate (0-1)
    response_rate = sig.get("recruiter_response_rate", 0.0)

    # Interview completion rate (0-1)
    interview_rate = sig.get("interview_completion_rate", 0.5)

    # GitHub activity (0-100, -1 means not linked)
    github_raw = sig.get("github_activity_score", -1)
    github_score = 0.3 if github_raw == -1 else github_raw / 100.0

    # Avg response time: lower is better (cap at 168h = 1 week)
    avg_response_hrs = sig.get("avg_response_time_hours", 100)
    response_time_score = max(0.0, 1.0 - avg_response_hrs / 168.0)

    # Verification trust
    verified = (
        (1 if sig.get("verified_email", False) else 0) +
        (1 if sig.get("verified_phone", False) else 0) +
        (0.5 if sig.get("linkedin_connected", False) else 0)
    ) / 2.5

    # Saved by recruiters (organic demand signal, log-scaled)
    saved = sig.get("saved_by_recruiters_30d", 0)
    saved_score = min(1.0, math.log1p(saved) / math.log1p(20))

    # Weighted composite
    behavioral = (
        completeness * 0.15 +
        open_to_work * 0.15 +
        response_rate * 0.20 +
        interview_rate * 0.15 +
        github_score * 0.15 +
        response_time_score * 0.05 +
        verified * 0.10 +
        saved_score * 0.05
    )

    return behavioral


# ===========================================================================
# SIGNAL 5: Nice-to-Have Bonuses (10%)
# ===========================================================================
def score_bonuses(candidate: dict) -> float:
    """
    Bonus scoring for nice-to-have signals: LLM fine-tuning, LTR, HR-tech, OSS.
    Returns [0, 1].
    """
    bonus = 0.0

    # Check skills for LLM fine-tuning
    skills = candidate.get("skills", [])
    finetune_skills = {"lora", "qlora", "peft", "fine-tuning llms", "rlhf", "dpo", "sft"}
    ltr_skills = {"learning to rank", "ltr", "lambdarank", "xgboost", "lightgbm"}

    for skill in skills:
        name = skill.lower() if isinstance(skill, str) else skill.get("name", "").lower()
        if name in finetune_skills:
            bonus += 0.15
            break

    for skill in skills:
        name = skill.lower() if isinstance(skill, str) else skill.get("name", "").lower()
        if name in ltr_skills:
            bonus += 0.10
            break

    # Career history text for HR-tech and open source
    all_text = " ".join(
        role.get("description", "") for role in candidate.get("career_history", [])
    ).lower()
    summary = candidate.get("profile", {}).get("summary", "").lower()
    full_text = f"{all_text} {summary}"

    hr_score = _text_keyword_score(full_text, HRTECH_KEYWORDS)
    bonus += hr_score * 0.20

    oss_score = _text_keyword_score(full_text, OPENSOURCE_KEYWORDS)
    bonus += oss_score * 0.15

    # Certifications bonus for relevant certs
    certs = candidate.get("certifications", [])
    relevant_certs = {"aws certified", "gcp", "azure", "tensorflow", "pytorch", "coursera ml",
                      "deep learning", "machine learning", "databricks"}
    for cert in certs:
        cert_name = cert.get("name", "").lower()
        if any(rc in cert_name for rc in relevant_certs):
            bonus += 0.08
            break

    # Education tier bonus
    edu = candidate.get("education", [])
    for e in edu:
        tier = e.get("tier", "unknown")
        if tier == "tier_1":
            bonus += 0.12
            break
        elif tier == "tier_2":
            bonus += 0.06
            break

    return min(1.0, bonus)


# ===========================================================================
# SIGNAL 6: Disqualifier Detection
# ===========================================================================
def compute_disqualifier_penalty(candidate: dict) -> float:
    """
    Detect hard disqualifiers from JD and return a penalty [0, 1].
    1.0 = maximum penalty (near-disqualified), 0.0 = no penalty.
    """
    penalty = 0.0
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    skills = candidate.get("skills", [])

    # --- Disqualifier 1: Zero relevant AI/ML skills ---
    has_any_ai_skill = False
    for skill in skills:
        name = skill.get("name", "").lower()
        tier_w, found = _get_tier(name)
        if found and tier_w >= TIER2_WEIGHT:
            has_any_ai_skill = True
            break

    # Also check text
    all_text = " ".join(role.get("description", "") for role in career).lower()
    summary = profile.get("summary", "").lower()
    ai_keywords_in_text = any(kw in f"{all_text} {summary}" for kw in [
        "machine learning", "ml", "neural network", "deep learning",
        "embedding", "nlp", "llm", "ai ", "artificial intelligence",
        "model training", "model serving"
    ])

    if not has_any_ai_skill and not ai_keywords_in_text:
        penalty += 0.5

    # --- Disqualifier 2: Pure research-only career (no production) ---
    if career:
        all_desc = " ".join(role.get("description", "") for role in career).lower()
        research_hits = sum(1 for kw in RESEARCH_KEYWORDS if kw in all_desc)
        production_hits = sum(1 for kw in PRODUCTION_KEYWORDS if kw in all_desc)
        if research_hits > 3 and production_hits == 0:
            penalty += 0.35

    # --- Disqualifier 3: Title mismatch (clearly non-tech role) ---
    title = profile.get("current_title", "").lower()
    if any(t in title for t in IRRELEVANT_TITLES):
        penalty += 0.30

    # --- Disqualifier 4: Very inexperienced (< 2 years) ---
    years = profile.get("years_of_experience", 0)
    if years < 2:
        penalty += 0.25

    # --- Disqualifier 5: Stale profile (inactive > 1 year) ---
    sig = candidate.get("redrob_signals", {})
    last_active_str = sig.get("last_active_date", "")
    if last_active_str:
        try:
            last_active = date.fromisoformat(last_active_str)
            days_since = (TODAY - last_active).days
            if days_since > 365:
                penalty += 0.15
        except (ValueError, TypeError):
            pass

    return min(0.95, penalty)  # never fully zero out a score
