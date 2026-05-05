# Chem_Agent

ChemIntel API 是一个面向精准化学情报场景的后端 Agent 项目。它的重点不是做一个聊天页面，而是展示一个真实后端系统如何把化合物、靶点、活性数据、文献 RAG、工具调用、Agent 执行轨迹、JWT 鉴权、审计日志和评测流程串成一套可运行、可追踪、可扩展的工程。

## 核心能力

- FastAPI 后端服务，按 `router -> schema -> service -> repository/database` 思路拆分模块。
- SQLAlchemy 2.x async 数据模型，覆盖 tenant、user、role、compound、target、bioactivity、paper、paper chunk、agent run、agent step、tool invocation、audit log。
- 真正的 JWT 登录、刷新和登出流程，密码使用 Argon2 哈希。
- RAG 使用 PostgreSQL + pgvector 作为主检索路径，轻量本地 Hybrid Retriever 作为降级路线。
- RAG 支持 `fast`、`balanced`、`high_recall` profile，其中 `high_recall` 包含 multi-query expansion 与 rerank。
- Agent 采用可控的 workflow 编排方式，而不是不可控的完全自主规划；每一步工具调用都可持久化追踪。
- Tool Executor 支持 Pydantic 参数校验、权限检查、超时控制、调用记录和错误记录。
- 支持 Docker Compose 部署 PostgreSQL、Redis、MinIO、API、worker、migration。
- 提供 RAG 和 Agent 评测脚本，输出 Hit@1、Hit@K、MRR、Citation Precision、平均延迟、P95 延迟等指标。

## 技术栈

- Web 框架：FastAPI
- ORM：SQLAlchemy 2.x async
- 数据库：PostgreSQL
- 向量检索：pgvector
- 缓存/队列：Redis
- 异步任务：Celery
- 对象存储：MinIO / S3 compatible storage
- LLM 接入：EasyAgent EasyLLM 适配层，兼容 OpenAI-style endpoint
- Embedding：本地 deterministic embedding fallback，可替换为远程 embedding endpoint
- 鉴权：JWT access token + refresh token + Argon2 password hash
- 部署：Docker Compose
- 测试：pytest
- 评测：自定义 RAG / Agent eval scripts

## 目录结构

```text
chemintel-api/
├── app/
│   ├── adapters/easyagent/      # EasyAgent / eval adapter
│   ├── core/                    # config, security, exceptions
│   ├── db/                      # SQLAlchemy session, models
│   ├── integrations/            # LLM, embedding, storage clients
│   ├── modules/                 # auth, agents, tools, literature, compounds
│   └── workers/                 # Celery app and task hooks
├── alembic/                     # database migrations
├── data/seeds/                  # demo seed data and eval cases
├── scripts/                     # bootstrap, seed, embedding rebuild, eval
├── tests/                       # unit, integration, eval tests
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## 快速启动

### 1. 准备环境

推荐使用 conda：

```bash
conda create -n chemintel python=3.11 -y
conda activate chemintel
pip install -e ".[dev]"
```

复制配置：

```bash
cp .env.example .env
```

如果使用真实 LLM，把 `.env` 中的 LLM 配置改成你的 OpenAI-compatible endpoint，例如：

```env
LLM_ENABLED=true
LLM_PROVIDER=openai
LLM_MODEL=qwen3.5-9b
LLM_BASE_URL=http://127.0.0.1:5124/v1
LLM_API_KEY=your-key
```

如果只做 RAG 检索评测，可以先关闭 LLM：

```env
LLM_ENABLED=false
```

### 2. 启动基础设施

```bash
docker compose up -d postgres redis minio
```

执行数据库迁移：

```bash
alembic upgrade head
```

创建管理员账号：

```bash
python scripts/bootstrap_admin.py \
  --username admin \
  --password 'AdminPass123!' \
  --email admin@example.com
```

导入种子数据并重建向量：

```bash
python scripts/seed_pubmed_pmc.py
python scripts/rebuild_embeddings.py --tenant-id tenant_demo
```

启动 API：

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

访问 OpenAPI：

```text
http://127.0.0.1:8000/docs
```

## Docker Compose 启动

完整启动：

```bash
docker compose up -d --build
```

查看服务：

```bash
docker compose ps
```

停止服务：

```bash
docker compose down
```

## 认证使用

登录：

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "content-type: application/json" \
  -d '{"username":"admin","password":"AdminPass123!"}'
```

