# PRD｜此刻看什么：AI 场景化影视决策 Agent

## 1. 产品定义

“此刻看什么”不是“输入片名或标签后查数据库”的影视搜索框，而是一个 Viewing Decision Agent。

用户往往不知道自己要搜哪一部片，而是在表达一个不完整的观看决策，例如：

- 我想看小众恋爱片
- 一个人睡前看，治愈一点，不要太虐
- 和同学聚会，找一部大家都能笑出来的电影
- 想看悬疑，但不要恐怖
- 像《功夫》一样好笑，但不要再给我热门片
- 给我一点惊喜，但别越过我说的雷点

系统的核心任务是把自然语言编译成可执行的约束、偏好与探索预算，再在合法候选集合中推荐、解释和探索。

## 2. 产品目标

1. 场景理解：理解谁一起看、观看时间、注意力、情绪、时长和容忍度。
2. 确定性优先：明确说出的类型、时长、平台、地区、雷点不能被向量相似度覆盖。
3. 内容理解：除类型外，还理解节奏、关系线、情绪、风险、惊喜维度。
4. 可解释推荐：说明为什么适合此刻、可能踩什么雷、有哪些无剧透看点。
5. 可控探索：允许“给我点惊喜”，但探索只发生在满足 Hard Constraints 的候选池。
6. 多轮决策：信息不足时先问信息增益最高的问题，而不是直接随机给五部片。

非目标：不把 LLM 当事实数据库，不让模型凭记忆宣称具体剧情雷点，不用一个“万能 embedding”替代全部业务规则，也不设计绕过平台反爬或风控的采集链路。

## 3. Intent Schema

自然语言不会直接变成一个向量，而是先生成 SceneProfile。

### 3.1 Hard Constraints

明确说出后必须满足：

- content_type
- required_genres
- runtime_max
- year_min
- platform
- language / region
- avoid_genres
- avoid_risks
- required_signals，例如“好笑”“节奏快”这类不满足就明显答错的信号

### 3.2 Soft Preferences

用于排序，不要求全部满足：

- companions
- scene
- moods
- tone
- pace
- cognitive_load
- relationship_focus
- popularity_preference
- quality_preference
- audience preference
- reference-title similarity

### 3.3 Exploration Budget

- precise = 0
- balanced 约 0.3
- explore 约 0.65

探索预算只影响合法集合内部排序，不会改变 Hard Gate。

## 4. AI 产品是否需要特征清单

需要，而且要把它当作 Feature Contract，而不是散落在 Prompt 中的一堆形容词。

| 特征层 | 示例 | 主要用途 |
| --- | --- | --- |
| Hard Metadata | 类型、语言、地区、时长、年份、平台 | 精确过滤 |
| Scene Context | 独处、朋友、家庭、聚会、睡前、饭后、通勤 | 场景适配 |
| Affect | 轻松、治愈、好笑、浪漫、紧张、刺激、烧脑 | 情绪匹配 |
| Narrative | 节奏、认知负担、信息密度、反转强度 | 观看成本 |
| Relationship | 恋爱、友情、家庭、职场 | 关系线匹配 |
| Tone | 甜、温柔、现实、苦甜、暗黑、怪趣、风格化 | 气质匹配 |
| Risk | 恐怖、暴力、成人尺度、社死、情绪沉重、死亡哀伤 | Hard / Soft Negative |
| Discovery | 热度、主流度、新鲜度、评分 | 探索排序 |
| Evidence Quality | 数据源、置信度、剧透等级 | 决定是否允许下结论 |

Feature Schema 要版本化。每个新特征必须说明数据来源、计算方式、是否可做 Hard Constraint、缺失值策略、置信度、使用环节以及对应 Eval Case。

## 5. 是否要平均池化成百维向量

不建议把全部标签、剧情、雷点、平台、时长平均池化成一个约 100 维的万能向量。

原因：

- 向量相似度是连续值，不适合表达“绝对不能恐怖”。
- 时长、年份、平台是精确字段，不应该被语义近似。
- 风险标签需要证据和置信度，不能被平均掉。
- “恋爱片”和“烧脑片”在文本向量上可能接近，但用户说了恋爱片时不能因此越界。

