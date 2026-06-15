"""
skills_taxonomy.py

Defines three tiers of skills mapped from the Redrob Senior AI Engineer JD.
Also includes keyword lists for scanning career history text.
"""

# ---------------------------------------------------------------------------
# TIER 1 — Hard requirements from JD (must-have)
# Weight multiplier: 3.0
# ---------------------------------------------------------------------------
TIER1_SKILLS = {
    # Embeddings & semantic retrieval
    "sentence-transformers", "sentence transformers", "bert embeddings",
    "bge", "e5", "openai embeddings", "text embeddings", "dense retrieval",
    "semantic search", "bi-encoder", "cross-encoder", "colbert",
    "embedding models", "semantic similarity",

    # Vector databases / hybrid search
    "milvus", "faiss", "pinecone", "weaviate", "qdrant", "opensearch",
    "elasticsearch", "chroma", "pgvector", "annoy", "hnsw",
    "vector database", "vector search", "vector store",
    "hybrid search", "bm25", "sparse retrieval", "dense-sparse hybrid",

    # Ranking & retrieval evaluation
    "ndcg", "mrr", "map@k", "recall@k", "precision@k",
    "ranking evaluation", "information retrieval", "learning to rank",
    "ltr", "lambdarank", "listwise", "pairwise ranking",
    "a/b testing", "ab testing", "online evaluation",
    "offline evaluation", "retrieval evaluation",

    # Core ML/AI production
    "mlops", "model serving", "model deployment",
    "feature store", "ml pipeline", "production ml",
    "model monitoring", "embedding drift",

    # Python production code
    "python", "pyspark", "fastapi", "flask",
}

TIER1_WEIGHT = 3.0

# ---------------------------------------------------------------------------
# TIER 2 — Nice-to-have from JD (good signals)
# Weight multiplier: 2.0
# ---------------------------------------------------------------------------
TIER2_SKILLS = {
    # LLM fine-tuning
    "lora", "qlora", "peft", "fine-tuning llms", "llm fine-tuning",
    "instruction tuning", "rlhf", "dpo", "sft", "adapter tuning",
    "parameter efficient", "fine-tune", "fine tuning",

    # LLM usage (orchestration)
    "langchain", "llamaindex", "llm", "gpt", "claude", "gemini",
    "hugging face", "huggingface", "transformers library",
    "prompt engineering", "rag", "retrieval augmented generation",

    # ML frameworks
    "pytorch", "tensorflow", "jax", "xgboost", "lightgbm", "catboost",
    "sklearn", "scikit-learn", "neural network", "deep learning",
    "gradient boosting",

    # MLOps tools
    "weights & biases", "wandb", "mlflow", "dvc", "bentoml", "ray",
    "kubeflow", "airflow", "prefect", "dagster",

    # Distributed / scale
    "spark", "kafka", "flink", "distributed training", "kubernetes",
    "docker", "ray distributed", "dask", "data engineering",

    # NLP
    "nlp", "natural language processing", "text classification",
    "named entity recognition", "ner", "sentiment analysis",
    "text generation", "summarization", "question answering",
    "tts", "speech recognition", "asr",

    # Cloud ML
    "sagemaker", "vertex ai", "azure ml", "gcp ml", "aws",
    "gcp", "azure",
}

TIER2_WEIGHT = 2.0

# ---------------------------------------------------------------------------
# TIER 3 — General engineering skills (breadth, low signal)
# Weight multiplier: 0.5
# ---------------------------------------------------------------------------
TIER3_SKILLS = {
    "sql", "pandas", "numpy", "matplotlib", "seaborn",
    "git", "github", "linux", "bash", "shell",
    "rest api", "graphql", "grpc", "microservices",
    "react", "javascript", "typescript", "node.js",
    "mongodb", "postgresql", "mysql", "redis",
    "data analysis", "data visualization", "statistics",
    "excel", "powerpoint", "tableau", "power bi",
    "project management", "agile", "scrum",
    "image classification", "object detection", "computer vision",
    "gans", "generative ai",
    "six sigma", "sap", "accounting", "marketing",
}

