# YING Full Agent 部署

GitHub Pages 只是静态预览。完整 YING 运行形态是：

```text
Web UI
  → FastAPI
    → OpenAI Responses API
    → canonical catalog / semantic retrieval / Hard Gate
    → Evidence RAG
    → optional Baidu AI Search / X social evidence
```

## 1. 必填服务端 Secrets

### OPENAI_API_KEY

完整 Agent 必填。生产配置默认：

```env
OPENAI_AGENT_ENABLED=1
OPENAI_AGENT_REQUIRED=1
OPENAI_AGENT_MODEL=gpt-5.6-terra
OPENAI_API_KEY=...
```

如果 `OPENAI_AGENT_REQUIRED=1` 但没有 Key，`/health` 会返回 503，避免把确定性检索假装成 LLM Agent。

### TMDB_API_TOKEN

canonical catalog 的真实海报补全必填。

```env
TMDB_API_TOKEN=...
```

构建流程会执行：

```bash
python scripts/backfill_real_posters.py --db db/catalog.sqlite3 --strict
```

任何内容没有真实 HTTP(S) poster asset 时，strict build 失败；生成 SVG 不允许进入 canonical catalog。

## 2. 可选联网观点 Secrets

```env
BAIDU_SEARCH_API_KEY=
X_BEARER_TOKEN=
```

没有这些 Key 不影响主推荐，但 Social Evidence 不会伪造实时帖子。

## 3. Render

仓库根目录已经提供 `render.yaml`。

部署后必须验证：

```text
GET /health
```

至少满足：

```json
{
  "ok": true,
  "openai_agent_enabled": true,
  "agent_mode": "openai-responses:gpt-5.6-terra",
  "catalog_quality": {
    "poster_coverage": 1.0
  }
}
```

## 4. GitHub Pages 连接完整后端

静态预览：

```text
https://ddd9977lvyzzz-ops.github.io/ai-scene-search/
```

完整后端部署后，可先用：

```text
https://ddd9977lvyzzz-ops.github.io/ai-scene-search/?api=https://YOUR-BACKEND
```

进行联调。

正式产品建议让 Web UI 与 FastAPI 同域部署，此时 `site/config.js` 会直接使用当前 origin，不需要把 API Key 放在前端。

## 5. 数据源 Attribution

TVmaze public API data 使用需要 attribution。

如果启用 TMDB 数据/图片，应用 Credits / About 区必须遵守 TMDB 官方 attribution 要求，包括官方 TMDB logo 与声明：

> This product uses the TMDB API but is not endorsed or certified by TMDB.

商业化前应重新确认对应数据源的商业许可，不把 portfolio / developer API 许可直接等同于商业许可。

## 6. 上线验收

```text
[ ] /health openai_agent_enabled = true
[ ] agent_mode = openai-responses:gpt-5.6-terra
[ ] poster_coverage = 1.0
[ ] generated posters = 0
[ ] 指定爱奇艺时其他平台结果 = 0
[ ] Filter chips 删除后服务端 Profile 同步
[ ] 登录后收藏可跨页面读取
[ ] “给我点惊喜”不突破 Hard Gate
[ ] Social Evidence 不存在时明确显示无数据，不生成虚假帖子
```
