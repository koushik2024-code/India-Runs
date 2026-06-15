"""
ranker.py

Main pipeline: reads candidates.jsonl (stream), scores each candidate
using multi-signal hybrid scoring, ranks top 100, writes submission CSV.

Usage:
    python ranker.py --input <path_to_candidates.jsonl> --output submission.csv

Or run directly — it will auto-find the data in the default location.
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

from score_signals import (
    score_skills,
    score_skill_text,
    score_experience,
    score_career_depth,
    score_behavioral,
    score_bonuses,
    compute_disqualifier_penalty,
)

# ---------------------------------------------------------------------------
# Scoring weights (must sum to 1.0 before penalty)
# ---------------------------------------------------------------------------
WEIGHTS = {
    "skills": 0.35,       # Core AI/ML skill match
    "skill_text": 0.05,   # Keyword scan of career descriptions
    "experience": 0.20,   # Experience fit + title + industry
    "career_depth": 0.15, # Production depth of career history
    "behavioral": 0.15,   # Platform engagement signals
    "bonuses": 0.10,      # Nice-to-have bonuses
}

assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-6, "Weights must sum to 1.0"

TOP_N = 100
PRINT_EVERY = 1000  # Progress print interval


def compute_composite_score(candidate: dict) -> tuple[float, dict]:
    """
    Compute weighted composite score for a candidate.
    Returns (final_score, breakdown_dict).
    """
    breakdown = {}

    # --- Raw signal scores ---
    s_skills = score_skills(candidate)
    s_skill_text = score_skill_text(candidate)
    s_experience = score_experience(candidate)
    s_career_depth = score_career_depth(candidate)
    s_behavioral = score_behavioral(candidate)
    s_bonuses = score_bonuses(candidate)

    # --- Weighted sum before penalty ---
    raw_score = (
        s_skills * WEIGHTS["skills"] +
        s_skill_text * WEIGHTS["skill_text"] +
        s_experience * WEIGHTS["experience"] +
        s_career_depth * WEIGHTS["career_depth"] +
        s_behavioral * WEIGHTS["behavioral"] +
        s_bonuses * WEIGHTS["bonuses"]
    )

    # --- Disqualifier penalty (multiplicative) ---
    penalty = compute_disqualifier_penalty(candidate)
    final_score = raw_score * (1.0 - penalty)

    breakdown = {
        "skills": round(s_skills, 4),
        "skill_text": round(s_skill_text, 4),
        "experience": round(s_experience, 4),
        "career_depth": round(s_career_depth, 4),
        "behavioral": round(s_behavioral, 4),
        "bonuses": round(s_bonuses, 4),
        "penalty": round(penalty, 4),
        "raw_score": round(raw_score, 4),
        "final_score": round(final_score, 4),
    }

    return final_score, breakdown


def generate_reasoning(candidate: dict, breakdown: dict) -> str:
    """
    Generate a concise recruiter-readable reasoning snippet.
    Format mirrors sample_submission.csv style.
    """
    profile = candidate.get("profile", {})
    title = profile.get("current_title", "N/A")
    yrs = profile.get("years_of_experience", 0)
    sig = candidate.get("redrob_signals", {})
    response_rate = sig.get("recruiter_response_rate", 0)
    github = sig.get("github_activity_score", -1)

    # Count high-tier skills
    skills = candidate.get("skills", [])
    from skills_taxonomy import TIER1_SKILLS, TIER2_SKILLS, PROFICIENCY_WEIGHTS
    from score_signals import _get_tier
    core_ai_skills = sum(
        1 for s in skills
        if _get_tier(s.get("name", ""))[0] >= 2.0
    )

    open_to_work = "open to work" if sig.get("open_to_work_flag") else "passive"
    github_str = f"; GitHub score {github}" if github >= 0 else ""

    reasoning = (
        f"{title} with {yrs:.1f} yrs; "
        f"{core_ai_skills} AI/ML core skills; "
        f"response rate {response_rate:.2f}; "
        f"skills={breakdown['skills']:.2f}, "
        f"exp={breakdown['experience']:.2f}, "
        f"prod={breakdown['career_depth']:.2f}; "
        f"{open_to_work}"
        f"{github_str}"
    )
    return reasoning


def rank_candidates(
    input_path: str,
    output_path: str,
    verbose: bool = True,
) -> list[dict]:
    """
    Stream-process candidates.jsonl, maintain a top-N heap, write CSV.
    Uses streaming to handle 487MB+ file without loading it all into RAM.
    """
    import heapq

    heap = []  # min-heap of (score, candidate_id, breakdown, candidate)
    total = 0
    skipped = 0

    start_time = time.time()

    if verbose:
        print(f"Processing: {input_path}")
        print(f"Output:     {output_path}")
        print("-" * 60)

    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                candidate = json.loads(line)
            except json.JSONDecodeError:
                skipped += 1
                continue

            total += 1
            cid = candidate.get("candidate_id", "")
            if not cid:
                skipped += 1
                continue

            score, breakdown = compute_composite_score(candidate)

            # Maintain top-N min-heap
            if len(heap) < TOP_N:
                heapq.heappush(heap, (score, cid, breakdown, candidate))
            elif score > heap[0][0]:
                heapq.heapreplace(heap, (score, cid, breakdown, candidate))

            if verbose and total % PRINT_EVERY == 0:
                elapsed = time.time() - start_time
                rate = total / elapsed
                print(f"  Processed {total:,} candidates | {rate:.0f}/sec | "
                      f"Current min-top-{TOP_N} score: {heap[0][0]:.4f}")

    elapsed = time.time() - start_time
    if verbose:
        print(f"\nDone! Processed {total:,} candidates in {elapsed:.1f}s ({skipped} skipped)")
        print(f"Top-{TOP_N} threshold score: {heap[0][0]:.4f}")
        print()

    # Sort heap descending by score
    results = sorted(heap, key=lambda x: (-x[0], x[1]))

    # Assign ranks and scale scores to [0.20, 0.99] for clean output
    # (mirrors the sample_submission.csv score range)
    if results:
        max_score = results[0][0]
        min_score = results[-1][0]
        score_range = max(max_score - min_score, 1e-9)

    output_rows = []
    for rank, (raw_score, cid, breakdown, candidate) in enumerate(results, start=1):
        # Scale to [0.20, 0.99]
        scaled_score = 0.20 + 0.79 * (raw_score - min_score) / score_range
        reasoning = generate_reasoning(candidate, breakdown)
        output_rows.append({
            "candidate_id": cid,
            "rank": rank,
            "score": round(scaled_score, 4),
            "reasoning": reasoning,
        })

    # Write CSV
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["candidate_id", "rank", "score", "reasoning"]
        )
        writer.writeheader()
        writer.writerows(output_rows)

    if verbose:
        print(f"Submission written to: {output_path}")
        print()
        print("=" * 60)
        print("TOP 10 CANDIDATES PREVIEW:")
        print("=" * 60)
        for row in output_rows[:10]:
            print(f"  #{row['rank']:>3}  {row['candidate_id']}  score={row['score']:.4f}")
            print(f"         {row['reasoning']}")
            print()

    return output_rows


def main():
    parser = argparse.ArgumentParser(
        description="Redrob AI Candidate Ranking System"
    )
    parser.add_argument(
        "--input", "-i",
        default=None,
        help="Path to candidates.jsonl (auto-detected if not provided)"
    )
    parser.add_argument(
        "--output", "-o",
        default="submission.csv",
        help="Output CSV path (default: submission.csv)"
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output"
    )
    args = parser.parse_args()

    # Auto-detect input if not provided
    input_path = args.input
    if not input_path:
        # Look in common locations
        candidates = [
            Path(__file__).parent.parent / "india_challenge" /
            "[PUB] India_runs_data_and_ai_challenge" /
            "India_runs_data_and_ai_challenge" / "candidates.jsonl",
            Path("candidates.jsonl"),
        ]
        for p in candidates:
            if p.exists():
                input_path = str(p)
                break

    if not input_path or not Path(input_path).exists():
        print(f"ERROR: Could not find candidates.jsonl. Please specify --input <path>")
        sys.exit(1)

    rank_candidates(
        input_path=input_path,
        output_path=args.output,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
