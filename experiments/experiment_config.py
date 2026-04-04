"""
Shared configuration for experiment scripts.

Environment variables required:
    OPENAI_COMPATIBLE_BASE_URL (or OPENAI_COMPATIBLE_BASE_URL_LLM)
    OPENAI_COMPATIBLE_API_KEY  (or OPENAI_COMPATIBLE_API_KEY_LLM)
    EXPERIMENT_LLM_MODEL       (default: glm-5-turbo)
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
EXPERIMENT_DIR = Path(__file__).parent
EVALUATION_DIR = EXPERIMENT_DIR / "evaluation"
DATA_DIR = EVALUATION_DIR / "data"
TOPICS_DIR = DATA_DIR / "topics"
REFERENCE_DIR = DATA_DIR / "reference"
BASELINE_API_DIR = DATA_DIR / "baseline_api"
MULTI_AGENT_API_DIR = DATA_DIR / "multi_agent_api"
MULTI_AGENT_REVIEW_DIR = DATA_DIR / "multi_agent_review"
BASELINE_FT_DIR = DATA_DIR / "baseline_ft"
BASELINE_BASE_DIR = DATA_DIR / "baseline_base"
OUTPUTS_DIR = EVALUATION_DIR / "outputs"

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
LLM_BASE_URL = os.environ.get(
    "OPENAI_COMPATIBLE_BASE_URL_LLM",
    os.environ.get("OPENAI_COMPATIBLE_BASE_URL", ""),
)
LLM_API_KEY = os.environ.get(
    "OPENAI_COMPATIBLE_API_KEY_LLM",
    os.environ.get("OPENAI_COMPATIBLE_API_KEY", "not-required"),
)
LLM_MODEL = os.environ.get("EXPERIMENT_LLM_MODEL", "glm-5-turbo")

# Cost per 1K tokens (USD) — adjust for your provider
INPUT_COST_PER_1K = float(os.environ.get("LLM_INPUT_COST_PER_1K", "0.0007"))
OUTPUT_COST_PER_1K = float(os.environ.get("LLM_OUTPUT_COST_PER_1K", "0.0007"))

# ---------------------------------------------------------------------------
# 9 test topics  (3 domains × 3 topics)
# ---------------------------------------------------------------------------
TOPICS = [
    # ---- Technology ----
    {
        "topic_id": "tech_1_transformer_attention",
        "topic": "Transformer Attention Mechanism",
        "domain": "technology",
        "keywords": [
            "self-attention",
            "multi-head attention",
            "positional encoding",
            "query key value",
            "scaled dot-product",
        ],
        "source_hint": (
            "Cover the self-attention mechanism: queries, keys, values, "
            "scaled dot-product attention, multi-head attention, "
            "and positional encoding. Reference the 'Attention Is All You Need' paper."
        ),
    },
    {
        "topic_id": "tech_2_qlora_finetuning",
        "topic": "QLoRA Efficient Fine-tuning",
        "domain": "technology",
        "keywords": [
            "QLoRA",
            "LoRA",
            "4-bit quantization",
            "NF4",
            "double quantization",
            "paged optimizers",
        ],
        "source_hint": (
            "Explain QLoRA: Normal Float 4-bit (NF4) quantization, "
            "double quantization, paged optimizers, and how LoRA adapters "
            "enable fine-tuning large models on consumer GPUs."
        ),
    },
    {
        "topic_id": "tech_3_multi_agent",
        "topic": "LLM Multi-Agent Architecture",
        "domain": "technology",
        "keywords": [
            "multi-agent",
            "orchestration",
            "tool use",
            "planning",
            "reflection",
            "debate",
        ],
        "source_hint": (
            "Cover LLM multi-agent architecture patterns: single-agent with tools, "
            "supervisor pattern, hierarchical agents, debate/reflection, "
            "and challenges like coordination overhead and error propagation."
        ),
    },
    # ---- Humanities ----
    {
        "topic_id": "hum_1_ai_bias_fairness",
        "topic": "AI Bias and Fairness",
        "domain": "humanities",
        "keywords": [
            "algorithmic bias",
            "fairness metrics",
            "disparate impact",
            "representation bias",
            "mitigation strategies",
        ],
        "source_hint": (
            "Discuss types of AI bias (historical, representation, measurement), "
            "fairness metrics (demographic parity, equalized odds), "
            "mitigation strategies, and real-world case studies (hiring, criminal justice)."
        ),
    },
    {
        "topic_id": "hum_2_ai_privacy",
        "topic": "AI Privacy and Data Protection",
        "domain": "humanities",
        "keywords": [
            "GDPR",
            "differential privacy",
            "data leakage",
            "memorization",
            "federated learning",
        ],
        "source_hint": (
            "Cover AI privacy concerns: GDPR implications, differential privacy, "
            "training data memorization and extraction attacks, "
            "federated learning as a privacy-preserving approach."
        ),
    },
    {
        "topic_id": "hum_3_ai_safety_alignment",
        "topic": "AI Safety and Alignment",
        "domain": "humanities",
        "keywords": [
            "RLHF",
            "Constitutional AI",
            "red-teaming",
            "guardrails",
            "jailbreak",
            "alignment",
        ],
        "source_hint": (
            "Explain AI safety and alignment: RLHF, Constitutional AI, "
            "red-teaming methodologies, guardrails implementation, "
            "jailbreak attacks and defenses."
        ),
    },
    # ---- Medicine ----
    {
        "topic_id": "med_1_ai_medical_imaging",
        "topic": "AI-Assisted Medical Imaging",
        "domain": "medicine",
        "keywords": [
            "sensitivity",
            "specificity",
            "chest radiograph",
            "CNN",
            "ViT",
            "FDA approval",
        ],
        "source_hint": (
            "Cover AI in medical imaging: CNN/ViT for chest X-ray analysis, "
            "sensitivity and specificity metrics, underdiagnosis risks, "
            "AI bias in medical data, and FDA approval pathways."
        ),
    },
    {
        "topic_id": "med_2_clinical_trials",
        "topic": "Clinical Trial Design",
        "domain": "medicine",
        "keywords": [
            "RCT",
            "endpoints",
            "statistical power",
            "placebo",
            "blinding",
            "adaptive design",
        ],
        "source_hint": (
            "Explain clinical trial design: RCT principles, primary/secondary endpoints, "
            "statistical power, placebo controls, blinding strategies, "
            "and how AI can assist in adaptive trial design."
        ),
    },
    {
        "topic_id": "med_3_ai_drug_discovery",
        "topic": "AI in Drug Discovery",
        "domain": "medicine",
        "keywords": [
            "molecular docking",
            "virtual screening",
            "ADMET",
            "generative chemistry",
            "hit-to-lead",
        ],
        "source_hint": (
            "Cover AI in drug discovery: traditional drug pipeline stages, "
            "molecular docking, virtual screening, ADMET prediction, "
            "generative chemistry, and recent success stories."
        ),
    },
]
