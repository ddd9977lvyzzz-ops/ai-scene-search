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
- 197 条中国大陆内容（其中以国产剧为主）
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

该 Query 会被解析成：required_genres=[Romance]；relationship=[romantic]；popularity=niche；content_type=open；exploration=precise。

Romance 是 Hard Constraint，而不是弱 embedding 特征。任何不满足 Romance 的候选都会先被过滤，即使向量相似度很高也不能进入最终结果。

## 数据 / 向量 / RAG 的职责分离

不要把整部影片所有标签简单平均池化成一个万能向量。

- Structured Feature：负责确定性边界。
- Semantic Vector：负责模糊语义召回。
- Evidence Chunks：负责推荐解释和事实依据。

正式工程中，影片主数据、Feature、Evidence 和 Vector 都是独立可版本化的数据层。

## Repository

https://github.com/ddd9977lvyzzz-ops/ai-scene-search
