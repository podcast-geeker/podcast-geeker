import os
import json
import re
import threading
from openai import OpenAI
from typing import Dict, Any, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import partial

# Initialize OpenAI client
client = OpenAI(
    base_url=os.environ.get(
        "OPENAI_COMPATIBLE_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"
    ),
    api_key=os.environ.get(
        "OPENAI_COMPATIBLE_API_KEY", "21f29eb8ef124b7daeb1d274339f6293.ttsP3FjbHVxjkR6W"
    ),
)

RESULT_PATH = "./experiments/evaluation/data"
RESULT_NAME = "evaluate.json"

# File lock to prevent concurrent file writes from multiple threads
file_lock = threading.Lock()


def clean_thinking_content(content: str) -> str:
    """Clean thinking tag content"""
    cleaned = re.sub(r"<thinking>.*?</thinking>", "", content, flags=re.DOTALL)
    return cleaned.strip()


def evaluate_with_llm(
    topic_id: str, model_output: str, reference_output: str
) -> Dict[str, Any]:
    """
    Use LLM to evaluate model output

    Args:
        topic_id: Topic ID
        model_output: Model-generated dialogue text
        reference_output: Reference dialogue text

    Returns:
        Dictionary containing scores for each dimension
    """
    prompt = f"""You are an expert dialogue evaluator. Please evaluate the following model-generated dialogue against a reference dialogue.

Topic: {topic_id}

Model Output:
{model_output}

Reference Output:
{reference_output}

Please evaluate the model output on the following dimensions (1-5 points for each):

1. Role Consistency: Are the Host and Expert roles distinct and consistent?
2. Naturalness: Is the dialogue natural and fluent?
3. Informativeness: Does the content have depth and rich information?
4. Topic Relevance: Does the content stay focused on the topic?
5. Engagement: Is the dialogue engaging?

Please provide your evaluation in the following JSON format:
{{
    "role_consistency": <1-5>,
    "naturalness": <1-5>,
    "informativeness": <1-5>,
    "topic_relevance": <1-5>,
    "engagement": <1-5>
}}

Provide only the JSON directly, no additional text, do note use markdown."""

    try:
        response = client.chat.completions.create(
            model=os.environ.get("EXPERIMENT_LLM_MODEL", "glm-5-turbo"),
            messages=[
                {
                    "role": "system",
                    "content": "You are a professional dialogue evaluator. Always respond with valid JSON.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=800,
        )

        # Validate response
        if not response.choices or not response.choices[0].message:
            print(f"Empty response for topic {topic_id}")
            return {
                "role_consistency": -1,
                "naturalness": -1,
                "informativeness": -1,
                "topic_relevance": -1,
                "engagement": -1,
            }

        content = response.choices[0].message.content
        if not content:
            print(f"Empty content for topic {topic_id}")
            return {
                "role_consistency": -1,
                "naturalness": -1,
                "informativeness": -1,
                "topic_relevance": -1,
                "engagement": -1,
            }

        # Clean special format content
        cleaned_content = clean_thinking_content(content)

        # Parse JSON
        return json.loads(cleaned_content.strip())

    except json.JSONDecodeError as e:
        print(f"JSON decode error for topic {topic_id}: {str(e)}")
        print(f"Content was: {cleaned_content[:500]}")
        return {
            "role_consistency": -1,
            "naturalness": -1,
            "informativeness": -1,
            "topic_relevance": -1,
            "engagement": -1,
        }
    except Exception as e:
        print(f"Error evaluating topic {topic_id}: {str(e)}")
        return {
            "role_consistency": -1,
            "naturalness": -1,
            "informativeness": -1,
            "topic_relevance": -1,
            "engagement": -1,
        }


def load_evaluation_results() -> Dict[str, Any]:
    """Load existing evaluation results"""
    result_path = os.path.join(RESULT_PATH, RESULT_NAME)
    if os.path.exists(result_path):
        with open(result_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_evaluation_results(evaluate: Dict[str, Any]) -> None:
    """Save evaluation results (thread-safe)"""
    result_path = os.path.join(RESULT_PATH, RESULT_NAME)

    # Use file lock to ensure thread safety
    with file_lock:
        # Create temp file
        temp_path = f"{result_path}.tmp"
        with open(temp_path, "w+", encoding="utf-8") as f:
            json.dump(evaluate, f, ensure_ascii=False, separators=(",", ":"), indent=0)

        # Atomic replace original file
        if os.path.exists(result_path):
            os.replace(temp_path, result_path)
        else:
            os.rename(temp_path, result_path)


def evaluate_topic(
    model_name: str, topic: str, reference_model: str = "reference"
) -> Tuple[str, str, Dict[str, Any]]:
    """
    Evaluate single topic (thread-safe)

    Args:
        model_name: Model name
        topic: Topic ID
        reference_model: Reference model name

    Returns:
        Tuple of (model_name, topic_id, evaluation_results)
    """
    # Load existing evaluation results
    evaluate = load_evaluation_results()

    # Ensure model exists in evaluation results
    if model_name not in evaluate:
        evaluate[model_name] = {"topics": {}}

    # Skip if already evaluated
    if (
        topic in evaluate[model_name]["topics"]
        and "llm_evaluation" in evaluate[model_name]["topics"][topic]
        and -1 not in evaluate[model_name]["topics"][topic]["llm_evaluation"].values()
    ):
        print(f"Skipping {model_name}/{topic} (already evaluated)")
        return (model_name, topic, None)

    print(f"Evaluating {model_name}/{topic}")

    # Load model output and reference output
    model_path = os.path.join(RESULT_PATH, model_name, f"{topic}.json")
    ref_path = os.path.join(RESULT_PATH, reference_model, f"{topic}.json")

    if not os.path.exists(model_path) or not os.path.exists(ref_path):
        print("  Skip: Missing data files")
        return (model_name, topic, None)

    with open(model_path, "r", encoding="utf-8") as f:
        model_data = json.load(f)
    with open(ref_path, "r", encoding="utf-8") as f:
        ref_data = json.load(f)

    # Extract dialogue text
    model_text = "\n".join([turn["text"] for turn in model_data["turns"]])
    ref_text = "\n".join([turn["text"] for turn in ref_data["turns"]])

    # Evaluate using LLM
    topic_scores = evaluate_with_llm(topic, model_text, ref_text)

    print(f"  Completed evaluation for {model_name}/{topic}")
    return (model_name, topic, topic_scores)


def evaluate_all_parallel(
    models: List[str],
    topics: List[str],
    reference_model: str = "reference",
    max_workers: int = None,
) -> None:
    """
    Evaluate all models and topics in parallel

    Args:
        models: List of models
        topics: List of topics
        reference_model: Reference model name
        max_workers: Maximum number of workers, default is None (automatically use system max threads)
    """
    # Load existing evaluation results
    evaluate = load_evaluation_results()

    # Ensure all models exist in evaluation results
    for model in models:
        if model not in evaluate:
            evaluate[model] = {"topics": {}}

    # Initialize LLM score accumulators
    llm_scores = {
        model: {
            "role_consistency": [],
            "naturalness": [],
            "informativeness": [],
            "topic_relevance": [],
            "engagement": [],
        }
        for model in models
    }

    # Create all evaluation tasks
    tasks = []
    for model in models:
        tasks.extend((model, topic) for topic in topics)

    # Use thread pool to evaluate all topics in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Create evaluation tasks
        future_to_task = {
            executor.submit(evaluate_topic, model, topic, reference_model): (
                model,
                topic,
            )
            for model, topic in tasks
        }

        # Process completed tasks
        for future in as_completed(future_to_task):
            model, topic = future_to_task[future]
            try:
                model_name, topic_id, topic_scores = future.result()
                if topic_scores:
                    # Accumulate dimension scores
                    for dimension in llm_scores[model_name]:
                        llm_scores[model_name][dimension].append(
                            topic_scores[dimension]
                        )

                    # Save evaluation results to memory
                    evaluate[model_name]["topics"][topic][
                        "llm_evaluation"
                    ] = topic_scores
            except Exception as e:
                print(f"Error evaluating topic {model}/{topic}: {str(e)}")

    # Calculate average scores and save results
    for model in models:
        if llm_scores[model]["role_consistency"]:  # Ensure there are evaluation results
            evaluate[model]["llm_evaluation"] = {
                dimension: sum(scores) / len(scores)
                for dimension, scores in llm_scores[model].items()
            }

    # Save final results (after all topic evaluations complete)
    save_evaluation_results(evaluate)
    print("Completed LLM evaluation for all models")


def main():
    """Main function"""
    # Define models and topics to evaluate
    models = [
        "baseline_api",
        "multi_agent_api",
        "multi_agent_review",
        "Llama_baseline_base",
        "Llama_baseline_ft",
    ]

    topics = [
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

    # Evaluate all models and topics in parallel
    evaluate_all_parallel(models, topics, max_workers=10)


if __name__ == "__main__":
    main()
