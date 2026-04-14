import os
import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from math import pi


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


with open(os.path.join(RESULT_PATH, RESULT_NAME), "r", encoding="utf-8") as f:
    evaluate = json.load(f)

print(evaluate)

# Set plotting style
plt.rcParams["figure.figsize"] = [10, 6]
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.3
plt.figure(figsize=(12, 8))

# Extract data for multi_agent_api and multi_agent_review
multi_agent_api_data = evaluate["multi_agent_api"]
multi_agent_review_data = evaluate["multi_agent_review"]

# Prepare metric data (excluding perplexity)
metrics = ["avg_distinct_1", "avg_distinct_2"]
metric_labels = ["Distinct-1", "Distinct-2"]
multi_agent_api_values = [multi_agent_api_data[metric] for metric in metrics]
multi_agent_review_values = [multi_agent_review_data[metric] for metric in metrics]

# Create bar chart
x = np.arange(len(metrics))
width = 0.2

fig, ax = plt.subplots(figsize=(4, 4))
rects1 = ax.bar(
    x - 2 * width / 2,
    multi_agent_api_values,
    2 * width,
    label="Multi-Agent API",
    color="#c1d8e9",
)
rects2 = ax.bar(
    x + 2 * width / 2,
    multi_agent_review_values,
    2 * width,
    label="Multi-Agent Review",
    color="#d4d4d4",
)

# Add labels and title
ax.set_ylabel("Score")
ax.set_title("Distinct Comparison")
ax.set_xticks(x)
ax.set_xticklabels(metric_labels)
ax.legend()


# Add value labels on bars
def autolabel(rects):
    for rect in rects:
        height = rect.get_height()
        ax.annotate(
            f"{height:.4f}",
            xy=(rect.get_x() + rect.get_width() / 2, height - 0.0035),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            va="bottom",
        )


autolabel(rects1)
autolabel(rects2)

plt.tight_layout()
plt.savefig(
    os.path.join(RESULT_PATH, "multi_agent_api_vs_review_quality_metrics.png"), dpi=300
)
plt.close()

# Perplexity comparison chart
perplexity_values = [
    multi_agent_api_data["avg_perplexity"],
    multi_agent_review_data["avg_perplexity"],
]

fig, ax = plt.subplots(figsize=(4, 4))
bars = ax.bar(
    ["Multi-Agent API", "Multi-Agent Review"],
    perplexity_values,
    color=["#c1d8e9", "#d4d4d4"],
    width=width,
)
ax.set_ylabel("Perplexity")
ax.set_title("Perplexity Comparison")
ax.set_ylim(0, 60)  # Set y-axis range for better visualization of differences

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        f"{height:.2f}",
        ha="center",
        va="bottom",
    )

plt.tight_layout()
plt.savefig(
    os.path.join(RESULT_PATH, "multi_agent_api_vs_review_perplexity.png"), dpi=300
)
plt.close()

# Prepare performance metric data
perf_metrics = ["avg_latency_seconds", "avg_estimated_cost_usd"]
perf_labels = ["Average Latency (seconds)", "Average Estimated Cost (USD)"]
multi_agent_api_perf_values = [
    multi_agent_api_data["metrics"][metric] for metric in perf_metrics
]
multi_agent_review_perf_values = [
    multi_agent_review_data["metrics"][metric] for metric in perf_metrics
]

# Create latency comparison chart
fig, ax = plt.subplots(figsize=(4, 4))
bars = ax.bar(
    ["Multi-Agent API", "Multi-Agent Review"],
    [multi_agent_api_perf_values[0], multi_agent_review_perf_values[0]],
    color=["#c1d8e9", "#d4d4d4"],
    width=width,
)
ax.set_ylabel("Seconds")
ax.set_title("Average Latency Comparison")

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        f"{height:.2f}",
        ha="center",
        va="bottom",
    )

plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, "multi_agent_api_vs_review_latency.png"), dpi=300)
plt.close()

# Create cost comparison chart
fig, ax = plt.subplots(figsize=(4, 4))
bars = ax.bar(
    ["Multi-Agent API", "Multi-Agent Review"],
    [multi_agent_api_perf_values[1], multi_agent_review_perf_values[1]],
    color=["#c1d8e9", "#d4d4d4"],
    width=width,
)
ax.set_ylabel("USD")
ax.set_title("Average Estimated Cost Comparison")

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        f"{height:.4f}",
        ha="center",
        va="bottom",
    )

plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, "multi_agent_api_vs_review_cost.png"), dpi=300)
plt.close()

# BERTScore comparison
bertscore_values = [
    multi_agent_api_data["avg_bertscore"],
    multi_agent_review_data["avg_bertscore"],
]

fig, ax = plt.subplots(figsize=(4, 4))
bars = ax.bar(
    ["Multi-Agent API", "Multi-Agent Review"],
    bertscore_values,
    color=["#c1d8e9", "#d4d4d4"],
    width=width,
)
ax.set_ylabel("BERTScore F1")
ax.set_title("BERTScore Comparison")
ax.set_ylim(0, 1)  # Set y-axis range for better visualization of differences

# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        f"{height:.4f}",
        ha="center",
        va="bottom",
    )

plt.tight_layout()
plt.savefig(
    os.path.join(RESULT_PATH, "multi_agent_api_vs_review_bertscore.png"), dpi=300
)
plt.close()

# ROUGE-L comparison
rouge_l_values = [
    multi_agent_api_data["avg_rouge_l"],
    multi_agent_review_data["avg_rouge_l"],
]

fig, ax = plt.subplots(figsize=(4, 4))
bars = ax.bar(
    ["Multi-Agent API", "Multi-Agent Review"],
    rouge_l_values,
    color=["#c1d8e9", "#d4d4d4"],
    width=width,
)
ax.set_ylabel("ROUGE-L F1")
ax.set_title("ROUGE-L Comparison")
ax.set_ylim(0, 0.5)  # Set y-axis range for better visualization of differences


# Add value labels
for bar in bars:
    height = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        f"{height:.4f}",
        ha="center",
        va="bottom",
    )

plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, "multi_agent_api_vs_review_rouge_l.png"), dpi=300)
plt.close()

# Prepare radar chart data
categories = [
    "Distinct-1",
    "Distinct-2",
    "ROUGE-L",
    "BERTScore",
    "Perplexity",
    "Latency",
    "Cost",
]
N = len(categories)

# Extract data
multi_agent_api_values = [
    multi_agent_api_data["avg_distinct_1"],
    multi_agent_api_data["avg_distinct_2"],
    multi_agent_api_data["avg_rouge_l"],
    multi_agent_api_data["avg_bertscore"],
    # Normalize perplexity, smaller values are better
    (multi_agent_api_data["avg_perplexity"] / 60),
    # Normalize latency, smaller values are better
    (multi_agent_api_data["metrics"]["avg_latency_seconds"] / 60),
    # Normalize cost, smaller values are better
    (multi_agent_api_data["metrics"]["avg_estimated_cost_usd"] / 0.01),
]

multi_agent_review_values = [
    multi_agent_review_data["avg_distinct_1"],
    multi_agent_review_data["avg_distinct_2"],
    multi_agent_review_data["avg_rouge_l"],
    multi_agent_review_data["avg_bertscore"],
    # Normalize perplexity, smaller values are better
    (multi_agent_review_data["avg_perplexity"] / 60),
    # Normalize latency, smaller values are better
    (multi_agent_review_data["metrics"]["avg_latency_seconds"] / 60),
    # Normalize cost, smaller values are better
    (multi_agent_review_data["metrics"]["avg_estimated_cost_usd"] / 0.01),
]

# Calculate angles
angles = [n / float(N) * 2 * pi for n in range(N)]
angles += angles[:1]  # Close the polygon

# Close the data
multi_agent_api_values += multi_agent_api_values[:1]
multi_agent_review_values += multi_agent_review_values[:1]

# Create radar chart
fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

# Plot Multi-Agent API
ax.plot(
    angles,
    multi_agent_api_values,
    "o-",
    linewidth=2,
    label="Multi-Agent API",
    color="#c1d8e9",
)
ax.fill(angles, multi_agent_api_values, alpha=0.25, color="#c1d8e9")

# Plot Multi-Agent Review
ax.plot(
    angles,
    multi_agent_review_values,
    "o-",
    linewidth=2,
    label="Multi-Agent Review",
    color="#d4d4d4",
)
ax.fill(angles, multi_agent_review_values, alpha=0.25, color="#d4d4d4")

# Add labels
ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories)
ax.set_ylim(0, 1)

# Add title and legend
ax.set_title(
    "Comparison between Multi-Agent API and Multi-Agent Review", size=15, y=1.08
)
ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.0))

plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, "multi_agent_api_vs_review_radar.png"), dpi=300)
plt.close()
