# 此刻看什么 · AI 场景化影视决策 Agent

一个以“当前观看场景”为核心，而不是只做片名搜索的影视推荐 Agent。

用户可以直接说：“我想看小众恋爱片”“和朋友聚会，想看轻松好笑的电影”“一个人睡前看，想治愈一点，不要太虐”“悬疑一点，但不要恐怖”“像《功夫》一样好笑的电影”。

系统先把自然语言编译成 Hard Constraints + Soft Preferences + Exploration Budget，再执行召回、过滤、排序与解释。

## 当前两套运行形态

### 1. GitHub Pages 在线作品集版

https://ddd9977lvyzzz-ops.github.io/ai-scene-search/

这个版本是无后端、零密钥的可交互 Demo：

- 内置一组经过人工校准的国产剧与代表性电影，保证关键 Case 不因外部 API 失败而失效。
- 浏览器启动后会尝试从 TVMaze 公共 API 拉取约 1000 条实时剧集内容，并转成 Scene / Emotion / Pace / Risk / Relationship 特征。
- Hard Gate、场景重排和“给我点惊喜”直接在浏览器执行。
- 外部数据请求失败时自动退回 curated fallback，不会白屏。

Pages 版的目的，是让面试官或评审打开链接就能体验产品逻辑。它不是生产数据库替代品。

### 2. 完整 FastAPI / RAG 工程版

完整工程基线：

- 3,339 条影视内容
- 3,339 条基线中包含 161 部中国大陆/中文剧集；公开重建数量会随上游数据变化
- Structured Features + 128 维 multilingual LSA semantic retrieval
- Hybrid Recall + Hard Constraint Filter + Feature / Scene / Semantic Rerank
- Content Intelligence + spoiler-safe Evidence RAG
- 可选 OpenAI Structured Intent Enrichment
- SQLite 主数据 + 可选 Redis Session
- Docker / Render 配置
- 18 / 18 automated tests
- 12 / 12 scenario evals
- Top-5 强约束检查 60 / 60

## 推荐链路

用户自然语言
→ Intent / Scene Understanding
→ Hard Constraints：类型 / 内容形态 / 时长 / 平台 / 明确雷点
→ Hybrid Recall：Structured + FTS/BM25 + Semantic
→ Hard Gate
→ Feature Match + Scene Match + Semantic Match
→ Exploration Controller
→ Rerank
→ Evidence Retrieval
→ 为什么推荐 / 可能雷点 / 无剧透惊喜点

核心原则：探索只能发生在合法候选集合内部，不能为了“惊喜”突破用户已经明确说出的边界。

## 为什么之前会出现 GitHub Pages 404

如果看到 “404 — There isn't a GitHub Pages site here.”，它不代表 index.html 路由写错，而是代表 GitHub 还没有成功发布 Pages artifact。

这个项目之前第一次 Pages workflow 在部署前增加了 catalog 完整性检查。当时上传到仓库的压缩 catalog 分片不完整，gzip 校验报 EOFError: Compressed file ended before the end-of-stream marker was reached。

因此 workflow 在 Configure Pages / Deploy 之前就停止了，GitHub 没有创建可访问站点，所以访问 Pages 域名只会得到 404。

现在发布链路已经改成：push main → checkout → configure-pages → upload site artifact → deploy-pages。

在线数据层由浏览器 live public catalog + curated fallback 负责，不再让一个静态压缩数据库阻断整个网站发布。

## “小众恋爱片”为什么不会再跑到烧脑片

该 Query 会被解析成：required_genres=[Romance]；relationship=[romantic]；popularity=niche；content_type=movie；exploration=precise。

Romance 是 Hard Constraint，而不是弱 embedding 特征。任何不满足 Romance 的候选都会先被过滤，即使向量相似度很高也不能进入最终结果。

## 数据 / 向量 / RAG 的职责分离

不要把整部影片所有标签简单平均池化成一个万能向量。

- Structured Feature：负责确定性边界。
- Semantic Vector：负责模糊语义召回。
- Evidence Chunks：负责推荐解释和事实依据。

正式工程中，影片主数据、Feature、Evidence 和 Vector 都是独立可版本化的数据层。

## 数据重建

仓库包含 public-data rebuild pipeline：

- data_pipeline/catalog_builder.py：TVMaze + Wikidata → canonical catalog
- scripts/migrate_content_intelligence.py：Tone / Risk / Surprise / Content Facts
- scripts/migrate_evidence_corpus.py：Evidence chunks
- scripts/build_embeddings.py：128d multilingual LSA
- scripts/verify_catalog.py：质量门槛
- scripts/bootstrap_runtime.py：容器首次启动自动完成上述流程

注意：公开 API 重建是可复现工程路径，不保证每次得到完全相同的条目数量；README 中 3,339 / 161 是已验证基线，不把动态上游数量伪装成固定生产数据。

## 文档

- docs/PRD.md：完整产品边界、Feature Schema、召回排序、RAG、调试指标
- docs/ARCHITECTURE.md：存储、向量、Redis、确定性与探索边界

## Repository

https://github.com/ddd9977lvyzzz-ops/ai-scene-search


## V1.2 — 深化为“观看决策 Agent”

最新版本不再把产品定义为影视版“万能搜”。新增了：

- **剧情事实硬约束**：支持“没有任何人死去 / 不要出轨 / 不伤害动物 / 不血腥 / 不要跳吓 / 结局圆满 / 不要大尺度”等自然语言条件。
- **Unknown ≠ Safe**：数据库没有记录某个雷点，不会自动解释为“没有这个雷点”。
- **Multi-channel recall**：结构化召回、稀疏特征、128d semantic index、可解释 scene vector、reference-title channel 分开，再由 RRF / reranker 融合。
- **Near-miss explanation**：0 结果时展示最接近的候选为什么被硬条件拦截，而不是悄悄放宽条件。
- **Decision Mode**：支持“别给列表，直接替我选一个”。
- **Poster quality gate**：完整数据管道要求 poster coverage = 100%；源站海报缺失时生成稳定 SVG fallback，并显式标记为 generated poster。
- **2026 国产精选层**：加入《惊蛰无声》《镖人：风起大漠》《飞驰人生3》《星河入梦》《熊猫计划之部落奇遇记》《熊出没·年年有熊》《群星闪耀时》《家业》《一瓯春》《深渊无间》等条目。

完整产品定义见：

- `docs/PRD_V1.2_DEEP_AGENT.md`
- `docs/RETRIEVAL_V2.md`

2026 公开信息参考：
- 国家电影局 2026 春节档片单：https://www.chinafilm.gov.cn/xwzx/gzdt/202602/t20260209_949645.html
- 国家电影局 2026 暑期档片单：https://www.chinafilm.gov.cn/xwzx/ywxx/202606/t20260625_996069.html
- 爱奇艺《家业》正片页：https://www.iqiyi.com/a_131ig5wtqg5.html
- 爱奇艺《一瓯春》正片页：https://www.iqiyi.com/a_2b9ocx2qugh.html
- 爱奇艺《深渊无间》正片页：https://www.iqiyi.com/a_okv7zmsbr1.html
