# 多 Agent 播客对话系统 — 总方案

## 1. 背景与目标

### 现状

`podcast-geeker` 通过外部库 `podcast-creator` 生成播客。核心调用链：

```
commands/podcast_commands.py
  → podcast_creator.create_podcast()
    → 内部 LangGraph: outline → transcript → tts → combine_audio
```

`transcript` 阶段用**一次 LLM 调用、一个大 prompt**，让 LLM 同时扮演所有角色并一次性输出整段对话。无法在生成过程中干预、审查或重试单轮对话。

### 目标

将 `transcript` 阶段替换为**多 Agent 逐轮对话**系统：每个说话人是一个独立 Agent 节点，轮流生成对话，中间可以做质量审查。

```
复用原库              替换                    复用原库
outline  →  [Host ⇌ Expert 循环]  →  tts → combine_audio
```

---

## 2. 为什么这样做


| 维度    | 现状（单次 LLM 调用）       | 改造后（多 Agent 节点）           |
| ----- | ------------------- | ------------------------- |
| 角色一致性 | 一个 LLM 同时演多个角色，容易串戏 | 每个 Agent 只演一个角色，prompt 专注 |
| 过程控制  | 对话跑偏只能整段重来          | 每轮检查，不合格只重做这一轮            |
| 可扩展性  | 加新角色要改整个 prompt     | 加一个节点即可                   |
| 技术展示  | 只是 prompt 工程        | LangGraph 多节点编排 + 条件路由    |


---

## 3. 架构图

```
┌─────────────┐
│  generate   │  复用 podcast-creator 的 generate_outline_node
│   outline   │  输入：素材 + briefing → 输出：大纲（segments 列表）
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────────┐
│              多 Agent 对话循环                │
│                                              │
│  ┌──────────┐    ┌────────────┐              │
│  │ host_turn │──→│ expert_turn │              │
│  └──────────┘    └─────┬──────┘              │
│       ↑                │                     │
│       │   ┌────────────▼────────────┐        │
│       │   │    should_continue      │        │
│       │   │  轮数够了？→ review      │        │
│       │   │  不够？→ host_turn       │        │
│       │   └────────────┬────────────┘        │
│       │                │                     │
│       │   ┌────────────▼────────────┐        │
│       └───│    quality_review       │        │
│           │  通过？→ 下一 segment    │        │
│           │  不通过？→ host_turn     │        │
│           └─────────────────────────┘        │
│                                              │
│  每个 segment 独立运行，segment 间可并行      │
└──────────────┬───────────────────────────────┘
               │
               ▼
┌─────────────┐
│  generate   │  复用 podcast-creator 的 TTS + 音频合并
│    audio    │  transcript → 多声音 TTS → 拼接 → MP3
└─────────────┘
```

---

## 4. 状态设计

```python
# podcast_geeker/podcasts/state.py

from typing import Annotated
import operator
from typing_extensions import TypedDict


class PodcastAgentState(TypedDict):
    # 从 podcast-creator 传入
    content: str            # 素材原文
    briefing: str           # 播客简报
    speakers: list          # 说话人配置列表（来自 SpeakerProfile）
    outline: dict           # 大纲（generate_outline 的输出）

    # 多 Agent 对话过程
    current_segment: int    # 当前 segment 索引
    transcript: Annotated[list, operator.add]  # 对话历史（逐条追加）
    turn_count: int         # 当前 segment 已对话轮数
    max_turns: int          # 每 segment 目标轮数

    # 质量控制
    quality_score: float    # 最近一次评审分数（0–1）
    retry_count: int        # 当前 segment 重试次数
    review_feedback: str    # 评审反馈文本

    # 最终输出
    final_transcript: list  # 完整 transcript（传给 TTS）
    audio_file: str         # 最终音频路径
```

---

## 5. 节点职责


