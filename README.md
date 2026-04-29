# ycmind

> Ask complex questions about YC companies and founders that search engines can't answer.

**Live demo:** [ycmind.vercel.app](https://ycmind.vercel.app) &nbsp;|&nbsp; **Backend:** [ycmind-api.railway.app](https://ycmind-api.railway.app)

---

## What is this?

ycmind is a production GraphRAG (Graph Retrieval-Augmented Generation) system built over the Y Combinator company directory. It combines a **Neo4j knowledge graph** with **Pinecone vector search** to answer multi-hop relational questions that simple keyword or semantic search cannot handle.

**Example queries:**

- *"Which YC fintech founders previously worked at Goldman Sachs and whose companies have since been acquired?"*
- *"Find all W23 batch companies in the DevTools sector whose founders studied at Stanford"*
- *"Which YC companies compete with Airbnb and what are their founding stories?"*

These questions require traversing relationships across multiple entities — exactly what GraphRAG is designed for.

---

## Why GraphRAG over naive RAG?

Standard RAG chunks documents and retrieves the most semantically similar chunks to a query. This breaks down when the answer requires **connecting information across multiple entities**.

| | Naive RAG | GraphRAG (ycmind) |
|---|---|---|
| Query type | Single-hop, semantic | Multi-hop, relational |
| Retrieval method | Vector similarity | Graph traversal + vector search |
| Multi-entity reasoning | Poor | Strong |
| Citation quality | Chunk-level | Entity + relationship level |

---

## Architecture

```
User Query
    ↓
Next.js Frontend (Vercel)
    ↓
FastAPI Backend (Railway)
    ↓
┌─────────────────────────┐
│     Hybrid Retriever    │
│                         │
│  Neo4j Aura  + Pinecone │
│  (graph)       (vector) │
└────────────┬────────────┘
             ↓
     Claude Sonnet (LLM)
             ↓
  Cited answer + graph viz
```

---

## Graph schema

**Node types**

| Node | Key properties |
|---|---|
| `Company` | name, batch, status, description, url, founded_year, valuation |
| `Founder` | name, role, linkedin_url, previous_company, university |
| `Batch` | name, year, season, num_companies |
| `Sector` | name, parent_sector |
| `University` | name, country, ranking |

**Relationships**

```
(Founder)  -[:FOUNDED]->       (Company)
(Founder)  -[:STUDIED_AT]->    (University)
(Founder)  -[:PREVIOUSLY_AT]-> (Company)
(Company)  -[:IN_BATCH]->      (Batch)
(Company)  -[:IN_SECTOR]->     (Sector)
(Company)  -[:ACQUIRED_BY]->   (Company)
(Company)  -[:COMPETES_WITH]-> (Company)
(Sector)   -[:PARENT_OF]->     (Sector)
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, Tailwind CSS, React Force Graph |
| Backend | FastAPI, Python 3.11 |
| Graph DB | Neo4j Aura (free tier) |
| Vector DB | Pinecone |
| Embeddings | OpenAI text-embedding-3-small |
| LLM | Claude Sonnet (Anthropic) |
| Observability | LangSmith |
| Frontend deploy | Vercel |
| Backend deploy | Railway |

---

## Project structure

```
ycmind/
├── frontend/                  # Next.js app
│   ├── app/
│   ├── components/
│   │   ├── SearchBar.tsx
│   │   ├── AnswerPanel.tsx
│   │   ├── GraphViewer.tsx
│   │   └── CompanyCard.tsx
│   └── lib/api.ts
│
├── backend/                   # FastAPI app
│   ├── main.py
│   ├── routers/
│   │   ├── query.py           # POST /query
│   │   └── graph.py           # GET /graph
│   ├── services/
│   │   ├── graph_retriever.py
│   │   ├── vector_retriever.py
│   │   ├── hybrid_retriever.py
│   │   └── llm_service.py
│   └── ingestion/
│       ├── scrape_yc.py
│       ├── build_graph.py
│       └── build_vectors.py
│
├── evals/                     # Benchmark suite
│   ├── questions.json
│   ├── run_eval.py
│   └── results/
│
└── README.md
```

---

## Getting started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Neo4j Aura account (free) — [console.neo4j.io](https://console.neo4j.io)
- Pinecone account (free) — [pinecone.io](https://pinecone.io)
- Anthropic API key — [console.anthropic.com](https://console.anthropic.com)
- OpenAI API key — [platform.openai.com](https://platform.openai.com)

### 1. Clone the repo

```bash
git clone https://github.com/yourusername/ycmind.git
cd ycmind
```

### 2. Set up the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in your keys:

```env
NEO4J_URI=neo4j+s://xxxxxxxx.databases.neo4j.io
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=your-password
PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX_NAME=ycmind
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

### 3. Run the ingestion pipeline

```bash
# Step 1: scrape YC directory
python ingestion/scrape_yc.py

# Step 2: build the knowledge graph in Neo4j
python ingestion/build_graph.py

# Step 3: embed company descriptions into Pinecone
python ingestion/build_vectors.py
```

### 4. Start the backend

```bash
uvicorn main:app --reload
# API running at http://localhost:8000
```

### 5. Set up the frontend

```bash
cd ../frontend
npm install
```

Create `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

```bash
npm run dev
# Frontend running at http://localhost:3000
```

---

## API reference

### `POST /query`

Submit a natural language question and receive a cited answer.

**Request**
```json
{
  "question": "Which W21 founders previously worked at Stripe?",
  "top_k": 5
}
```

**Response**
```json
{
  "answer": "Based on the knowledge graph...",
  "citations": [...],
  "graph_context": {
    "nodes": [...],
    "edges": [...]
  },
  "retrieval_method": "hybrid"
}
```

### `GET /graph?entity={name}`

Returns the subgraph around a specific entity for visualization.

---

## Evaluation

ycmind includes a benchmark suite comparing GraphRAG vs naive RAG on 20 hand-crafted multi-hop questions.

```bash
cd evals
python run_eval.py
```

Results are saved to `evals/results/` with per-question accuracy, hallucination rate, and answer completeness scores.

---

## Deployment

### Backend (Railway)

1. Push the `backend/` folder to a GitHub repo
2. Create a new Railway project and connect the repo
3. Add all environment variables in Railway dashboard
4. Railway auto-detects the `Dockerfile` and deploys

### Frontend (Vercel)

1. Push the `frontend/` folder to a GitHub repo
2. Import the repo in Vercel
3. Set `NEXT_PUBLIC_API_URL` to your Railway backend URL
4. Vercel auto-detects Next.js and deploys

---

## Roadmap

- [ ] Add SEC filings as a second data source
- [ ] Founder social graph (co-founders across companies)
- [ ] Time-series view of batch growth by sector
- [ ] Natural language to Cypher query translator
- [ ] Slack bot integration

---

## License

MIT
