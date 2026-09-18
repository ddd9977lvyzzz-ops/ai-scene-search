# 影（YING）PRD V1.3｜场景化影视决策 Agent

> 一句话定位：**不是帮用户“搜到一部片”，而是理解此刻的观看场景、硬边界和情绪成本，替用户做更可靠的观看决策。**

## 1. 用户与核心问题

### 1.1 核心用户群体

| 用户群 | 典型特征 | 主要问题 |
|---|---|---|
| 决策疲劳用户 | 打开多个视频平台仍不知道看什么 | 选择多、决策成本高，传统榜单不理解当下状态 |
| 场景型用户 | 睡前、吃饭、聚会、通勤、约会、陪父母 | “好片”不等于“此刻适合” |
| 高边界用户 | 不想死人、不要出轨、不要跳吓、不要大尺度 | 类型标签过粗，普通推荐无法保证剧情边界 |
| 内容探索用户 | 想看小众、跨地区、非爆款内容 | 算法容易困在热门内容和已有偏好 |
| 多人共看用户 | 情侣、朋友、家人需求不同 | 很难同时满足所有人的雷点与偏好 |

### 1.2 产品中的角色

- **Viewer**：提问、收藏、建立个人观看偏好。
- **Group Viewer**：多人输入边界，求共同可接受结果（P1）。
- **Curator**：发布“场景 + 边界 + 片单”的社区方案。
- **Content / Platform Partner**：提供正版可用性、物料和跳转链接；不能修改用户硬边界。
- **System Moderator**：处理虚假平台信息、错误剧情事实、刷榜和社区低质内容。

### 1.3 五个核心痛点

1. **搜索是片名导向，不是场景导向**：用户经常只知道“今晚很累”“和爸妈看”“不想看到任何人死”。
2. **平台可用性不可靠**：搜索结果可能推荐用户当前平台无法观看的作品。
3. **影视雷点不是普通标签**：“没有人死亡”需要正向剧情事实证据，不能用“数据库没写死亡”代替。
4. **社媒口碑噪声大**：热度、营销、搬运、刷量与真实体验混在一起。
5. **推荐没有沉淀**：用户看过、收藏过、踩过雷的决策过程没有形成可复用资产。

---

## 2. 场景 → 产品功能

| 使用场景 | 用户表达 | 对应功能 |
|---|---|---|
| 一个人下班很累 | “今晚脑子不想转” | Cognitive Load、节奏、可打断性排序 |
| 跟父母一起看 | “不要尴尬、不要大尺度” | Family-safe Plot Facts + Risk Hard Gate |
| 极强剧情边界 | “不要任何人死” | required_facts=no_character_death；Unknown ≠ Safe |
| 指定视频平台 | “我只看爱奇艺” | Verified Platform Availability Hard Gate |
| 想找非爆款 | “小众一点，别都是热门” | Popularity / Novelty Channel |
| 想突破信息茧房 | “给我点惊喜” | Exploration Controller，只在合法候选内探索 |
| 已有参考作品 | “像《功夫》但不要太暴力” | Reference-title Recall + Violence Hard Gate |
| 不想自己做选择 | “别给列表，直接替我选一个” | Decision Mode |
| 推荐后仍犹豫 | “大家为什么喜欢这部？” | Social Evidence：公众号 / 小红书 / 百度 / X 等来源分析 |
| 长期使用 | 收藏、看过、踩雷 | 账户、片单、长期偏好与负反馈记忆 |
| 社区发现 | “爸妈同看不尴尬片单” | Scene Card 社区：场景 + 边界 + 片单 |

---

## 3. 核心产品结构

### 3.0 完整网站信息架构

- **Agent**：核心对话决策页，负责自然语言理解、约束管理、推荐与解释。
- **发现**：按“下班后 / 聚会 / 指定平台 / 小众探索 / 参考作品 / 直接替我选”等场景进入，而不是传统类型榜单。
- **社区**：Scene Card 社区，用户复用“场景 + 边界 + 片单”。
- **片单**：账户收藏、后续看过/不喜欢/踩雷反馈与私人 Scene。
- **内容详情**：真实海报、平台快照、剧情事实、雷点、无剧透看点和证据层。
- **账户**：完整 FastAPI 模式走服务端账户与片单；GitHub Pages 仅保留无密钥预览。

### 3.1 首页 / Agent

输入自然语言 → 自动提取：

- 场景：独处 / 家人 / 朋友 / 情侣 / 聚会 / 睡前等
- 内容：电影 / 剧集 / 综艺 / 动漫
- 情绪：轻松 / 治愈 / 刺激 / 烧脑
- 剧情边界：死亡、出轨、动物伤害、跳吓、血腥、大尺度、开放结局等
- 平台：爱奇艺 / 腾讯视频 / 优酷 / 芒果TV / Netflix 等
- 探索强度：精准 / 适度探索 / 惊喜

### 3.2 推荐结果

每部作品必须回答四件事：