| 节点                 | 调 LLM?     | 职责                                 |
| ------------------ | ---------- | ---------------------------------- |
| `generate_outline` | 是          | 复用原库，生成 segment 大纲                 |
| `host_turn`        | 是          | Host Agent 生成一句话（开场、提问、追问）         |
| `expert_turn`      | 是          | Expert Agent 生成一句话（回答、解释、举例）       |
| `should_continue`  | **否**      | 纯逻辑：轮数够了去 review，不够继续对话            |
| `quality_review`   | 是          | 评审 Agent：打分 + 反馈，决定通过或重做           |
| `after_review`     | **否**      | 纯逻辑：通过则推进下一 segment，不通过回 host_turn |
| `generate_audio`   | 否（TTS API） | 复用原库，文字转语音                         |
| `combine_audio`    | 否          | 复用原库，合并音频片段                        |


---

## 6. LangGraph 工作流定义

```python
# podcast_geeker/graphs/podcast.py

from langgraph.graph import END, START, StateGraph
from podcast_geeker.podcasts.state import PodcastAgentState
from podcast_geeker.podcasts.nodes import (
    host_turn_node,
    expert_turn_node,
    should_continue,
    quality_review_node,
    after_review,
)
from podcast_creator.nodes import (
    generate_outline_node,
    generate_all_audio_node,
    combine_audio_node,
)

graph = StateGraph(PodcastAgentState)

graph.add_node("generate_outline", generate_outline_node)   # 复用原库
graph.add_node("host_turn", host_turn_node)                  # 自定义
graph.add_node("expert_turn", expert_turn_node)              # 自定义
graph.add_node("quality_review", quality_review_node)        # 自定义
graph.add_node("generate_audio", generate_all_audio_node)   # 复用原库
graph.add_node("combine_audio", combine_audio_node)          # 复用原库

graph.add_edge(START, "generate_outline")
graph.add_edge("generate_outline", "host_turn")
graph.add_edge("host_turn", "expert_turn")
graph.add_conditional_edges("expert_turn", should_continue, {
    "continue": "host_turn",
    "review": "quality_review",
})
graph.add_conditional_edges("quality_review", after_review, {
    "pass": "generate_audio",
    "retry": "host_turn",
})
graph.add_edge("generate_audio", "combine_audio")
graph.add_edge("combine_audio", END)

graph = graph.compile()
```

---

## 7. Prompt 模板

**Host Agent** (`prompts/podcast/host_turn.jinja`)

```
你是播客主持人 {{ host.name }}，风格：{{ host.personality }}。

当前话题（大纲 segment {{ segment_index }}）：{{ current_segment }}

对话历史：
{% for turn in transcript[-6:] %}
{{ turn.speaker }}: {{ turn.dialogue }}
{% endfor %}

请以 Host 身份说下一句话（一句，不超过 80 字）：
- 若是开场：介绍话题
- 若对话进行中：向 Expert 提问或追问刚才的回答
- 若快结束：引导收尾

只输出你的台词，不要加角色名前缀。
```

**Expert Agent** (`prompts/podcast/expert_turn.jinja`)

```
你是播客嘉宾 {{ expert.name }}，背景：{{ expert.backstory }}，风格：{{ expert.personality }}。

当前话题：{{ current_segment }}
Host 刚才说：{{ transcript[-1].dialogue }}

请以 Expert 身份回应（一句，不超过 100 字）：
- 直接回应 Host 的问题
- 结合专业背景给出具体见解
- 适当用类比或例子

只输出你的台词，不要加角色名前缀。
```

**Quality Review** (`prompts/podcast/quality_review.jinja`)

```
评审以下播客对话段落，打分并给出反馈。

话题：{{ current_segment }}
对话：
{% for turn in segment_transcript %}
{{ turn.speaker }}: {{ turn.dialogue }}
{% endfor %}

评分标准：
- 相关性（0–3）：对话是否紧扣话题
- 流畅性（0–3）：对话是否自然，无生硬感
- 深度（0–4）：是否有实质内容，避免空洞

请返回 JSON：
{"score": 0.0~1.0, "feedback": "...", "pass": true/false}
```

