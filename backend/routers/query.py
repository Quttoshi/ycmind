import json
import logging
import time

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from models import QueryRequest, QueryResponse
from services.hybrid_retriever import HybridRetriever
from services.llm_service import LLMService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query", response_model=QueryResponse)
async def query(request: Request, body: QueryRequest):
    start = time.monotonic()
    try:
        retriever = HybridRetriever(
            neo4j_client=request.app.state.neo4j_client,
            pinecone_index=request.app.state.pinecone_index,
            openai_client=request.app.state.openai_client,
        )
        llm = LLMService(openai_client=request.app.state.openai_client)

        graph_context, vector_matches, method = retriever.retrieve(body.question, body.top_k)
        answer, citations = llm.synthesize(body.question, graph_context, vector_matches)

        return QueryResponse(
            answer=answer,
            citations=citations,
            graph_context=graph_context,
            retrieval_method=method,
            latency_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception as e:
        logger.exception("Query failed")
        return JSONResponse(status_code=500, content={"detail": "Failed to process query"})


@router.post("/query/stream")
def query_stream(request: Request, body: QueryRequest):
    start = time.monotonic()

    retriever = HybridRetriever(
        neo4j_client=request.app.state.neo4j_client,
        pinecone_index=request.app.state.pinecone_index,
        openai_client=request.app.state.openai_client,
    )
    llm = LLMService(openai_client=request.app.state.openai_client)

    try:
        graph_context, vector_matches, method = retriever.retrieve(body.question, body.top_k)
    except Exception as e:
        logger.exception("Retrieval failed")
        def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Retrieval failed'})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    def event_generator():
        try:
            for token in llm.synthesize_stream(body.question, graph_context, vector_matches):
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        except Exception as e:
            logger.exception("LLM streaming failed")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Answer generation failed'})}\n\n"
            return

        latency = int((time.monotonic() - start) * 1000)
        done = {
            "type": "done",
            "retrieval_method": method,
            "latency_ms": latency,
            "nodes": [{"id": n.id, "label": n.label, "properties": n.properties} for n in graph_context.nodes],
            "edges": [{"source": e.source, "target": e.target, "relationship": e.relationship} for e in graph_context.edges],
            "citations": [],
        }
        yield f"data: {json.dumps(done)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
