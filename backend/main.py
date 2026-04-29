from contextlib import asynccontextmanager

from anthropic import Anthropic
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from neo4j import GraphDatabase
from openai import OpenAI
from pinecone import Pinecone

from config import settings
from routers import graph, query


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.neo4j_driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_username, settings.neo4j_password),
    )
    pc = Pinecone(api_key=settings.pinecone_api_key)
    app.state.pinecone_index = pc.Index(settings.pinecone_index_name)
    app.state.openai_client = OpenAI(api_key=settings.openai_api_key)
    app.state.anthropic_client = Anthropic(api_key=settings.anthropic_api_key)
    yield
    app.state.neo4j_driver.close()


app = FastAPI(title="ycmind API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://ycmind.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router)
app.include_router(graph.router)


@app.get("/health")
async def health():
    try:
        app.state.neo4j_driver.verify_connectivity()
        return {"status": "ok", "neo4j": "connected"}
    except Exception as e:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "error", "detail": str(e)},
        )