---

## 8. 入口切换

`commands/podcast_commands.py` 改一处调用（其余 profile 加载、API key provision、输出目录等全部保留）：

```python
# 改前
result = await create_podcast(
    content=input_data.content,
    briefing=briefing,
    episode_name=input_data.episode_name,
    output_dir=str(output_dir),
    speaker_config=speaker_profile.name,
    episode_profile=episode_profile.name,
)

# 改后
from podcast_geeker.graphs.podcast import graph as podcast_graph

result = await podcast_graph.ainvoke({
    "content": input_data.content,
    "briefing": briefing,
    "speakers": speaker_profile.speakers,
    "episode_name": input_data.episode_name,
    "output_dir": str(output_dir),
}, config={"configurable": {
    "outline_model": f"{episode_profile.outline_provider}/{episode_profile.outline_model}",
    "transcript_model": f"{episode_profile.transcript_provider}/{episode_profile.transcript_model}",
    "tts_provider": speaker_profile.tts_provider,
    "tts_model": speaker_profile.tts_model,
}})
```

---

## 9. 文件结构

```
podcast_geeker/
├── graphs/
│   ├── ask.py              （已有）
│   ├── chat.py             （已有）
│   ├── source.py           （已有）
│   └── podcast.py          ← 新建：多 Agent LangGraph 工作流
├── podcasts/
│   ├── models.py           （已有）
│   ├── state.py            ← 新建：PodcastAgentState
│   └── nodes.py            ← 新建：host_turn, expert_turn, quality_review 节点

prompts/podcast/
├── outline.jinja           （已有，复用）
├── transcript.jinja        （已有，保留作 fallback）
├── host_turn.jinja         ← 新建
├── expert_turn.jinja       ← 新建
└── quality_review.jinja    ← 新建

commands/
└── podcast_commands.py     （已有，改一行入口）

evaluation/                 ← 新建：评估体系（§10–§12）
├── eval_metrics.py         ← 自动指标计算（BERTScore / ROUGE / Distinct / PPL）
├── llm_judge.py            ← LLM-as-Judge 多维评估
├── run_experiments.py      ← 批量跑对比实验
├── analyze_results.py      ← 结果汇总 + 可视化
├── test_cases/             ← 15 组测试话题 + 参考对话
└── results/                ← 实验产出存放

prompts/evaluation/
└── judge.jinja             ← LLM-Judge prompt 模板

training/                   ← 可选：QLoRA 微调（§13）
├── generate_training_data.py
├── finetune_qlora.py
├── export_model.py
└── data/
    ├── train.jsonl
    └── val.jsonl
```

核心新建 **5 个文件**，修改 **1 个文件**；评估体系新增 **5 个文件 + 1 个 prompt**；微调（可选）新增 **3 个文件**。

---

## 10. 评估体系

> **必做。** Guideline Section 4 明确要求 quantitative results（tables/figures）+ qualitative examples。

### 10.1 自动指标（#14）

`evaluation/eval_metrics.py`，对每组实验的生成对话批量计算：


| 指标                          | 库                  | 衡量                          |
| --------------------------- | ------------------ | --------------------------- |
| **BERTScore** (F1)          | `bert-score`       | 语义相似度（vs 参考对话）              |
| **ROUGE-L**                 | `rouge-score`      | n-gram 序列重叠                 |
| **Distinct-1 / Distinct-2** | 自实现                | 词汇多样性（unigram / bigram 去重比） |
| **Perplexity**              | `evaluate` + 小型 LM | 流畅度（说明所用 base model）        |


**测试集**：15 个话题（与训练/生成数据不重叠），每个话题准备一段高质量参考对话（GPT-4o 生成后人工确认）。

### 10.2 LLM-as-Judge（#15）

`evaluation/llm_judge.py` + `prompts/evaluation/judge.jinja`，使用 GPT-4o 对生成对话做多维打分（1–5）：