TIER3_WEIGHT = 0.5

# ---------------------------------------------------------------------------
# Proficiency multipliers
# ---------------------------------------------------------------------------
PROFICIENCY_WEIGHTS = {
    "expert": 1.0,
    "advanced": 0.85,
    "intermediate": 0.65,
    "beginner": 0.35,
}

# ---------------------------------------------------------------------------
# Career history text: PRODUCTION signals (positive)
# ---------------------------------------------------------------------------
PRODUCTION_KEYWORDS = [
    "production", "deployed", "deployment", "real users", "at scale",
    "serving", "inference", "api endpoint", "latency", "throughput",
    "a/b test", "online", "live system", "rollout", "monitoring",
    "retrieval system", "ranking system", "recommendation system",
    "search infrastructure", "embedding pipeline", "vector index",
    "feature pipeline", "model serving", "ml platform",
    "millions of", "billion", "petabyte", "terabyte",
    "reduced latency", "improved recall", "ndcg", "mrr",
    "index refresh", "embedding drift", "retrieval quality",
]

# ---------------------------------------------------------------------------
# Career history text: RESEARCH-ONLY signals (negative — disqualifier)
# ---------------------------------------------------------------------------
RESEARCH_KEYWORDS = [
    "academic", "research paper", "arxiv", "publication", "journal",
    "thesis", "dissertation", "phd candidate", "research lab",
    "research scientist", "postdoc", "postdoctoral",
    "university lab", "academic project", "literature review",
    "benchmark dataset", "citation",
]

# ---------------------------------------------------------------------------
# Title relevance scoring
# ---------------------------------------------------------------------------
HIGHLY_RELEVANT_TITLES = {
    "ai engineer", "ml engineer", "machine learning engineer",
    "senior ai engineer", "senior ml engineer",
    "nlp engineer", "search engineer", "ranking engineer",
    "recommendation engineer", "data scientist",
    "applied scientist", "applied ml", "applied ai",
    "research engineer",  # OK if has production signals
    "senior data scientist", "lead ml engineer",
    "principal ml engineer", "staff ml engineer",
    "founding engineer", "software engineer ml",
}

RELEVANT_TITLES = {
    "backend engineer", "software engineer", "data engineer",
    "analytics engineer", "platform engineer", "infrastructure engineer",
    "full stack engineer", "senior software engineer",
    "technical lead", "tech lead", "senior engineer",
}

IRRELEVANT_TITLES = {
    "accountant", "hr manager", "marketing manager", "content writer",
    "graphic designer", "customer support", "sales executive",
    "operations manager", "project manager", "mechanical engineer",
    "civil engineer", "business analyst",
}

# ---------------------------------------------------------------------------
# HR-tech / marketplace experience bonus (in career description)
# ---------------------------------------------------------------------------
HRTECH_KEYWORDS = [
    "hr tech", "hrtech", "recruiting", "recruitment", "talent",
    "candidate matching", "job matching", "marketplace platform",
    "talent intelligence", "applicant tracking", "ats",
    "sourcing", "hiring platform",
]

# ---------------------------------------------------------------------------
# Open source contribution signals
# ---------------------------------------------------------------------------
OPENSOURCE_KEYWORDS = [
    "open source", "opensource", "github contribution", "pull request",
    "open-source", "contributed to", "maintainer", "apache", "hugging face",
    "open source project",
]

# ---------------------------------------------------------------------------
# Company size scoring (proxy for scale of experience)
# ---------------------------------------------------------------------------
COMPANY_SIZE_SCORES = {
    "1-10": 0.2,
    "11-50": 0.3,
    "51-200": 0.5,
    "201-500": 0.65,
    "501-1000": 0.75,
    "1001-5000": 0.85,
    "5001-10000": 0.9,
    "10001+": 1.0,
}