当前 Demo 的职责拆分：

- Structured Feature：确定性边界
- Sparse FTS / BM25：显式词和类别召回
- 128d multilingual LSA：语义召回
- Evidence Chunk：RAG 解释

生产版本可以替换成更强的 embedding 模型和向量数据库。维数由模型和检索效果决定，不是为了“百维”而人为平均池化。

## 6. 数据如何存

### Demo

- SQLite：影片主实体、结构化特征、Evidence、Vector
- GitHub Pages：公开内容源 + curated fallback
- Redis：可选 Session / Cache

### 生产建议

PostgreSQL / MySQL：
- 内容主表
- 可精确过滤的 Feature
- 来源与版本
- 平台可用性
- Evidence 元数据

pgvector / Qdrant / Milvus / Elasticsearch Vector：
- content semantic embedding
- evidence chunk embedding

Redis：
- session state
- query cache
- rate limit
- 短生命周期 candidate cache

Object Storage：
- 原始数据快照
- 离线中间产物

不建议把完整影视主库全部以 JSON 塞进 Redis。Redis 更适合短生命周期状态；灵活字段可以使用 PostgreSQL JSONB，但关键可过滤字段仍应结构化。

## 7. RAG 是什么

RAG = Retrieval-Augmented Generation。

这个产品里要区分两种 Retrieval。

Candidate Retrieval 解决“哪些片值得进入候选池”，使用 Structured + Sparse + Dense。

Evidence Retrieval 解决“为什么推荐它、有没有用户关心的雷点、这句话有没有依据”。

Evidence RAG 的流程是：

1. 已经选出候选影片；
2. 按 content_id 检索该片的简介、官方描述、编辑标注、家长指南等 Evidence Chunk；
3. 按 spoiler_level 过滤；
4. LLM 只基于证据生成“为什么推荐 / 雷点 / 无剧透看点”。

因此 RAG 不是整个推荐算法，而是推荐解释和内容理解的证据层。

## 8. 数据源与 API 边界

当前公开工程使用：

- TVMaze API：剧集基础元数据、海报、类型、国家、时长、评分；
- Wikidata SPARQL：电影和中国内容补充；
- 可选 OpenAI API：只做 Soft Intent Enrichment。

LLM 不得覆盖确定性 Hard Constraint。

未来如果获得腾讯视频、爱奇艺、优酷、芒果 TV 等官方或授权接口，应通过统一 Adapter 接入。没有授权时只使用公开合法数据和来源链接，不通过绕过反爬机制取得数据。

## 9. 全链路流程

~~~mermaid
flowchart TD
    A[用户自然语言] --> B[Intent Compiler]
    B --> C[SceneProfile]
    C --> C1[Hard Constraints]
    C --> C2[Soft Preferences]
    C --> C3[Exploration Budget]

    C1 --> D1[Structured Recall]
    C2 --> D2[Sparse FTS / BM25]
    C2 --> D3[Dense Semantic Recall]
    D1 --> E[Candidate Union]
    D2 --> E
    D3 --> E

    E --> F[Hard Gate]
    F -->|不合法| X[Discard]
    F -->|合法| G[Feature + Scene Rerank]

    C3 --> H[Exploration Controller]
    G --> H
    H --> I[Top K]

    I --> J[Evidence Retrieval]
    J --> K[spoiler-safe RAG]
    K --> L[Why / Watchouts / Surprise]
    L --> M[用户反馈]
    M --> N[Session / Preference Signals]
~~~

## 10. 召回和排序

一个可调试 baseline：

RetrievalScore = Sparse + Semantic + Structured + EvidenceQuality 的加权组合。

进入 Hard Gate 后，RankScore 再加入：

- Genre / RequiredSignal
- Relationship
- Mood / Tone / Pace
- Scene Fit
- Popularity Preference
- Quality Preference
- Risk Penalty

Explore 模式额外引入 novelty、diversity 和 surprise，但 Hard Gate 始终在探索之前。

## 11. “小众恋爱片”为什么不能推荐烧脑片

正确解析：

- content_type = movie
- required_genres = Romance
- relationship_focus = romantic
- popularity_preference = niche
- exploration_mode = precise