返回中会包含 `access_token` 和 `refresh_token`。后续请求使用：

```bash
Authorization: Bearer <access_token>
```

查看当前用户：

```bash
curl -s http://127.0.0.1:8011/api/v1/auth/me \
  -H "authorization: Bearer <access_token>"
```

刷新 token：

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/refresh \
  -H "content-type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

登出：

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/auth/logout \
  -H "content-type: application/json" \
  -d '{"refresh_token":"<refresh_token>"}'
```

## RAG 如何工作

当前 RAG 主路径是：

```text
用户 query
  -> multi-query expansion
  -> embedding
  -> PostgreSQL pgvector ANN search
  -> lexical score / title score / token overlap boost
  -> rerank
  -> citations
  -> grounded answer
```

如果 `VECTOR_SEARCH_ENABLED=false`，或数据库没有 pgvector embedding，系统会降级到本地 Hybrid Retriever：

```text
PaperChunk 全量读取
  -> TF-IDF / title match / token overlap
  -> heuristic boost
  -> rerank
```

这个 fallback 适合本地 demo 和故障降级，不适合大规模生产检索。真实测试应优先使用 pgvector 路径，并在结果中确认 `retrieval_mode` 是 `pgvector_hybrid`。

默认情况下，RAG 的 multi-query expansion 使用 deterministic chemistry query expansion，不会在检索阶段调用真实 LLM。真实 LLM 默认只用于最终报告生成，避免 LLM endpoint 慢或不可用时拖垮检索链路。如果你要实验 LLM 参与 query expansion，可以显式设置：

```env
RAG_LLM_QUERY_EXPANSION_ENABLED=true
```

## 推荐的的 RAG 测试集

建议分两类找数据：文献文本数据用于 RAG，结构化化学数据用于工具和业务实体。

### 文献 RAG 数据源

1. PMC Open Access Subset

适合做全文 RAG。可以下载开放获取的 PMC 文章，包含 XML、文本和部分 PDF。适合构造几千到几十万 chunk 的测试集。

官方地址：

```text
https://pmc.ncbi.nlm.nih.gov/tools/openftlist/
```

2. PubMed Baseline / Update Files

适合做摘要级 RAG。PubMed 主要提供 title、abstract、MeSH、journal、publication type 等元数据。摘要数据更轻，适合快速扩大到 1k-10k 文档。

官方地址：

```text
https://pubmed.ncbi.nlm.nih.gov/download/
```

3. NCBI E-utilities

适合按关键词小批量拉取数据，例如 EGFR、PARP1、BRAF inhibitor、kinase inhibitor resistance。适合自己构造领域聚焦测试集。

官方文档：

```text
https://www.ncbi.nlm.nih.gov/books/NBK25501/
```

### 结构化化学数据源

1. PubChem

适合补充 compound、CID、synonyms、SMILES、InChIKey、基础性质等信息。

下载页：

```text
https://pubchem.ncbi.nlm.nih.gov/docs/downloads
```

PUG-REST API：

```text
https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
```

2. ChEMBL

适合补充 compound、target、assay、bioactivity 等药物发现相关结构化数据。

官方下载：

```text
https://www.ebi.ac.uk/chembl/downloads
```

3. ChEBI

适合补充化学实体、ontology、同义词、分类关系。

官方下载：

```text
https://www.ebi.ac.uk/chebi/downloadsForward.do
```

## 推荐测试集规模


## 如何把大数据集导入项目

当前项目的种子文献数据格式在：

```text
data/seeds/literature/papers.json
```

你可以把 PubMed / PMC 下载的数据转换成同样结构：

```json
{
  "id": "pap_egfr_0001",
  "title": "EGFR mutations and response to gefitinib in non-small-cell lung cancer",
  "abstract": "....",
  "doi": "10.xxxx/xxxx",
  "pmid": "12345678",
  "pmcid": "PMC123456",
  "source_url": "https://pubmed.ncbi.nlm.nih.gov/12345678/",
  "chunks": [
    {
      "section_title": "abstract",
      "content": "..."
    },
    {
      "section_title": "results",
      "content": "..."
    }
  ]
}
```

导入后执行：

```bash
python scripts/seed_pubmed_pmc.py
python scripts/rebuild_embeddings.py --tenant-id tenant_demo
```

如果数据量较大，不建议一次性写入一个巨大 JSON 文件。更合理的方式是：

- 按主题或年份切分为多个 JSONL 文件。
- 批量 upsert paper 和 paper_chunk。
- embedding 分批重建，例如每批 500-2,000 chunks。
- 对失败批次记录 source_sync_job，支持断点重跑。
- 重建完成后执行 RAG eval，而不是只看 API 是否能返回。

当前项目已经有 `SourceSyncJob` 等数据模型，可以继续扩展成正式的数据导入任务。

## 如何构造自己的 RAG 评测集

评测集文件在：

```text
data/seeds/eval_cases/rag_eval.json
```

每个 case 建议包含：

```json
{
  "case_id": "rag_egfr_001",
  "query": "Which evidence supports gefitinib sensitivity in EGFR-mutant NSCLC?",
  "expected_paper_ids": ["pap_egfr_0001"]
}
```

构造规则：

- query 不要直接复制 chunk 原文，否则指标虚高。
- query 应该像真实用户问题，例如“Which evidence supports...”“What mechanism explains...”
- `expected_paper_ids` 可以有多个，只要命中任意一个相关证据就算召回成功。
- 每个主题至少准备 10-20 个问题，避免只靠少数 case 得到偶然高分。
- 加入 hard cases，例如同一 compound 的不同靶点、同一靶点的不同药物、缩写歧义、同义词问题。
- 加入 negative cases，验证系统在没有证据时是否会降低置信度或说明限制。
## 如何运行 RAG 评测

运行 pgvector 主路径：

```bash
LLM_ENABLED=false python scripts/run_eval.py \
  --suite rag \
  --profile high_recall \
  --k 3
