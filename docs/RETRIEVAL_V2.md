# Retrieval V2 — Multi-channel Scene Retrieval

## 为什么不做“一个万能向量”

单个平均向量会把完全不同的信号压成一团：

- Romance 是不是必须
- 有没有人死亡
- 是否小众
- 是否适合爸妈
- 是否烧脑
- 是否和某部片相似

这些信号有不同的数学角色。

因此系统将信息分成三类：

### 1. Deterministic

SQL / inverted index / exact facts：

- type
- runtime
- platform
- language
- explicit genre
- risk
- plot facts

负责 “能不能”。

### 2. Interpretable Scene Vector

当前 Demo 维护一组显式维度：

funny, light, relaxing, healing, romantic, exciting, tense,
thought_provoking, scary, fast, slow, friendship, family,
sweet, gentle, realistic, bittersweet, dark, playful, warm,
niche, no_character_death, happy_ending, family_safe,
no_gore, no_jump_scares ...

它不是替代 embedding，而是提供：

- 可解释
- 可调权重
- 适合场景逻辑
- 可作为 dense channel 之外的第二向量空间

### 3. Semantic Dense Vector

完整后端保留 128d LSA semantic index。

下一版建议拆成：

- semantic_profile_vector
- plot_theme_vector
- scene_fit_vector
- evidence_chunk_vectors

不要平均池化成一个固定 100 维结果。

## Recall

并行获取：

- Structured top-N
- FTS/BM25 top-N
- Dense top-N
- Scene vector top-N
- Reference title top-N

然后用 Reciprocal Rank Fusion 合并：

RRF(d) = Σ 1 / (k + rank_channel(d))

这样不会把 BM25 分数、cosine 分数和业务分强行放在同一数值尺度上。

## Hard Gate

RRF 只决定进入候选池。

最终任何候选仍必须经过：

- required_genre
- required_fact
- avoid_risk
- runtime
- platform
- type

探索模式也不能绕过 Hard Gate。

## Rerank

候选集进入 contextual reranker：

score =
  structured * 2.2
+ scene_vector * 2.4
+ semantic * 1.8
+ reference * 1.2
+ quality * 0.5
+ novelty * 0.35
- uncertainty_penalty
- repetition_penalty

真正上线时权重由离线 Eval + 在线反馈学习，而不是长期手写。

## “没有任何人死去”示例

Query compiler:

required_facts = ["no_character_death"]
content_type = movie

Structured recall 可以先召回已标 no_character_death=true 的内容。

即使 dense embedding 认为某部悲剧电影非常“温暖治愈”，它也会在 Hard Gate 被删除。

这就是产品区别：

> embedding 可以猜“像什么”，但不能决定“是否违反用户明确边界”。