| 维度               | 说明           |
| ---------------- | ------------ |
| Role Consistency | 角色行为是否始终符合人设 |
| Naturalness      | 对话是否自然流畅     |
| Informativeness  | 是否有实质内容      |
| Topic Relevance  | 是否紧扣话题       |
| Engagement       | 是否有听下去的吸引力   |


对应课程 Lecture 5 的 **LLM-as-a-judge** 方法。

### 10.3 对比实验设计（#16）

在相同的 15 个测试话题上，对比至少三组配置：


| Config                         | 描述                                        | 目的                    |
| ------------------------------ | ----------------------------------------- | --------------------- |
| **A — Baseline**               | 单次大 prompt 生成整段对话（原 `podcast-creator` 方式） | 基准线                   |
| **B — Multi-Agent + API**      | 多 Agent + GPT-4o-mini                     | 验证多 Agent 架构价值        |
| **C — Multi-Agent + 无 review** | 多 Agent，跳过 quality_review                 | 消融：验证 review agent 效果 |


可选消融：不同 `max_turns`（3 / 5 / 7）验证轮数对质量的影响。

**记录要求**（放报告 Table 1）：硬件、Python 版本、LLM 版本、`max_turns`、`max_retries`、总耗时。

---

## 11. 结果分析与可视化（#17）

`evaluation/analyze_results.py` 汇总 §10 产出，生成报告所需素材：


| 素材           | 内容                                                           |
| ------------ | ------------------------------------------------------------ |
| **Table 2**  | 自动指标对比（BERTScore / ROUGE-L / Distinct-1/2 / PPL），每 Config 一行 |
| **Table 3**  | LLM-Judge 多维平均分对比                                            |
| **Figure 1** | 指标对比柱状图或雷达图                                                  |
| **Figure 2** | 定性样例——每个 Config 各选 best / worst 一组并排展示                       |


**定性样例选取原则**：同一话题输入，三组 Config 产出对齐，保留原始 transcript 逐句。

---

## 12. 伦理与社会影响（#18）

> **必做。** Guideline Section 5 明确要求讨论 bias, privacy, safety, fairness。


| 维度             | 本项目具体风险             | 缓解思路                                |
| -------------- | ------------------- | ----------------------------------- |
| **AI 语音合成**    | 仿声风险、未经同意使用他人声线     | 明示 AI 生成标签；使用 TTS API 预设音色而非克隆      |
| **生成内容偏见**     | LLM 可能放大文化/性别刻板印象   | quality_review 加偏见检测维度；多话题分布测试      |
| **内容误导性**      | 播客内容可能被当作事实         | 在播客开头加免责声明（Episode Profile 配置项）     |
| **隐私**         | 用户上传素材在云端处理         | podcast-geeker 支持完全自托管 + 本地模型；数据不外传 |
| **微调数据偏见（可选）** | 合成训练数据可能继承 API 模型偏见 | 数据审核步骤；记录话题分布避免单一视角                 |


参考：课程 Lecture 9（Responsible AI and Safety）。

---

## 13. 可选：QLoRA 微调（#11–#13）

> **非必须。** Guideline Methodology 中 "LoRA, QLoRA" 是 **举例（e.g.）**，不是强制项。本项目通过 prompt engineering + agent design + RAG 已满足要求。时间充裕时可作为加分项完成。

### 13.1 为什么不做也合理


| 因素    | 说明                                                   |
| ----- | ---------------------------------------------------- |
| 数据量限制 | 播客对话风格样本稀缺，合成数据质量难以超越 GPT-4o-mini 直接推理               |
| 成本    | QLoRA 需要 GPU 资源和额外工程成本；API 方案更稳定可控                   |
| 替代充分  | prompt engineering（角色 persona + few-shot）在这个任务上已有强基线 |


### 13.2 做了能展示什么

- SFT 数据合成流程（#11）
- QLoRA 超参与训练配置，对应报告 Table（#12）
- training loss curve（报告 Figure）
- 多 Agent 工作流中的模型可插拔架构（#13）

### 13.3 技术方案概要