```

运行 fallback 路径，对比 pgvector 和本地检索：

```bash
VECTOR_SEARCH_ENABLED=false LLM_ENABLED=false python scripts/run_eval.py \
  --suite rag \
  --profile high_recall \
  --k 3
```

运行 Agent 评测：

```bash
LLM_ENABLED=false python scripts/run_eval.py --suite agent
```

如果你接入真实 LLM，可以去掉 `LLM_ENABLED=false`：

```bash
python scripts/run_eval.py --suite agent
```

## RAG 指标怎么看

项目评测会关注：

- Hit@1：第一条 citation 是否命中期望文档。
- Hit@K：前 K 条 citation 是否至少有一条命中期望文档。
- MRR：相关文档排名越靠前越高。
- Citation Precision@1：第一条引用是否准确。
- Citation Precision@K：前 K 条引用中相关引用比例。
- Average Latency：平均检索延迟。
- P95 Latency：95 分位延迟，比平均值更能体现稳定性。




## API 示例

### RAG 查询

```bash
curl -s -X POST http://127.0.0.1:8000/api/v1/rag/query \
  -H "content-type: application/json" \
  -H "authorization: Bearer <access_token>" \
  -d '{
    "query": "What evidence links gefitinib to EGFR-mutant NSCLC?",
    "top_k": 3,
    "profile": "high_recall"
  }'
```

返回中应关注：

```json
{
  "answer": "...",
  "citations": [],
  "retrieval_mode": "pgvector_hybrid"
}
```

### Compound Research Agent

```bash
curl -s -X POST http://127.0.0.1:8011/api/v1/agents/compound_research_agent/runs \
  -H "content-type: application/json" \
  -H "authorization: Bearer <access_token>" \
  -d '{
    "input": "Give me a short research brief on Gefitinib and cite evidence."
  }'
```

查询 Agent steps：

```bash
curl -s http://127.0.0.1:8000/api/v1/agents/runs/<run_id>/steps \
  -H "authorization: Bearer <access_token>"
```

## 测试

运行单元、评测和集成测试：

```bash
pytest tests/unit tests/eval tests/integration -q
```

注意：如果测试依赖 PostgreSQL、pgvector 或 Redis，请先启动 Docker Compose 中的基础设施，并确认 `.env` 指向正确数据库。
