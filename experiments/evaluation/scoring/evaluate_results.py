import os
import json
from bert_score import score as bert_score
from rouge import Rouge
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import torch
import warnings

rouge = Rouge()
gpt2_model = GPT2LMHeadModel.from_pretrained("gpt2")
gpt2_tokenizer = GPT2Tokenizer.from_pretrained("gpt2")
gpt2_model.eval()
warnings.filterwarnings("ignore", message=".*weights.*not.*initialized.*")
warnings.filterwarnings("ignore", message=".*weights of.*not used.*")


RESULT_PATH = "./experiments/evaluation/data"
MODEL_NAME = [
    "baseline_api",
    "multi_agent_api",
    "multi_agent_review",
    # "Llama_base",
    # "Llama_ft",
    "Llama_baseline_base",
    "Llama_baseline_ft",
]
REFERENCE = "reference"
TOPIC_NAME = [
    "hum_1_ai_bias_fairness",
    "hum_2_ai_privacy",
    "hum_3_ai_safety_alignment",
    "med_1_ai_medical_imaging",
    "med_2_clinical_trials",
    "med_3_ai_drug_discovery",
    "tech_1_transformer_attention",
    "tech_2_qlora_finetuning",
    "tech_3_multi_agent",
]
RESULT_NAME = "evaluate.json"

data = {}

for model in [*MODEL_NAME, REFERENCE]:
    data[model] = {}
    for topic in TOPIC_NAME:
        file_path = os.path.join(RESULT_PATH, model, f"{topic}.json")
        with open(file_path, "r", encoding="utf-8") as f:
            data[model][topic] = json.load(f)

evaluate = {}
for model in MODEL_NAME:
    evaluate[model] = {"metrics": {}, "topics": {}}
    evaluate[model]["metrics"]["avg_latency_seconds"] = sum(
        data[model][topic]["metrics"]["latency_seconds"] for topic in TOPIC_NAME
    ) / len(TOPIC_NAME)
    evaluate[model]["metrics"]["avg_estimated_cost_usd"] = sum(
        data[model][topic]["metrics"]["estimated_cost_usd"] for topic in TOPIC_NAME
    ) / len(TOPIC_NAME)

    distinct_1_s = []
    distinct_2_s = []
    rouge_l_s = []
    perplexity_s = []
    bertscore_s = []
    texts_models = []
    texts_refs = []

    for topic in TOPIC_NAME:
        evaluate[model]["topics"][topic] = {}

        texts = "\n".join([turn["text"] for turn in data[model][topic]["turns"]])
        tokens = list(texts.replace(" ", "").replace("\n", ""))

        # Distinct-1
        if ngrams_1 := [tuple(tokens[i : i + 1]) for i in range(len(tokens))]:
            distinct_1_s.append(len(set(ngrams_1)) / len(ngrams_1))
        else:
            distinct_1_s.append(0.0)

        # Distinct-2
        if ngrams_2 := [tuple(tokens[i : i + 2]) for i in range(len(tokens) - 1)]:
            distinct_2_s.append(len(set(ngrams_2)) / len(ngrams_2))
        else:
            distinct_2_s.append(0.0)

        # Perplexity
        inputs = gpt2_tokenizer(
            texts, return_tensors="pt", truncation=True, max_length=512
        )
        with torch.no_grad():
            outputs = gpt2_model(**inputs, labels=inputs["input_ids"])
        perplexity_s.append(torch.exp(outputs.loss).item())

        # 计算模型与reference的ROUGE-L（单向比较）
        texts_model = "\n".join([turn["text"] for turn in data[model][topic]["turns"]])
        texts_ref = "\n".join(
            [turn["text"] for turn in data[REFERENCE][topic]["turns"]]
        )
        try:
            rouge_scores = rouge.get_scores(texts_model, texts_ref)
            rouge_l_score = rouge_scores[0]["rouge-l"]["f"]
            rouge_l_s.append(rouge_l_score)
            evaluate[model]["topics"][topic]["rouge_l"] = rouge_l_score
        except Exception:
            rouge_l_s.append(0.0)
            evaluate[model]["topics"][topic]["rouge_l"] = 0.0

        # 计算模型与reference的BERTScore（单向比较）
        texts_models.append(texts_model)
        texts_refs.append(texts_ref)
    _, _, f1 = bert_score(texts_models, texts_refs, lang="en", verbose=False)

    evaluate[model]["avg_distinct_1"] = sum(distinct_1_s) / len(distinct_1_s)
    evaluate[model]["avg_distinct_2"] = sum(distinct_2_s) / len(distinct_2_s)
    evaluate[model]["avg_rouge_l"] = sum(rouge_l_s) / len(rouge_l_s)
    evaluate[model]["avg_perplexity"] = sum(perplexity_s) / len(perplexity_s)
    evaluate[model]["avg_bertscore"] = float(sum(f1) / len(f1))


print(evaluate)

with open(os.path.join(RESULT_PATH, RESULT_NAME), "w+", encoding="utf-8") as f:
    json.dump(evaluate, f, ensure_ascii=False, separators=(",", ":"), indent=0)