1. **为什么适合你现在这个场景**
2. **明确命中了哪些硬条件**
3. **可能的雷点 / 证据不足项**
4. **在哪里可看，以及平台证据更新时间**

结果默认 5 部；Decision Mode 只给 1 部。

### 3.3 “猜你还想确认”联网观点层

推荐结果之后提供 Social Evidence，而不是简单再塞一排相似影片：

- 这部作品在不同社区被讨论的核心角度
- 正面 / 负面体验分别集中在哪里
- 不同来源是否互相验证
- 哪些讨论可能来自营销、搬运或异常互动
- 保留原始链接、作者、时间和来源平台

**社媒信号只能作为弱排序特征，不能推翻平台、风险和剧情事实 Hard Gate。**

### 3.4 账户与我的片单

- 注册 / 登录
- 收藏
- 看过 / 不喜欢 / 踩雷
- 自定义片单
- 保存 Scene Card
- 后续推荐将收藏视为**弱偏好**，不会因为曾经收藏爱情片就永远推爱情片。

### 3.5 社区模式

社区的内容单位不是“影评”，而是 **Scene Card**：

> 场景 + 人群 + 硬边界 + 推荐理由 + 片单

例：

- 和爸妈看不尴尬
- 没有人死的轻松电影
- 工作日 90 分钟内
- 三个人聚会必须好笑
- 分手后不想再看爱情线

Scene Card 可收藏、复用并一键进入 Agent；优秀 Scene Card 形成自然传播入口。

---

## 4. 推荐与数据系统

### 4.1 内容特征资产

每部作品拆成独立数据层，而不是平均成一个“万能向量”：

**Metadata**  
类型、年份、地区、语言、时长、平台。

**Scene Features**  
适合谁看、注意力要求、是否可被打断、适合吃饭/睡前/聚会等。

**Content Understanding**  
情绪、节奏、关系、主题、叙事密度、世界观、惊喜类型。

**Plot Facts**  
no_character_death、happy_ending、no_infidelity、no_animal_harm、no_gore、no_jump_scares、family_safe 等。

**Evidence**  
剧情事实、雷点、平台可用性都必须带来源和置信度。

### 4.2 召回链路

```text
Query Compiler
    ↓
Constraint Ledger
    ↓
并行召回
├ Structured / SQL
├ BM25 / FTS
├ Semantic Vector
├ Interpretable Scene Vector
├ Reference-title Recall
└ Cached Social Signal
    ↓
RRF Candidate Fusion
    ↓
Hard Gate
    ↓
Contextual Rerank
    ↓
Evidence RAG
    ↓
Decision / Explanation
```

**Hard Gate 永远先于社媒热度和探索。**

### 4.3 平台可用性

平台字段区分：

- `origin_platform`：首播 / 来源信息
- `verified_availability`：当前地区已验证可观看
- `unknown`：没有可靠证据

当用户明确说“只看爱奇艺”时，只接受 `verified_availability=iqiyi` 的候选。

### 4.4 LLM Agent Brain

完整网站不是“自然语言 → 数据库查找”的壳。服务端通过 **OpenAI Responses API** 接入模型，当前默认模型为 `gpt-5.6-terra`，承担两层职责：

1. **Semantic Planning**：理解隐含场景、情绪负荷、语气、关系线、探索意图，并生成 query rewrite / retrieval hints。
2. **Grounded Answer Generation**：只基于 Hard Gate 后的候选、Evidence RAG 与平台证据生成自然语言推荐，不允许模型凭空创造片名、剧情事实或可观看平台。

确定性代码仍掌控平台、年份、时长、明确雷点和 Plot Facts 等 Hard Constraints。也就是说：**LLM 负责理解与表达，检索/RAG负责事实，Hard Gate负责不可违反的边界。**

生产模式若没有模型 API，会直接暴露“Agent 未连接”，不会把本地检索伪装成 AI 回答。

---

## 5. 社媒数据：怎么抓、怎么分真伪

### 5.1 数据接入

**X**：使用官方 Recent Search API。  
**百度**：使用百度 AI Search Web Search API，可指定站点过滤。  
**小红书**：官方开放平台当前主要面向电商/店铺能力，不设计反爬绕过；通过授权来源、公开索引 Web Search 或合作数据接入。  
**公众号**：优先公开索引、媒体合作或授权数据，不爬取私域/受限内容。

### 5.2 可信度评分

每条 Social Evidence 记录：

- source_url
- platform
- author / account
- published_at
- engagement
- entity_confidence
- source_reliability
- authenticity_score
- recommendation_signal

真实性判断至少包含：

1. **实体匹配**：帖子讨论的确实是这部作品。
2. **来源等级**：官方 / 媒体 / 已验证创作者 / 普通 UGC。
3. **去重与搬运检测**：重复文本降权。
4. **时效衰减**：过旧讨论降低权重。
5. **跨平台一致性**：多个独立来源同时出现才提高置信度。
6. **互动异常**：极端互动但低来源可信度不直接视为真实口碑。

