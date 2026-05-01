# Behavioral Guidelines

## 1. Think Before Coding
Don't assume. Don't hide confusion. Surface tradeoffs.

Before implementing:
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them — don't pick silently.
- If a simpler approach exists, say so. Push back when warranted.
- If something is unclear, stop. Name what's confusing. Ask.

## 2. Simplicity First
Minimum code that solves the problem. Nothing speculative.

- No features beyond what was asked.
- No abstractions for single-use code.
- No "flexibility" or "configurability" that wasn't requested.
- No error handling for impossible scenarios.
- If you write 200 lines and it could be 50, rewrite it.

## 3. Surgical Changes
Touch only what you must. Clean up only your own mess.

When editing existing code:
- Don't "improve" adjacent code, comments, or formatting.
- Don't refactor things that aren't broken.
- Match existing style, even if you'd do it differently.
- If you notice unrelated dead code, mention it — don't delete it.

When your changes create orphans:
- Remove imports/variables/functions that YOUR changes made unused.
- Don't remove pre-existing dead code unless asked.

## 4. Goal-Driven Execution
Define success criteria. Loop until verified.

For multi-step tasks, state a brief plan:
1. [Step] → verify: [check]
2. [Step] → verify: [check]

---

# ycmind

GraphRAG system over the Y Combinator company directory. Answers multi-hop relational questions using Neo4j + Pinecone + OpenAI.

## Stack

- **Backend**: FastAPI, Python 3.12, uv
- **Graph DB**: Neo4j Aura Free (HTTP Query API — Bolt port 7687 is blocked, use HTTP only)
- **Vector DB**: Pinecone (index: `ycmind`, namespace: `companies`, dimension: 1536)
- **Embeddings**: OpenAI `text-embedding-3-small`
- **LLM**: OpenAI `gpt-4o-mini`
- **Frontend**: Next.js 14, Tailwind CSS

## Project Structure

```
backend/
  config.py              # pydantic-settings, loads .env
  main.py                # FastAPI app, lifespan startup
  models.py              # Pydantic request/response models
  neo4j_http.py          # HTTP client for Neo4j (replaces Bolt driver)
  ingestion/
    scrape_yc.py         # Algolia scraper (requires --key from DevTools)
    build_graph.py       # Loads companies/founders into Neo4j
    build_vectors.py     # Embeds companies into Pinecone
  services/
    graph_retriever.py   # Intent classifier + Cypher template engine
    vector_retriever.py  # Pinecone semantic search
    hybrid_retriever.py  # RRF fusion of graph + vector results
    llm_service.py       # GPT-4o-mini answer synthesis with citations
  routers/
    query.py             # POST /query
    graph.py             # GET /graph
frontend/
  app/page.tsx           # Single page layout
  components/
    SearchBar.tsx        # Query input + example chips
    AnswerPanel.tsx      # Answer + citations + metadata
    ResultsTable.tsx     # Companies + founders tables
  lib/api.ts             # API client
```

## Environment Variables

```env
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=xxxxxxxx
NEO4J_PASSWORD=your-password
NEO4J_QUERY_URL=https://xxxxxxxx.databases.neo4j.io/db/xxxxxxxx/query/v2

PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX_NAME=ycmind

OPENAI_API_KEY=your-openai-key

LANGSMITH_API_KEY=your-langsmith-key   # optional
LANGSMITH_PROJECT=ycmind
```

## Running Locally

```bash
# Backend
cd backend
uv sync
uv run uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

## Ingestion Pipeline (run once)

```bash
cd backend

# 1. Scrape YC via Algolia (get key from DevTools on ycombinator.com/companies)
uv run python ingestion/scrape_yc.py --key YOUR_ALGOLIA_KEY

# 2. Load into Neo4j
uv run python ingestion/build_graph.py

# 3. Embed into Pinecone
uv run python ingestion/build_vectors.py
```

## Key Decisions

- **Neo4j HTTP API**: Bolt (port 7687) is blocked on the dev machine. All Neo4j calls use the HTTP Query API v2 (port 443) via `neo4j_http.py`. Do not switch back to the Bolt driver.
- **OpenAI only**: Using OpenAI for both LLM (gpt-4o-mini) and embeddings (text-embedding-3-small). No Anthropic dependency.
- **Algolia key**: The public search key rotates — must be grabbed fresh from DevTools each time the scraper is run.
- **Pinecone dimension**: Must be 1536 to match `text-embedding-3-small`. If index exists with wrong dimension, delete and recreate.
- **Idempotent ingestion**: All graph writes use MERGE — safe to re-run build_graph.py without duplicating data.