- **基座模型**：Qwen2.5-7B-Instruct（受限可降为 3B）
- **技术栈**：HuggingFace PEFT + TRL SFTTrainer，4-bit QLoRA，rank=16, alpha=32
- **训练环境**：Colab Pro / 学校 HPC
- **集成**：导出 LoRA adapter → GGUF → Ollama，在工作流中作为 `transcript_model` 可选项

---

## 14. 速度预估


| 场景                                 | 预估耗时     |
| ---------------------------------- | -------- |
| 本地模型（Ollama 7B）                    | 10–20 分钟 |
| 付费 API（GPT-4o-mini / Gemini Flash） | 1–2 分钟   |
| 付费 API + segment 并行                | < 1 分钟   |


TTS 与音频合并阶段两条路径耗时相同，速度瓶颈只在 LLM 对话生成阶段。

---

## 15. 风险与降级


| 风险                      | 降级方案                                           |
| ----------------------- | ---------------------------------------------- |
| Week 9–10 时间不够          | 先跑通 Host⇌Expert 基础循环，暂不加 quality_review        |
| 本地模型太慢                  | 换 API 模型（GPT-4o-mini 单次调用 < 1 秒）               |
| podcast-creator 节点接口不兼容 | 直接调 Esperanto TTS 接口，不复用原库 TTS 节点              |
| segment 并行引入状态冲突        | 回退为串行，牺牲速度保正确性                                 |
| 评估脚本跑不出结果               | 至少保留 LLM-Judge 打分（无需参考对话）+ 定性样例                |
| QLoRA 训练失败（可选项）         | 降为 future work，Discussion 中分析 prompt-only 的合理性 |


最小可交付版本（MVP）：`generate_outline` → `host_turn ⇌ expert_turn` 循环 → `generate_audio` → `combine_audio`，不含 quality_review 和并行优化。

---

## 16. Issue 与架构图对应关系

### 16.1 架构图三区域总览

整个管线分为三个区域，分别对应"复用原库"和"核心新增"部分：

```
区域 1：大纲生成（复用 podcast-creator）
  └── generate_outline

区域 2：多 Agent 对话循环（核心新增）
  ├── host_turn        ← Host Agent 说一句话
  ├── expert_turn      ← Expert Agent 说一句话
  ├── should_continue  ← 纯逻辑：轮数路由
  ├── quality_review   ← 评审 Agent 打分
  └── after_review     ← 纯逻辑：通过/重试路由

区域 3：音频生成（复用 podcast-creator）
  ├── generate_audio   ← TTS 文字转语音
  └── combine_audio    ← 合并音频片段 → MP3
```

### 16.2 Issue 与架构图组件对应表


| Issue        | 对应架构图组件                                                               | 类比         | 说明                                                                                                 |
| ------------ | --------------------------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------- |
| **Issue 1**  | 区域 1 的 `generate_outline` + 区域 3 的 `generate_audio` / `combine_audio` | 确认能不能拆零件   | 验证这 3 个节点能否从 `podcast-creator` 单独导入；决定整体架构策略                                                       |
| **Issue 2**  | 连接所有方块的"数据管道"                                                         | 定义托盘格式     | `PodcastAgentState` 是 State 字典，不是图上任何一个方块，而是所有节点共享的数据容器                                            |
| **Issue 3**  | 区域 2 中 3 个调 LLM 方块的"大脑"                                               | 操作手册       | `host_turn.jinja` / `expert_turn.jinja` / `quality_review.jinja`，节点是"手"，Prompt 是"手里的工具"            |
| **Issue 4**  | 区域 2 的全部 5 个方块                                                        | 造出每个工人     | `host_turn_node` / `expert_turn_node` / `quality_review_node` / `should_continue` / `after_review` |
| **Issue 5**  | 架构图上的所有箭头（边/路由）                                                       | 画传送带路线图    | 用 `add_edge` / `add_conditional_edges` 把方块连起来，定义执行顺序和条件分叉                                          |
| **Issue 6**  | 架构图的"最外层开关"                                                           | 把客户订单接到新工厂 | 修改 `podcast_commands.py`，把入口从 `create_podcast()` 切换到 `podcast_graph.ainvoke()`                     |
| **Issue 7**  | 整张架构图的端到端验证                                                           | 通电测试       | 从素材输入到音频输出完整跑通，验证每个方块和每条箭头都正确                                                                      |
| **Issue 14** | 评估体系 — 自动指标                                                           | 质检报告       | BERTScore / ROUGE / Distinct / PPL，批量评估三组 Config 产出                                                |
| **Issue 15** | 评估体系 — LLM-as-Judge                                                   | 专家打分       | GPT-4o 五维评审，输出结构化分数                                                                                |
| **Issue 16** | 对比实验设计与执行                                                             | 三方横评       | 跑通 Config A/B/C，记录硬件/超参/耗时                                                                         |
| **Issue 17** | 结果分析与可视化                                                              | 出报告        | 汇总 tables/figures + 定性样例                                                                           |
| **Issue 18** | 伦理与社会影响                                                               | 合规审查       | 报告 Discussion 伦理段                                                                                  |


