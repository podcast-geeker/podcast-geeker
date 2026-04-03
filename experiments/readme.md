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