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

# Set plot style
plt.rcParams["figure.figsize"] = [10, 6]
plt.rcParams["axes.grid"] = True
plt.rcParams["grid.alpha"] = 0.3
plt.figure(figsize=(12, 8))

# Extract data for baseline_api and multi_agent_api
baseline_data = evaluate["baseline_api"]
multi_agent_data = evaluate["multi_agent_api"]

# Prepare metric data (excluding perplexity)
metrics = ["avg_distinct_1", "avg_distinct_2"]
metric_labels = ["Distinct-1", "Distinct-2"]
baseline_values = [baseline_data[metric] for metric in metrics]
multi_agent_values = [multi_agent_data[metric] for metric in metrics]

# Create bar chart
x = np.arange(len(metrics))
width = 0.2

fig, ax = plt.subplots(figsize=(4, 4))
rects1 = ax.bar(
    x - 2 * width / 2, baseline_values, 2 * width, label="Baseline API", color="#92b1d9"
)
rects2 = ax.bar(
    x + 2 * width / 2,
    multi_agent_values,
    2 * width,
    label="Multi-Agent API",
    color="#f6c8b6",
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
    os.path.join(RESULT_PATH, "baseline_vs_multiagent_quality_metrics.png"), dpi=300
)
plt.close()

# Perplexity comparison chart
perplexity_values = [
    baseline_data["avg_perplexity"],
    multi_agent_data["avg_perplexity"],
]

fig, ax = plt.subplots(figsize=(4, 4))
bars = ax.bar(
    ["Baseline API", "Multi-Agent API"],
    perplexity_values,
    color=["#92b1d9", "#f6c8b6"],
    width=width,
)
ax.set_ylabel("Perplexity")
ax.set_title("Perplexity Comparison")
ax.set_ylim(0, 60)  # Set y-axis range for better display of differences

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
plt.savefig(os.path.join(RESULT_PATH, "baseline_vs_multiagent_perplexity.png"), dpi=300)
plt.close()

# Prepare performance metrics data
perf_metrics = ["avg_latency_seconds", "avg_estimated_cost_usd"]
perf_labels = ["Average Latency (seconds)", "Average Estimated Cost (USD)"]
baseline_perf_values = [baseline_data["metrics"][metric] for metric in perf_metrics]
multi_agent_perf_values = [
    multi_agent_data["metrics"][metric] for metric in perf_metrics
]

# Create latency comparison chart
fig, ax = plt.subplots(figsize=(4, 4))
bars = ax.bar(
    ["Baseline API", "Multi-Agent API"],
    [baseline_perf_values[0], multi_agent_perf_values[0]],
    color=["#92b1d9", "#f6c8b6"],
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
plt.savefig(os.path.join(RESULT_PATH, "baseline_vs_multiagent_latency.png"), dpi=300)
plt.close()

# Create cost comparison chart
fig, ax = plt.subplots(figsize=(4, 4))
bars = ax.bar(
    ["Baseline API", "Multi-Agent API"],
    [baseline_perf_values[1], multi_agent_perf_values[1]],
    color=["#92b1d9", "#f6c8b6"],
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
plt.savefig(os.path.join(RESULT_PATH, "baseline_vs_multiagent_cost.png"), dpi=300)
plt.close()

# BERTScore comparison
bertscore_values = [
    baseline_data["avg_bertscore"],
    multi_agent_data["avg_bertscore"],
]

fig, ax = plt.subplots(figsize=(4, 4))
bars = ax.bar(
    ["Baseline API", "Multi-Agent API"],
    bertscore_values,
    color=["#92b1d9", "#f6c8b6"],
    width=width,
)
ax.set_ylabel("BERTScore F1")
ax.set_title("BERTScore Comparison")
ax.set_ylim(0, 1)  # Set y-axis range for better display of differences

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
plt.savefig(os.path.join(RESULT_PATH, "baseline_vs_multiagent_bertscore.png"), dpi=300)
plt.close()

# ROUGE-L comparison
rouge_l_values = [
    baseline_data["avg_rouge_l"],
    multi_agent_data["avg_rouge_l"],
]

fig, ax = plt.subplots(figsize=(4, 4))
bars = ax.bar(
    ["Baseline API", "Multi-Agent API"],
    rouge_l_values,
    color=["#92b1d9", "#f6c8b6"],
    width=width,
)
ax.set_ylabel("ROUGE-L F1")
ax.set_title("ROUGE-L Comparison")
ax.set_ylim(0, 0.5)  # Set y-axis range for better display of differences


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
plt.savefig(os.path.join(RESULT_PATH, "baseline_vs_multiagent_rouge_l.png"), dpi=300)
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
baseline_values = [
    baseline_data["avg_distinct_1"],
    baseline_data["avg_distinct_2"],
    baseline_data["avg_rouge_l"],
    baseline_data["avg_bertscore"],
    # Normalize Perplexity, smaller is better
    (baseline_data["avg_perplexity"] / 60),
    # Normalize Latency, smaller is better
    (baseline_data["metrics"]["avg_latency_seconds"] / 60),
    # Normalize Cost, smaller is better
    (baseline_data["metrics"]["avg_estimated_cost_usd"] / 0.01),
]

multi_agent_values = [
    multi_agent_data["avg_distinct_1"],
    multi_agent_data["avg_distinct_2"],
    multi_agent_data["avg_rouge_l"],
    multi_agent_data["avg_bertscore"],
    # Normalize Perplexity, smaller is better
    (multi_agent_data["avg_perplexity"] / 60),
    # Normalize Latency, smaller is better
    (multi_agent_data["metrics"]["avg_latency_seconds"] / 60),
    # Normalize Cost, smaller is better
    (multi_agent_data["metrics"]["avg_estimated_cost_usd"] / 0.01),
]

# Calculate angles
angles = [n / float(N) * 2 * pi for n in range(N)]
angles += angles[:1]  # Close the polygon

# Close the data
baseline_values += baseline_values[:1]
multi_agent_values += multi_agent_values[:1]

# Create radar chart
fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

# Plot Baseline API
ax.plot(
    angles, baseline_values, "o-", linewidth=2, label="Baseline API", color="#92b1d9"
)
ax.fill(angles, baseline_values, alpha=0.25, color="#92b1d9")

# Plot Multi-Agent API
ax.plot(
    angles,
    multi_agent_values,
    "o-",
    linewidth=2,
    label="Multi-Agent API",
    color="#f6c8b6",
)
ax.fill(angles, multi_agent_values, alpha=0.25, color="#f6c8b6")

# Add labels
ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories)
ax.set_ylim(0, 1)

# Add title and legend
ax.set_title("Comparison between Baseline API and Multi-Agent API", size=15, y=1.08)
ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.0))

plt.tight_layout()
plt.savefig(os.path.join(RESULT_PATH, "baseline_vs_multiagent_radar.png"), dpi=300)
plt.close()
