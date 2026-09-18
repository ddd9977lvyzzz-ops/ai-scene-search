# PRD V1.2 — 此刻看什么 / Scene Decision Agent

## 1. 产品重新定义

这不是“影视版万能搜”，也不是给数据库套一个聊天框。

核心问题不是“用户在找哪部片”，而是：

> **用户此刻处于什么观看状态，哪些内容边界绝不能踩，什么作品最适合现在这个人/这群人。**

与电商搜索不同，影视决策很少有稳定的“加购/购买”行为可直接复制。真实需求高度依赖当下：同行者、精力、时间、情绪、关系风险、剧情雷点、是否能被打断、是否想探索新口味。

因此推荐系统必须从“相似商品”思路转向 **Scene + Constraint + Content Understanding**。

---

## 2. V1.2 已实现能力

### 2.1 Plot Fact Constraints / 剧情事实硬约束

用户可以直接说：

- 没有任何人死去
- 不要有人出轨
- 不要伤害动物
- 不要血腥
- 不要 jump scare
- 结局圆满
- 不要开放式结局
- 和爸妈看，不要大尺度

这些要求不作为普通 embedding 相似度，而进入 required_facts / avoid_risks。

关键规则：

> **Unknown != Safe**

数据库没有“角色死亡”证据，不代表“已确认没有角色死亡”。

只有 content_facts.no_character_death = true 的候选，才能通过“没人死”硬条件。

### 2.2 Confidence-aware Near Miss

当硬约束过多导致 0 结果时，Agent 不偷偷放宽条件。

它会返回：

- 最接近的候选
- 每个候选具体被哪一条规则拦截

例如：

> 《X》：缺少“没有角色死亡”证据  
> 《Y》：满足剧情边界，但时长超过 90 分钟

这是“决策解释”，而不是普通搜索。

### 2.3 Pick-one Decision Mode

用户可以说：

> “别给列表，直接替我选一个。”

Agent 会保留所有硬约束，但只输出排序第一位，让产品从“结果页”变成“替用户做低风险决定的 Agent”。

### 2.4 Explore-within-boundaries

“给我点惊喜”不会解锁被明确禁止的内容。

探索只能改变：

- 国家 / 地区
- 年代
- 子类型
- 叙事结构
- 热度
- 风格

不能突破：

- 类型硬条件
- 内容形态
- 时长
- 指定平台
- 风险边界
- 剧情事实

---

## 3. 数据资产

### 3.1 一部影片不是一个 embedding

每条内容拆为：

1. Entity / Metadata
2. Scene Features
3. Emotion / Tone
4. Narrative Features
5. Relationship / Theme
6. Risk Tags
7. Plot Facts
8. Evidence Chunks
9. Semantic Vectors
10. Poster / Visual Asset

### 3.2 Plot Facts

V1.2 增加：

- no_character_death
- happy_ending
- no_animal_harm
- no_infidelity
- no_gore
- no_jump_scares
- no_sexual_content
- family_safe
- closed_ending
- romance_central
- friendship_central
- career_central

每个 fact 后续应保存：

- value
- confidence
- evidence_source
- spoiler_level
- extraction_version

### 3.3 海报

产品质量门槛：

> poster coverage = 100%

顺序：

source poster
→ alternate source
→ stable generated SVG poster

生成海报必须显式标记为 generated fallback，不冒充官方物料。

---

## 4. 2026 国产内容层

Demo 新增 2026 国产内容，用来解决旧库年份滞后和国产内容不足。

当前精选包括：

- 惊蛰无声
- 镖人：风起大漠
- 飞驰人生3
- 星河入梦
- 熊猫计划之部落奇遇记
- 熊出没·年年有熊
- 群星闪耀时
- 家业
- 一瓯春
- 深渊无间

信息源优先使用国家电影局和正版平台公开页面。

---

## 5. V2 Recall Architecture

用户 Query
→ Query Compiler
→ Constraint Ledger
→ Parallel Recall
→ RRF Merge
→ Hard Gate
→ Contextual Rerank
→ Evidence Retrieve
→ Response Planner

### Parallel Recall

A. Structured Recall
- genre
- type
- year
- runtime
- platform
- plot facts

B. Sparse Recall
- BM25 / FTS
- title / synopsis / theme / aliases

C. Dense Semantic Recall
- synopsis + themes embedding

D. Scene Feature Vector
- 可解释 0/1 或连续特征向量
- mood / pace / relationship / tone / cognitive load / safety facts

E. Reference-title Recall
- “像《功夫》”
- anchor title 的多个特征空间分别取邻居

不同召回分数不可直接相加，因此先采用 RRF 做候选融合。

---

## 6. 排序

Hard Gate 之后才进入分数。

Final score 可以由以下分量组成：

- structured match
- feature-vector cosine
- semantic similarity
- reference-title similarity
- scene fit
- quality
- novelty
- repetition penalty
- evidence confidence
- risk uncertainty penalty

权重按 Query 动态变化。

“没人死”这类 Query：
plot fact = Hard

“今晚累，只想躺着看”：
cognitive load / pace = High weight

“像《功夫》但不要暴力”：
reference similarity = High weight
violence = Hard Gate

---

## 7. Evidence RAG

推荐阶段和解释阶段分离。

Recommendation Retrieval：
> 从全部影片里找候选。

Evidence RAG：
> 对已经选中的影片检索剧情事实、风险、关系走向和看点证据。

LLM 不能凭模型记忆擅自补：
- 谁死了
- 是否出轨
- 结局是 HE / BE
- 是否有动物伤害

若证据不足，应显示：

> “当前信息不足，不能确认没有这一雷点。”

---

## 8. 与普通 AI 搜索的区别

普通影视 AI 搜索：
Query → embedding → top-k → LLM 写推荐理由

此刻看什么：
Scene Understanding
→ Hard Boundary
→ Content Facts
→ Multi-channel Recall
→ Contextual Ranking
→ Evidence RAG
→ Decision

真正的产品资产不是聊天 UI，而是：

> **可执行的观看决策模型 + 内容理解图谱。**

---

## 9. 下一阶段

优先级 P0：
- 扩大 plot facts 覆盖
- 为 3,339 条内容构建 fact_confidence / evidence
- 将当前单 128d semantic index 升级为 multi-vector
- 增加标题级 poster audit
- 后端接真实在线部署

P1：
- Group Consensus：两个人分别输入雷点/偏好，求 Pareto 最优
- Emotional Arc：想要前松后爽 / 不要后半段压抑
- Watchability：能否边吃饭 / 能否被打断 / 是否需要持续注意字幕
- Spoiler Firewall：用户自己选择能看到几级剧情事实
- Taste Exploration Map：展示推荐为什么离开用户常看区域