执行：

召回候选 → Romance Hard Gate → 非 Romance 全部删除 → 只在剩余恋爱片中按小众度、氛围、场景排序。

因此即使一部烧脑悬疑片的 embedding 非常接近 Query，也没有资格进入结果。

如果用户第二轮选择“想烧脑”，它只是对“合法恋爱电影”内部增加 thought_provoking 偏好，而不是取消 Romance 约束。

## 12. 场景化为什么不是“多几个标签”

产品真正的差异是 Context × Content。

同一部片在不同场景下排序不同：

- 家庭饭后：成人尺度、恐怖、尴尬风险权重显著提高；
- 朋友聚会：喜剧 payoff、互动性和快节奏更重要；
- 一个人睡前：低认知负担、温柔、治愈更重要；
- 周末沉浸：长片、世界观、视觉奇观惩罚降低；
- 通勤：单集时长和中断友好度更重要。

## 13. 内容理解、雷点与惊喜

每部内容至少维护三层。

Entity / Metadata：
片名、类型、年份、时长、国家、海报、平台。

Content Intelligence：
relationship、tone、pace、cognitive load、themes、risk tags、surprise dimension、popularity bucket。

Evidence：
每条 Risk / Surprise 至少包含 evidence_type、text、source_ref、confidence、spoiler_level。

如果只有“类型 + 一句话简介”，系统必须明确显示证据不足，不能说“确定没有某类雷点”。

## 14. 多轮澄清策略

不应该每次固定追问三四题，而是只问信息增益最高的问题。

例如用户说“我想看小众恋爱片”，已经确定电影、恋爱、小众，但不知道谁一起看，所以先问：

“这次是自己看，还是和别人一起看？”

下一轮再根据需要问：

“更想轻松、刺激、治愈，还是烧脑？”

当已有足够约束时直接推荐，不为了展示 Agent 而强行追问。

## 15. API 设计

Session：
- POST /v1/sessions
- GET /v1/sessions/{session_id}

Chat：
- POST /v1/sessions/{session_id}/chat
- Response type：clarify / recommend / no_match

Catalog：
- GET /v1/catalog/search?q=
- GET /v1/catalog/browse
- GET /v1/content/{content_id}

Debug：
- GET /health
- GET /v1/demo/meta
- GET /v1/demo/feature-schema

Feedback：
- POST /v1/sessions/{session_id}/feedback

## 16. AI 每个环节要调试什么

| 环节 | 关键指标 |
| --- | --- |
| Intent | Hard constraint accuracy、slot accuracy、conflict detection |
| Recall | Recall@K、source coverage、empty recall rate |
| Hard Gate | constraint violation rate，目标 0 |
| Rerank | NDCG、Top-K relevance、scene fit |
| Exploration | diversity 上升且 constraint violation 仍为 0 |
| Evidence | evidence coverage、unsupported-claim rate |
| RAG | groundedness、spoiler violation、hallucination |
| Multi-turn | clarification rate、turns-to-decision、abandonment |
| Data | poster coverage、feature coverage、stale platform rate |

每次新增规则都必须配 Eval Query，不靠“感觉调 Prompt”。

## 17. 核心回归 Case

1. “小众恋爱片” → Top K 全部 Romance。
2. “悬疑，不要恐怖” → Horror violation = 0。
3. “和朋友聚会，轻松好笑” → Comedy / funny signal 高覆盖。
4. “一个人睡前，治愈，90 分钟内” → runtime violation = 0。
5. “给我点惊喜，但不要恐怖” → 多样性提升但 Horror violation = 0。
6. “像《功夫》一样好笑” → 相似性来自喜剧、节奏和风格，而不是只靠标题 embedding。

## 18. 上线分层

GitHub Pages 用于作品集体验：零密钥、可直接对话、公开 API + curated fallback、浏览器执行硬过滤和场景排序。

Full Backend 用于工程展示和可扩展架构：FastAPI、SQLite / Postgres、Redis、Sparse + Dense Hybrid Recall、Hard Gate、Reranker、Evidence RAG、可选 OpenAI soft intent。

两个版本共享同一原则：先守边界，再做探索。
