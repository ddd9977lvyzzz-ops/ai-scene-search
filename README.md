# 此刻看什么 · AI 场景化影视决策 Agent

完整 V1.1 工程正在由 GitHub Actions 自动展开。

项目不是“片名搜索聊天壳”，而是把观看场景、明确边界、内容理解和探索空间编译为可执行推荐条件，再经过 Hybrid Recall、Hard Gate、Rerank 和 Evidence RAG 给出结果。

当前基线：
- 3,339 条影视内容
- 160+ 国产剧
- 128 维 multilingual LSA semantic retrieval
- Content Intelligence + spoiler-safe Evidence RAG
- 18 / 18 automated tests passed
- 12 / 12 scenario evals passed
- Top-5 hard-constraint checks 60 / 60

仓库首次提交后，`Expand full project bundle` workflow 会自动将 `bundle/ai-scene-search-v1.1-portable.zip` 展开为完整可浏览源码；随后 CI 与 GitHub Pages workflow 会自动运行。

在线 Demo 部署完成后地址将是：
https://ddd9977lvyzzz-ops.github.io/ai-scene-search/
