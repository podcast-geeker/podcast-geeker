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

| 维度 | 现状（单次 LLM 调用） | 改造后（多 Agent 节点） |
|---|---|---|
| 角色一致性 | 一个 LLM 同时演多个角色，容易串戏 | 每个 Agent 只演一个角色，prompt 专注 |
| 过程控制 | 对话跑偏只能整段重来 | 每轮检查，不合格只重做这一轮 |
| 可扩展性 | 加新角色要改整个 prompt | 加一个节点即可 |
| 技术展示 | 只是 prompt 工程 | LangGraph 多节点编排 + 条件路由 |

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

| 节点 | 调 LLM? | 职责 |
|---|---|---|
| `generate_outline` | 是 | 复用原库，生成 segment 大纲 |
| `host_turn` | 是 | Host Agent 生成一句话（开场、提问、追问） |
| `expert_turn` | 是 | Expert Agent 生成一句话（回答、解释、举例） |
| `should_continue` | **否** | 纯逻辑：轮数够了去 review，不够继续对话 |
| `quality_review` | 是 | 评审 Agent：打分 + 反馈，决定通过或重做 |
| `after_review` | **否** | 纯逻辑：通过则推进下一 segment，不通过回 host_turn |
| `generate_audio` | 否（TTS API） | 复用原库，文字转语音 |
| `combine_audio` | 否 | 复用原库，合并音频片段 |

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
```

新建 **5 个文件**，修改 **1 个文件**，其余不动。

---

## 10. 速度预估

| 场景 | 预估耗时 |
|---|---|
| 本地模型（Ollama 7B） | 10–20 分钟 |
| 付费 API（GPT-4o-mini / Gemini Flash） | 1–2 分钟 |
| 付费 API + segment 并行 | < 1 分钟 |

TTS 与音频合并阶段两条路径耗时相同，速度瓶颈只在 LLM 对话生成阶段。

---

## 11. 风险与降级

| 风险 | 降级方案 |
|---|---|
| Week 9–10 时间不够 | 先跑通 Host⇌Expert 基础循环，暂不加 quality_review |
| 本地模型太慢 | 换 API 模型（GPT-4o-mini 单次调用 < 1 秒） |
| podcast-creator 节点接口不兼容 | 直接调 Esperanto TTS 接口，不复用原库 TTS 节点 |
| segment 并行引入状态冲突 | 回退为串行，牺牲速度保正确性 |

最小可交付版本（MVP）：`generate_outline` → `host_turn ⇌ expert_turn` 循环 → `generate_audio` → `combine_audio`，不含 quality_review 和并行优化。

---

## 12. Issue 与架构图对应关系

### 12.1 架构图三区域总览

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

### 12.2 Issue 与架构图组件对应表

| Issue | 对应架构图组件 | 类比 | 说明 |
|-------|--------------|------|------|
| **Issue 1** | 区域 1 的 `generate_outline` + 区域 3 的 `generate_audio` / `combine_audio` | 确认能不能拆零件 | 验证这 3 个节点能否从 `podcast-creator` 单独导入；决定整体架构策略 |
| **Issue 2** | 连接所有方块的"数据管道" | 定义托盘格式 | `PodcastAgentState` 是 State 字典，不是图上任何一个方块，而是所有节点共享的数据容器 |
| **Issue 3** | 区域 2 中 3 个调 LLM 方块的"大脑" | 操作手册 | `host_turn.jinja` / `expert_turn.jinja` / `quality_review.jinja`，节点是"手"，Prompt 是"手里的工具" |
| **Issue 4** | 区域 2 的全部 5 个方块 | 造出每个工人 | `host_turn_node` / `expert_turn_node` / `quality_review_node` / `should_continue` / `after_review` |
| **Issue 5** | 架构图上的所有箭头（边/路由） | 画传送带路线图 | 用 `add_edge` / `add_conditional_edges` 把方块连起来，定义执行顺序和条件分叉 |
| **Issue 6** | 架构图的"最外层开关" | 把客户订单接到新工厂 | 修改 `podcast_commands.py`，把入口从 `create_podcast()` 切换到 `podcast_graph.ainvoke()` |
| **Issue 7** | 整张架构图的端到端验证 | 通电测试 | 从素材输入到音频输出完整跑通，验证每个方块和每条箭头都正确 |

### 12.3 State 与 Graph 边的区别

这是最容易混淆的一点：

| | Issue 2：State | Issue 5：Graph 边 |
|---|---|---|
| 回答的问题 | **数据长什么样？** | **执行顺序是什么？** |
| 类比 | 表格的列定义（schema） | 流水线的传送带路线图 |
| 控制的是 | 字段名、类型、默认值 | 谁先跑、谁后跑、什么条件分叉 |

**State 只定义"有哪些格子"**，不知道谁往里写、谁从里读、什么顺序。  
**Graph 边定义"谁先谁后"**，`host_turn` 结束后必须进 `expert_turn`，`expert_turn` 结束后根据 `should_continue` 的返回值决定走哪条路。

没有 Graph 边：LangGraph 不知道从哪个节点开始、到哪里结束、中间怎么走。  
没有 State：节点之间无法传递数据，每个节点都是孤立的。

### 12.4 关键路径与并行关系

```
关键路径（串行，必须按序完成）：
Issue 1 → Issue 2 → Issue 4 → Issue 5 → Issue 6 → Issue 7
              ↘ Issue 3 ↗

并行机会：
Issue 2 和 Issue 3 在 Issue 1 完成后可同时开始
Issue 9（可视化）和 Issue 10（TTS）完全独立，现在即可开始
```

---

## 13. 扩展功能

### 13.1 Issue 9 — 前端播客内容可视化（wavesurfer.js）

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

### 13.2 Issue 10 — 高质量 TTS 接入

**核心结论：纯配置任务，不需要修改任何 Python 代码。**

现有 `openai-compatible` provider 机制已经支持任何暴露 `/v1/audio/speech` 接口的 TTS 服务，直接在 SpeakerProfile 和 Credential DB 中配置即可。

#### 推荐技术栈

| 用途 | 选型 | Provider 配置 |
|------|------|--------------|
| 英文内容 TTS | OpenAI tts-1-hd | `tts_provider = openai` |
| 中文内容 TTS | MiniMax Speech-01-HD | `tts_provider = openai-compatible` |
| 对话生成 LLM | GPT-4o-mini | `transcript_provider = openai` |
| 大纲生成 LLM | GPT-4o-mini | `outline_provider = openai` |

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

### 13.3 完整 Issue 列表

| Issue | 标题 | 难度 | 负责人 | 依赖 | 可并行? |
|-------|------|------|--------|------|---------|
| #1 | 验证 podcast-creator 节点兼容性 | HIGH | Leader | — | 立即开始 |
| #2 | 创建 PodcastAgentState | LOW | AI/NLP | #1 | — |
| #3 | 创建 Prompt 模板（3 个 Jinja） | MEDIUM | AI/NLP | #1 | 与 #2 并行 |
| #4 | 实现 Agent 节点（gpt-4o-mini） | HIGH | AI/NLP | #2, #3 | — |
| #5 | 构建 LangGraph 工作流 | MEDIUM | AI/NLP | #1, #4 | — |
| #6 | 切换入口调用 | LOW | AI/NLP | #5 | — |
| #7 | 集成测试与质量调优 | MEDIUM | AI/NLP + Leader | #6 | — |
| #9 | 波形播放器（wavesurfer.js） | MEDIUM | Frontend | — | **立即开始** |
| #10 | TTS 接入（OpenAI / MiniMax） | LOW | Audio | — | **立即开始** |
