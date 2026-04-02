"""
Podcast Transcript Generator
=============================
Loads the fine-tuned QLoRA podcast-expert adapter and generates
multi-turn host/expert transcripts for new topics.

Usage (local, requires GPU or slow CPU):
    python experiments/generate_transcript.py

Usage (Colab - paste as a new cell after Cell 4):
    Replace ADAPTER_PATH with "./podcast-expert-lora" or "./output/checkpoint-35"

Output:
    experiments/generated_transcripts.json
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ADAPTER_PATH = Path(__file__).parent / "podcast-expert-lora"
OUTPUT_PATH  = Path(__file__).parent / "generated_transcripts.json"
MAX_NEW_TOKENS = 150
TEMPERATURE    = 0.7
TOP_P          = 0.9

# Topics to generate (none of these were in the original 10-sample dataset)
EPISODES = [
    {
        "topic": "quantum_computing",
        "host_questions": [
            "Quantum computing is getting a lot of attention. Where do you think we actually are right now?",
            "So it is still early days. What would need to happen for quantum to become practically useful?",
            "That is reassuring. What is the most realistic near-term application?",
        ],
    },
    {
        "topic": "open_source_ai",
        "host_questions": [
            "Open-source AI models have been growing fast. Is that a good thing for society?",
            "But there are safety concerns around open weights. How do you think about that tradeoff?",
            "So transparency and risk exist together. Where does responsibility land?",
        ],
    },
    {
        "topic": "digital_wellbeing",
        "host_questions": [
            "Screen time is at an all-time high. What does the research actually say about its effects?",
            "That is more nuanced than most headlines suggest. What habits genuinely help?",
            "Last question: is the goal to use technology less, or to use it differently?",
        ],
    },
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_adapter(path: Path) -> None:
    """Verify the adapter folder has the essential files."""
    required = {"adapter_config.json"}
    weights  = {"adapter_model.safetensors", "adapter_model.bin"}

    missing = required - {f.name for f in path.iterdir()}
    if missing:
        sys.exit(f"[ERROR] Adapter folder is missing: {missing}\n"
                 f"  → Make sure you extracted the full podcast-expert-lora.zip into {path}")

    has_weights = any((path / w).exists() for w in weights)
    if not has_weights:
        sys.exit(
            "[ERROR] No adapter weights found (adapter_model.safetensors or .bin).\n"
            "  → In Colab, re-run the save cell:\n"
            "       model.save_pretrained('podcast-expert-lora')\n"
            "       !zip -r podcast-expert-lora.zip podcast-expert-lora/\n"
            "  → Then re-download and extract the zip here."
        )
    print(f"[OK] Adapter found at {path}")


def load_model(adapter_path: Path):
    """Load base model + LoRA adapter. Falls back to CPU if no GPU."""
    try:
        # Try unsloth first (faster, same interface as training)
        from unsloth import FastLanguageModel
        import torch

        use_gpu = torch.cuda.is_available()
        print(f"[INFO] Loading via unsloth (GPU={'yes' if use_gpu else 'no, using CPU — this will be slow'})")

        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name=str(adapter_path),
            max_seq_length=2048,
            load_in_4bit=use_gpu,   # 4-bit only works on GPU
            dtype=None,
        )
        FastLanguageModel.for_inference(model)
        device = "cuda" if use_gpu else "cpu"
        return model, tokenizer, device

    except ImportError:
        # Fallback: standard transformers + peft (slower but no unsloth needed)
        print("[INFO] unsloth not found, falling back to transformers + peft")
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel

        base_model_id = "unsloth/Llama-3.2-1B-Instruct"
        device = "cuda" if torch.cuda.is_available() else "cpu"

        tokenizer = AutoTokenizer.from_pretrained(str(adapter_path))
        base = AutoModelForCausalLM.from_pretrained(
            base_model_id,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto" if device == "cuda" else None,
        )
        model = PeftModel.from_pretrained(base, str(adapter_path))
        model = model.to(device)
        model.eval()
        return model, tokenizer, device


def generate_response(model, tokenizer, device: str, topic: str, question: str) -> str:
    """Generate a single expert response."""
    messages = [
        {
            "role": "system",
            "content": (
                f"You are an insightful podcast guest. The topic is {topic}. "
                "Give concise, thoughtful answers to the host's questions."
            ),
        },
        {"role": "user", "content": question},
    ]

    prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    input_ids = inputs["input_ids"]

    import torch
    with torch.no_grad():
        outputs = model.generate(
            input_ids,
            max_new_tokens=MAX_NEW_TOKENS,
            temperature=TEMPERATURE,
            top_p=TOP_P,
            do_sample=True,
        )

    return tokenizer.decode(
        outputs[0][input_ids.shape[-1]:], skip_special_tokens=True
    ).strip()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Podcast Transcript Generator — Fine-tuned QLoRA Model")
    print("=" * 60)

    check_adapter(ADAPTER_PATH)
    model, tokenizer, device = load_model(ADAPTER_PATH)

    results = []
    for episode in EPISODES:
        topic = episode["topic"]
        questions = episode["host_questions"]

        print(f"\n[Episode] topic={topic}")
        turns = []

        for q in questions:
            print(f"  Host: {q}")
            answer = generate_response(model, tokenizer, device, topic, q)
            print(f"  Expert: {answer}\n")

            turns.append({"speaker": "host",   "text": q})
            turns.append({"speaker": "expert",  "text": answer})

        results.append({
            "generated_at": datetime.utcnow().isoformat(),
            "model": str(ADAPTER_PATH),
            "topic": topic,
            "turns": turns,
        })

    OUTPUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"\n[Done] Saved {len(results)} transcripts → {OUTPUT_PATH}")
    print("Each transcript has", sum(len(e["turns"]) for e in results), "turns total.")


if __name__ == "__main__":
    main()
