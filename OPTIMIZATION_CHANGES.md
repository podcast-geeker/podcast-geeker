# Podcast Geeker 性能优化改动说明

本文档记录本次针对“问答速度”和“音频生成速度”做的实际代码改动。

## 改动概览

本次改动涉及 2 个文件：

1. `api/routers/chat.py`
2. `commands/podcast_commands.py`

目标：

- 降低问答链路中的阻塞和串行等待
- 降低播客生成前的准备时间开销

---

## 1) 问答链路优化（`api/routers/chat.py`）

### 1.1 避免事件循环阻塞

**改动位置：**

- `execute_chat()` 中执行 `chat_graph` 的部分

**改动前：**

- 在异步路由里直接调用同步 `chat_graph.invoke(...)`
- 这会阻塞事件循环，影响并发请求响应

**改动后：**

- 改为 `await asyncio.to_thread(chat_graph.invoke, ...)`
- 将同步调用放入工作线程执行，主事件循环保持可调度

**预期收益：**

- 高并发时接口更稳定，其他请求不易被单次 LLM 推理阻塞
- 平均响应时间和尾延迟（P95/P99）下降

### 1.2 上下文构建由串行改为并发

**改动位置：**

- `build_context()` 中 source/note 上下文聚合逻辑

**改动前：**

- 逐个 source/note 串行读取与构建上下文

**改动后：**

- 使用 `asyncio.gather(..., return_exceptions=True)` 并发处理 source 和 note
- 对 note 的同步 `get_context` 使用 `asyncio.to_thread` 并发调度
- 出错项跳过并记录 warning，不影响整体构建

**预期收益：**

- 多源、多笔记场景下上下文构建耗时明显缩短
- 用户在“生成前准备/问答前准备”阶段等待时间减少

---

## 2) 播客生成链路优化（`commands/podcast_commands.py`）

### 2.1 配置加载从“全量”改为“按需”

**改动位置：**

- `generate_podcast_command()` 中 profile 配置部分

**改动前：**

- 每次生成时查询并转换所有 `episode_profile` 与 `speaker_profile`
- 实际只会用到当前所选 profile

**改动后：**

- 仅对当前选中的 `episode_profile` 和对应 `speaker_profile` 做归一化并注入配置
- 移除该处全表查询依赖

**预期收益：**

- 生成前准备阶段数据库查询与数据转换开销下降
- profile 数量增长时依然保持较好启动速度

### 2.2 Provider Key Provision 并发化

**改动位置：**

- `providers_to_provision` 处理段

**改动前：**

- provider key 逐个串行 provision

**改动后：**

- 去重后，使用 `asyncio.gather` 并发 provision（`ollama` 仍跳过）

**预期收益：**

- 多 provider 混用时准备阶段更快

---

## 验证结果

执行语法编译检查：

```bash
python -m compileall api/routers/chat.py commands/podcast_commands.py
```

结果：通过（2 个文件均可编译）。

---

## 兼容性与风险说明

1. 本次改动未调整接口协议（request/response 字段保持不变）。
2. 并发化后日志顺序可能与串行模式不同，属预期行为。
3. `build_context` 改为并发后，个别 source/note 异常仍会被容错跳过，不影响总体返回。

---

## 后续可继续优化（本次未改）

1. 在 `podcast_geeker/graphs/ask.py` 中对 strategy 产出的查询词去重与裁剪，减少重复向量检索与 LLM 调用。
2. 为 `vector_search` 增加短期缓存（同会话/同问题窗口）以复用 embedding 与检索结果。
3. 在播客生成链路增加分阶段耗时埋点（outline/transcript/tts/mix），用于精确定位真实瓶颈。
4. 若 `podcast_creator` 支持，开启 TTS 并行合成或批量合成。
