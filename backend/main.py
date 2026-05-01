from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
from pinecone import Pinecone

from config import settings
from neo4j_http import Neo4jHTTPClient
from routers import graph, query


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.neo4j_client = Neo4jHTTPClient()
    pc = Pinecone(api_key=settings.pinecone_api_key)
    app.state.pinecone_index = pc.Index(settings.pinecone_index_name)
    app.state.openai_client = OpenAI(api_key=settings.openai_api_key)
    yield


app = FastAPI(title="ycmind API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ycmind.vercel.app",
        "https://*.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(query.router)
app.include_router(graph.router)


@app.get("/health")
async def health():
    try:
        app.state.neo4j_client.verify_connectivity()
        return {"status": "ok", "neo4j": "connected", "llm": "openai/gpt-4o-mini"}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": str(e)},
        )