### 16.3 State 与 Graph 边的区别

这是最容易混淆的一点：


|       | Issue 2：State  | Issue 5：Graph 边 |
| ----- | -------------- | --------------- |
| 回答的问题 | **数据长什么样？**    | **执行顺序是什么？**    |
| 类比    | 表格的列定义（schema） | 流水线的传送带路线图      |
| 控制的是  | 字段名、类型、默认值     | 谁先跑、谁后跑、什么条件分叉  |


**State 只定义"有哪些格子"**，不知道谁往里写、谁从里读、什么顺序。  
**Graph 边定义"谁先谁后"**，`host_turn` 结束后必须进 `expert_turn`，`expert_turn` 结束后根据 `should_continue` 的返回值决定走哪条路。

没有 Graph 边：LangGraph 不知道从哪个节点开始、到哪里结束、中间怎么走。  
没有 State：节点之间无法传递数据，每个节点都是孤立的。

### 16.4 关键路径与并行关系

```
核心实现（串行）：
Issue 1 → Issue 2 → Issue 4 → Issue 5 → Issue 6 → Issue 7
              ↘ Issue 3 ↗

评估体系（Issue 7 完成后汇合）：
Issue 14 ─┐
Issue 15 ─┼─→ Issue 16 → Issue 17
           │
Issue 7  ──┘

完全独立（立即并行）：
Issue 9（波形播放器）
Issue 10（TTS 接入）
Issue 18（伦理分析）

可选（时间充裕）：
Issue 11 → Issue 12 → Issue 13 ──→ Issue 16（作为 Config D）
```

---

## 17. 扩展功能

### 17.1 Issue 9 — 前端播客内容可视化（wavesurfer.js）

**目标**：将 `EpisodeCard.tsx` 中的原生 `<audio controls>` 替换为交互式波形播放器。

**与核心管线的关系**：完全独立，不依赖 Issue 1–7，可立即并行开始。

**改造范围**：

```
frontend/src/components/podcasts/
└── WaveformPlayer.tsx    ← 新建

frontend/src/components/podcasts/EpisodeCard.tsx
  第 252-254 行（弹窗内）：<audio controls> → <WaveformPlayer>
  第 399-403 行（卡片底部）：<audio controls> → <WaveformPlayer>
```

**WaveformPlayer 接收的 prop**：

```tsx
interface WaveformPlayerProps {
  audioSrc: string  // 复用 EpisodeCard 现有鉴权 Blob URL，第 141 行 audioSrc state
}
```

功能要求：实时波形渲染、播放/暂停、进度 seek、时间戳显示、Dark/Light 主题适配。

---

### 17.2 Issue 10 — 高质量 TTS 接入

**核心结论：纯配置任务，不需要修改任何 Python 代码。**

