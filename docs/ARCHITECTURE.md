# Technical Architecture

## 系统边界

~~~mermaid
flowchart LR
    UI[Web / App] --> API[FastAPI]
    API --> IC[Intent Compiler]
    IC --> HP[Hard Profile]
    IC --> SP[Soft Scene Profile]

    HP --> SR[Structured Recall]
    SP --> BM[FTS / BM25]
    SP --> DV[Dense Vector Search]

    SR --> U[Candidate Union]
    BM --> U
    DV --> U

    U --> HG[Hard Gate]
    HG --> RR[Reranker]
    RR --> EX[Exploration Controller]
    EX --> TOP[Top K]

    TOP --> ER[Evidence Retriever]
    ER --> RAG[Grounded Explanation]
    RAG --> UI

    DB[(Postgres / SQLite)] --> SR
    DB --> BM
    VDB[(pgvector / Vector DB)] --> DV
    EDB[(Evidence Store)] --> ER
    REDIS[(Redis)] --> API
~~~

## Storage Contract

权威内容主实体不放 Redis。

Canonical Store 负责片名、metadata、结构化 feature、source、version、platform availability 和 evidence metadata。

Vector Store 至少区分 content semantic vector 与 evidence chunk vector。两种向量的职责不同，不应该混为一个“万能向量”。

Redis 只用于 session profile、已曝光候选、短期缓存、rate limit 和临时偏好状态。

## Determinism Boundary

LLM 可以做：

- soft intent enrichment
- theme / tone 的语言归一化
- 基于 Evidence 的自然语言解释

LLM 不可以做：

- 删除显式 Hard Constraint
- 凭记忆宣称某片存在或不存在具体敏感情节
- 在没有证据时填补平台可用性
- 让 Explore 模式重新召回已被 Hard Gate 删除的候选

## Public Data Adapter

当前公开 Repo 使用 TVMaze 和 Wikidata SPARQL。

未来可以替换成授权平台 Adapter。Adapter 层只需要输出统一 Record；下游 Feature、Vector、Ranking 不绑定某一家平台。

## Vector Strategy

Demo 使用 128d multilingual LSA，因为它可离线复现、不需要 API Key、能够真实展示 vector coverage，并且方便离线评测。

生产环境可替换为托管 embedding API 或自部署 multilingual embedding。替换 Vector Adapter 不需要改变 Hard Gate。

## RAG Boundary

Candidate Retrieval 和 Evidence Retrieval 必须分开。

Query → Candidate Retrieval → Hard Gate → Rank → Content IDs

Content IDs → Evidence Retrieval → spoiler-safe grounded explanation

这样可以避免“检索到一段相似剧情，就把另一部片当作推荐候选”的耦合错误。