Social Score 在总排序中的权重控制在低位（当前设计约 5%），避免“热搜即好看”。

---

## 6. 商业化

### Free

- 基础场景推荐
- 硬边界筛选
- 基础收藏
- 有限次数联网观点检索
- 公共 Scene Card

### YING Pro（订阅）

核心付费价值不是“多推荐几部”，而是降低高频用户的决策成本：

- 无限 / 更高频 Social Evidence 实时检索
- 高级剧情雷点库与更细 Spoiler Control
- 长期偏好记忆与自动复盘
- 多人 Group Consensus
- 跨平台可用性提醒 / 上线提醒
- 私人片单 Agent 与自动整理

### B2B / 联盟收入

- 视频平台正版跳转 / 联盟分成
- 影视社区 / 媒体的 Scene Recommendation API
- 内容平台的剧情风险标签 / 场景标签 SaaS
- 片方宣发可购买**明确标识的 Sponsored Candidate**，但必须先通过用户 Hard Gate，不允许用商业权重突破雷点和平台限制。

---

## 7. GTM 与冷启动

### Phase 1：用“普通推荐做不到的问题”冷启动

首批只打 3 个最容易形成认知的 Demo：

1. **“给我没有任何人死去的电影”**
2. **“和爸妈看，不要尴尬”**
3. **“只看爱奇艺，今晚替我选一个”**

核心传播语不是“AI 推荐电影”，而是：

> **你可以把真正难说清楚的观看条件直接告诉「影」。**

### Phase 2：内容冷启动

- 先人工深标 300–500 部高频作品，保证 Plot Facts 准确性。
- 国产新剧 / 新电影建立高时效 Curated Layer。
- 与影视博主、公众号作者、播客主共建 Scene Card，而不是让他们只写传统影评。

### Phase 3：社媒增长

**小红书**：做“场景题”而非片单题，例如“求没有人死的治愈电影”。评论区直接收集真实自然语言 Query。  
**B站 / 抖音**：短视频演示极端 Query → Agent 如何拆约束 → 为什么普通榜单会错。  
**公众号**：发布场景型主题片单并嵌入 Scene Card。  
**X / 海外**：用 trigger-aware / group movie night / decision fatigue 切海外场景。

### Phase 4：增长闭环

```text
社媒 Scene Case
→ 打开预填 Query
→ 首次推荐
→ 收藏 / 分享
→ 注册保存
→ 生成个人 Scene Card
→ 分享到社媒 / 群聊
→ 新用户带着完整场景进入
```

---

## 8. 北极星指标与质量指标

**North Star：每周“成功完成观看决策”的用户数。**

代理指标：

- 首次 Query → 收藏 / 平台跳转率
- 推荐后继续追问率
- 片单收藏率
- Scene Card 复用率 / 分享率
- D7 / D30 回访
- Social Evidence 展开率
- 指定平台命中率

质量红线：

- **Hard Constraint Violation Rate = 0**
- 平台误报率
- Plot Fact 错误率
- Social Evidence 错绑作品率
- 0 结果率与合理放宽率

---

## 9. 版本边界

### 当前项目已实现

- 场景对话
- Plot Fact 硬约束
- 2026 国产精选层
- 真实海报 Strict Gate：canonical catalog 只接受 HTTP(S) poster asset，缺失时通过 TVMaze/TMDB 回填，未补齐则构建失败
- Verified Platform Gate（Demo 已校准爱奇艺样本）
- OpenAI Responses API Agent Brain：语义规划 + grounded answer generation；Hard Constraints 仍由确定性代码掌控
- 多路召回 / Scene Vector / RRF
- Social Evidence 后端接口与真实性评分框架
- 完整网站 SPA：Agent / 发现 / 社区 / 片单
- 标签可点击逐项删除，并同步服务端 Session Profile
- FastAPI 服务端账户、收藏片单与 Scene Community；Pages 仅作本地预览
- Decision Mode

### 下一版本 P0

1. 将 3,339 条内容扩充为高覆盖 Plot Facts + Evidence。
2. 增加真实平台可用性定时刷新。
3. 配置百度 AI Search / X API 后上线 Social Evidence 实时检索。
4. 将服务端账户、Session、Event 从 Demo SQLite 升级为持久化生产存储。
5. 加入“看过 / 不喜欢 / 踩雷”反馈闭环。

### P1

- 多人 Group Consensus
- 社区 Scene Card 发布与排序
- 上线提醒 / 跨平台订阅
- 个性化 Taste Map
- 付费 Pro 与 B2B API

---

## 10. 外部接口依据

- X Developer Docs：Recent Search / Posts Search 使用官方 API。
- 百度 AI Search：`POST /v2/ai_search/web_search`，支持 Web Search、站点过滤和时效过滤。
- 小红书开放平台公开入口目前以电商、店铺授权和工具型应用为主，因此本项目不设计绕过反爬的通用笔记抓取。
