## 大型檔案（GitHub Releases）

下列檔案**不納入 Git**，請在 [Releases](https://github.com/podcast-geeker/podcast-geeker/releases) 下載對應資產後放到專案路徑（或自行解壓）：

| 資產建議檔名 | 放到 |
|--------------|------|
| `podcast-expert-lora.zip`（或本機曾命名為 `podcast-expert-lora (1).zip`） | 解壓到 `experiments/podcast-expert-lora/`，或依 notebook 說明放在 Colab 工作目錄 |
| `experiment_local_results.zip` | 解壓到 `experiments/evaluation/data/` |
| `Llama_experiment_local_results.zip` | 解壓到 `experiments/evaluation/data/` |
| `api_3configs.zip` | 解壓到 `experiments/evaluation/data/` |
| `evaluation_architecture.jpg` | `experiments/evaluation_architecture.jpg` |

維護者發佈新版本時：在 GitHub 上 **Create a new release**，將上述檔案以 **Release assets** 上傳（可與應用程式版本 tag 分開，例如 `experiments-assets-v1`）。

使用 `curl` 下載範例（將 `TAG` 與 `ASSET` 換成實際 release 與檔名）：

```bash
curl -fL -o experiments/podcast-expert-lora.zip \
  "https://github.com/podcast-geeker/podcast-geeker/releases/download/TAG/ASSET"
```

---

執行流程
本地（需設定環境變數）：

```
export OPENAI_COMPATIBLE_BASE_URL=https://your-glm-endpoint/v1
export OPENAI_COMPATIBLE_API_KEY=your-api-key
cd experiments
python prepare_sources.py                    # Step 1: 生成 9 份來源文件
python generate_transcript.py --config ref   # Step 2: 參考對話
python generate_transcript.py --config A     # Step 3: Baseline
python generate_transcript.py --config B     # Step 4: Multi-Agent
# 或一次跑完: python generate_transcript.py --config all
```

Colab Pro（T4 GPU）：

上傳 podcast-expert-lora.zip + evaluation/data/topics/*.txt
依序執行 notebook 的 6 個 cells
下載 experiment_local_results.zip，解壓到 evaluation/data/
每筆結果 JSON 都已嵌入 4 項系統指標（latency / input_tokens / output_tokens / cost / peak_gpu_memory），Phase 2 的 eval 和 visualize 直接讀取即可。


---

============================================================
Experiment Transcript Generator
============================================================
  Model   : glm-5-turbo
  Base URL: https://open.bigmodel.cn/api/paas/v4
  Configs : ['A', 'B', 'B_review', 'ref']
  Topics  : 9

--- Config A (baseline_api) ---
  [1/9] tech_1_transformer_attention ...   [WARN] Could not parse JSON turns, returning raw text as single turn
done  latency=72.7s  tokens=3214  cost=$0.0022
  [2/9] tech_2_qlora_finetuning ... done  latency=22.1s  tokens=2943  cost=$0.0021
  [3/9] tech_3_multi_agent ...   [WARN] Could not parse JSON turns, returning raw text as single turn
done  latency=38.4s  tokens=3138  cost=$0.0022
  [4/9] hum_1_ai_bias_fairness ... done  latency=31.1s  tokens=2967  cost=$0.0021
  [5/9] hum_2_ai_privacy ...   [WARN] Could not parse JSON turns, returning raw text as single turn
done  latency=24.6s  tokens=3124  cost=$0.0022
  [6/9] hum_3_ai_safety_alignment ... done  latency=26.0s  tokens=3081  cost=$0.0022
  [7/9] med_1_ai_medical_imaging ...   [WARN] Could not parse JSON turns, returning raw text as single turn
done  latency=25.6s  tokens=3133  cost=$0.0022
  [8/9] med_2_clinical_trials ...   [WARN] Could not parse JSON turns, returning raw text as single turn
done  latency=25.3s  tokens=3112  cost=$0.0022
  [9/9] med_3_ai_drug_discovery ... done  latency=18.9s  tokens=2936  cost=$0.0021

--- Config B (multi_agent_api) ---
  [1/9] tech_1_transformer_attention ... done  latency=61.7s  tokens=11587  cost=$0.0081
  [2/9] tech_2_qlora_finetuning ... done  latency=38.4s  tokens=12763  cost=$0.0089
  [3/9] tech_3_multi_agent ... done  latency=48.8s  tokens=11271  cost=$0.0079
  [4/9] hum_1_ai_bias_fairness ... done  latency=37.9s  tokens=11866  cost=$0.0083
  [5/9] hum_2_ai_privacy ... done  latency=60.7s  tokens=11511  cost=$0.0081
  [6/9] hum_3_ai_safety_alignment ... done  latency=73.9s  tokens=11786  cost=$0.0083
  [7/9] med_1_ai_medical_imaging ... done  latency=58.4s  tokens=12016  cost=$0.0084
  [8/9] med_2_clinical_trials ... done  latency=43.0s  tokens=11006  cost=$0.0077
  [9/9] med_3_ai_drug_discovery ... done  latency=56.7s  tokens=10981  cost=$0.0077

--- Config B_review (multi_agent_review) ---
  [1/9] tech_1_transformer_attention ... done  latency=34.8s  tokens=12969  cost=$0.0091
  [2/9] tech_2_qlora_finetuning ... done  latency=46.3s  tokens=13557  cost=$0.0095
  [3/9] tech_3_multi_agent ... done  latency=43.1s  tokens=12376  cost=$0.0087
  [4/9] hum_1_ai_bias_fairness ... done  latency=68.5s  tokens=12625  cost=$0.0088
  [5/9] hum_2_ai_privacy ... done  latency=48.2s  tokens=12463  cost=$0.0087
  [6/9] hum_3_ai_safety_alignment ... done  latency=49.2s  tokens=12680  cost=$0.0089
  [7/9] med_1_ai_medical_imaging ... done  latency=37.9s  tokens=12556  cost=$0.0088
  [8/9] med_2_clinical_trials ... done  latency=50.2s  tokens=12613  cost=$0.0088
  [9/9] med_3_ai_drug_discovery ... done  latency=79.3s  tokens=12414  cost=$0.0087

--- Config ref (reference) ---
  [1/9] tech_1_transformer_attention ... done  latency=33.8s  tokens=3490  cost=$0.0024
  [2/9] tech_2_qlora_finetuning ... done  latency=26.3s  tokens=2443  cost=$0.0017
  [3/9] tech_3_multi_agent ... done  latency=29.8s  tokens=3132  cost=$0.0022
  [4/9] hum_1_ai_bias_fairness ... done  latency=33.8s  tokens=3320  cost=$0.0023
  [5/9] hum_2_ai_privacy ...   [WARN] Could not parse JSON turns, returning raw text as single turn
done  latency=40.0s  tokens=3649  cost=$0.0026
  [6/9] hum_3_ai_safety_alignment ... done  latency=24.3s  tokens=3085  cost=$0.0022
  [7/9] med_1_ai_medical_imaging ... done  latency=60.3s  tokens=3396  cost=$0.0024
  [8/9] med_2_clinical_trials ... done  latency=37.5s  tokens=3562  cost=$0.0025
  [9/9] med_3_ai_drug_discovery ... done  latency=70.0s  tokens=3507  cost=$0.0025

[Done] All transcripts generated.