现有 `openai-compatible` provider 机制已经支持任何暴露 `/v1/audio/speech` 接口的 TTS 服务，直接在 SpeakerProfile 和 Credential DB 中配置即可。

#### 推荐技术栈


| 用途       | 选型                   | Provider 配置                        |
| -------- | -------------------- | ---------------------------------- |
| 英文内容 TTS | OpenAI tts-1-hd      | `tts_provider = openai`            |
| 中文内容 TTS | MiniMax Speech-01-HD | `tts_provider = openai-compatible` |
| 对话生成 LLM | GPT-4o-mini          | `transcript_provider = openai`     |
| 大纲生成 LLM | GPT-4o-mini          | `outline_provider = openai`        |


#### 英文 SpeakerProfile 示例

```json
{
  "tts_provider": "openai",
  "tts_model": "tts-1-hd",
  "speakers": [
    { "name": "Host",   "voice_id": "nova", "backstory": "...", "personality": "Warm, curious, asks clear questions" },
    { "name": "Expert", "voice_id": "onyx", "backstory": "...", "personality": "Knowledgeable, concise, uses examples" }
  ]
}
```

#### 中文 SpeakerProfile 示例

```json
{
  "tts_provider": "openai-compatible",
  "tts_model": "speech-01-hd",
  "speakers": [
    { "name": "主持人", "voice_id": "female-tianmei",  "backstory": "...", "personality": "活泼，善于引导，提问清晰" },
    { "name": "嘉宾",   "voice_id": "male-qn-qingse", "backstory": "...", "personality": "专业，有条理，善用比喻" }
  ]
}
```

MiniMax Credential DB 配置：

```
provider: openai_compatible
api_key:  <MiniMax API Key>
base_url: https://api.minimaxi.chat/v1
```

如中英混合效果不理想，可替换为 Fish Audio（`base_url: https://api.fish.audio/v1`），接入方式完全相同。

---

### 17.3 完整 Issue 列表


| Issue | 标题                       | 难度     | 负责人             | 依赖           | 必做?    |
| ----- | ------------------------ | ------ | --------------- | ------------ | ------ |
| #1    | 验证 podcast-creator 节点兼容性 | HIGH   | Leader          | —            | 必做     |
| #2    | 创建 PodcastAgentState     | LOW    | AI/NLP          | #1           | 必做     |
| #3    | 创建 Prompt 模板（3 个 Jinja）  | MEDIUM | AI/NLP          | #1           | 必做     |
| #4    | 实现 Agent 节点（gpt-4o-mini） | HIGH   | AI/NLP          | #2, #3       | 必做     |
| #5    | 构建 LangGraph 工作流         | MEDIUM | AI/NLP          | #1, #4       | 必做     |
| #6    | 切换入口调用                   | LOW    | AI/NLP          | #5           | 必做     |
| #7    | 集成测试与质量调优                | MEDIUM | AI/NLP + Leader | #6           | 必做     |
| #9    | 波形播放器（wavesurfer.js）     | MEDIUM | Frontend        | —            | 可选     |
| #10   | TTS 接入（OpenAI / MiniMax） | LOW    | Audio           | —            | 可选     |
| #11   | 合成播客对话训练数据               | MEDIUM | AI/NLP          | —            | **可选** |
| #12   | QLoRA 微调播客对话模型           | HIGH   | AI/NLP          | #11          | **可选** |
| #13   |                         | MEDIUM | AI/NLP          | #12, #5      | **可选** |
| #14   | 评估框架 — 自动指标              | MEDIUM | AI/NLP          | —            | 必做     |
| #15   | LLM-as-Judge 多维评估        | MEDIUM | AI/NLP          | —            | 必做     |
| #16   | 对比实验设计与执行                | HIGH   | AI/NLP + Leader | #7, #14, #15 | 必做     |
| #17   | 实验结果分析与可视化               | MEDIUM | AI/NLP          | #16          | 必做     |
| #18   | 伦理与社会影响分析                | LOW    | Leader          | —            | 必做     |


