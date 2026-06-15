"""
analyze_results.py

Post-processing analysis of the ranked candidates.
Prints detailed breakdown, statistics, and spot-check info.
"""

import csv
import json
import sys
from pathlib import Path
from collections import Counter

def load_submission(csv_path: str) -> list[dict]:
    rows = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def analyze(csv_path: str, jsonl_path: str):
    print(f"\nAnalyzing: {csv_path}")
    rows = load_submission(csv_path)
    print(f"Total rows: {len(rows)}")

    # Score distribution
    scores = [float(r["score"]) for r in rows]
    print(f"\nScore range: {min(scores):.4f} – {max(scores):.4f}")
    print(f"Mean score:  {sum(scores)/len(scores):.4f}")

    # Load candidate details for top 20
    top_ids = {r["candidate_id"] for r in rows[:20]}
    top_candidates = {}

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
                cid = c.get("candidate_id", "")
                if cid in top_ids:
                    top_candidates[cid] = c
                    if len(top_candidates) == len(top_ids):
                        break
            except json.JSONDecodeError:
                continue

    print("\n" + "=" * 70)
    print("DETAILED TOP 20 CANDIDATES")
    print("=" * 70)

    for row in rows[:20]:
        cid = row["candidate_id"]
        rank = row["rank"]
        score = row["score"]
        c = top_candidates.get(cid, {})
        if not c:
            print(f"#{rank} {cid} — profile not found in JSONL")
            continue

        profile = c.get("profile", {})
        sig = c.get("redrob_signals", {})
        skills = c.get("skills", [])

        print(f"\n#{rank:>3} | {cid} | Score: {score}")
        print(f"     Name:     {profile.get('anonymized_name', 'N/A')}")
        print(f"     Title:    {profile.get('current_title', 'N/A')} @ {profile.get('current_company', 'N/A')}")
        print(f"     Location: {profile.get('location', 'N/A')}, {profile.get('country', 'N/A')}")
        print(f"     Years:    {profile.get('years_of_experience', 'N/A')}")
        print(f"     Open?:    {sig.get('open_to_work_flag')}")
        print(f"     GitHub:   {sig.get('github_activity_score')}")
        print(f"     Resp.rt:  {sig.get('recruiter_response_rate')}")

        top_skills = sorted(skills, key=lambda s: s.get("endorsements", 0), reverse=True)[:5]
        skill_names = [f"{s['name']} ({s['proficiency']})" for s in top_skills]
        print(f"     Skills:   {', '.join(skill_names)}")
        print(f"     Reason:   {row['reasoning']}")

    # Title distribution in top 100
    print("\n" + "=" * 70)
    print("TITLE DISTRIBUTION (Top 100)")
    print("=" * 70)

    from collections import Counter
    # Load all top 100 for stats
    all_ids = {r["candidate_id"] for r in rows}
    all_candidates = {}

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                c = json.loads(line)
                cid = c.get("candidate_id", "")
                if cid in all_ids:
                    all_candidates[cid] = c
                    if len(all_candidates) == len(all_ids):
                        break
            except json.JSONDecodeError:
                continue

    titles = Counter(
        all_candidates[r["candidate_id"]].get("profile", {}).get("current_title", "N/A")
        for r in rows if r["candidate_id"] in all_candidates
    )
    for title, count in titles.most_common(15):
        print(f"  {count:>3}x  {title}")

    print("\nDone!")


if __name__ == "__main__":
    csv_p = sys.argv[1] if len(sys.argv) > 1 else "submission.csv"
    jsonl_p = (
        sys.argv[2] if len(sys.argv) > 2
        else str(
            Path(__file__).parent.parent / "india_challenge" /
            "[PUB] India_runs_data_and_ai_challenge" /
            "India_runs_data_and_ai_challenge" / "candidates.jsonl"
        )
    )
    analyze(csv_p, jsonl_p)
