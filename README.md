# Redrob AI — Intelligent Candidate Ranking System

> **Challenge**: India Runs Data & AI Challenge — Candidate Discovery & Ranking  
> **Role Targeted**: Senior AI Engineer, Founding Team @ Redrob AI

---

## What This Does

This system ranks candidates the way a **great recruiter would** — not by keyword-matching, but by understanding what the role actually needs and scoring each candidate across multiple dimensions:

| Signal | Weight | What It Measures |
|---|---|---|
| Core AI/ML Skills Match | 35% | Proficiency + endorsements + duration for JD-relevant skills |
| Experience Fit | 20% | Gaussian peak at 7 yrs, title relevance, industry |
| Career Depth / Production | 15% | Production vs. research language in job descriptions |
| Platform Behavioral Signals | 15% | Response rate, GitHub, verification, interview completion |
| Nice-to-Have Bonuses | 10% | LLM fine-tuning, LTR, HR-tech background, OSS |
| Disqualifier Penalties | -∞ | Pure research-only, no AI skills, very stale profiles |

---

## Architecture

```
JD Analysis → Skills Taxonomy (3 tiers)
                    │
candidates.jsonl → Streaming Reader (line-by-line, no RAM spike)
                    │
              ┌─────┴─────────────────────────────┐
              │  score_skills()    35%             │
              │  score_skill_text() 5%             │
              │  score_experience() 20%            │
              │  score_career_depth() 15%          │
              │  score_behavioral() 15%            │
              │  score_bonuses()   10%             │
              │  disqualifier_penalty() (×penalty) │
              └─────┬─────────────────────────────┘
                    │
              Min-Heap Top-100 (O(n log k))
                    │
              submission.csv
```

**No external API required.** Runs fully locally on CPU. Processes the full ~487MB JSONL in ~60-120 seconds.

---

## Quick Start

```bash
# Install dependencies (minimal — pure stdlib + json)
pip install -r requirements.txt

# Run the ranker (auto-detects candidates.jsonl path)
python ranker.py

# Or specify paths explicitly
python ranker.py --input /path/to/candidates.jsonl --output submission.csv

# Validate the submission
python validate_submission.py submission.csv

# Inspect results in detail
python analyze_results.py submission.csv /path/to/candidates.jsonl
```

---

## Project Structure

```
redrob-ranking/
├── ranker.py              # Main pipeline (run this)
├── score_signals.py       # Individual scoring functions per dimension
├── skills_taxonomy.py     # JD-derived skill tier classification
├── analyze_results.py     # Post-run analysis & spot-check tool
├── requirements.txt       # Dependencies
├── submission.csv         # Generated output (100 ranked candidates)
└── README.md              # This file
```

---

## Scoring Design Philosophy

### Why Not Just Keywords?

Keyword filters miss the right people because:
- A candidate may have listed "Python" as beginner but used it for 60 months with 40 endorsements
- A candidate's job description says "deployed embedding-based retrieval to 10M users" but their skills list doesn't say "FAISS"
- Two candidates both list "Machine Learning" — one trained models in an academic lab, one shipped to production at a major tech company

This system accounts for **all of these signals**:

1. **Multi-dimensional skill scoring**: `proficiency × tier_weight × duration × log(endorsements)`
2. **Text analysis of career descriptions**: production keywords vs. research-only language
3. **Platform behavioral signals**: is this person actually responsive and engaged?
4. **Disqualifier detection**: catches the JD's explicit red flags (pure research, no recent code, no AI skills)

### Why Streaming?

The `candidates.jsonl` is ~487MB. Loading it all into RAM would require 1-2GB. Instead, we use a **min-heap of size 100** — we only ever keep the top-100 candidates in memory, processing the file line-by-line.

Space complexity: O(100) = O(1) effectively  
Time complexity: O(n log 100) ≈ O(n)

---

## Submission Format

```csv
candidate_id,rank,score,reasoning
CAND_XXXXXXX,1,0.9920,"ML Engineer with 6.5 yrs; 8 AI/ML core skills; response rate 0.82; ..."
...
```

100 rows, unique IDs, ranks 1–100, scores non-increasing.
