import time

from fastapi import APIRouter, Request

from models import QueryRequest, QueryResponse
from services.hybrid_retriever import HybridRetriever
from services.llm_service import LLMService

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(request: Request, body: QueryRequest):
    start = time.monotonic()

    retriever = HybridRetriever(
        driver=request.app.state.neo4j_driver,
        pinecone_index=request.app.state.pinecone_index,
        openai_client=request.app.state.openai_client,
        anthropic_client=request.app.state.anthropic_client,
    )
    llm = LLMService(anthropic_client=request.app.state.anthropic_client)

    graph_context, vector_matches, method = retriever.retrieve(body.question, body.top_k)
    answer, citations = llm.synthesize(body.question, graph_context, vector_matches)

    return QueryResponse(
        answer=answer,
        citations=citations,
        graph_context=graph_context,
        retrieval_method=method,
        latency_ms=int((time.monotonic() - start) * 1000),
    )
