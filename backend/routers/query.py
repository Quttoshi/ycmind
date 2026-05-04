import json
import logging
import re
import time
from dataclasses import dataclass

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

from models import Citation, GraphContext, QueryRequest, QueryResponse
from services.hybrid_retriever import HybridRetriever
from services.llm_service import LLMService

router = APIRouter()
logger = logging.getLogger(__name__)

# ── In-memory query cache ─────────────────────────────────────────────────────

@dataclass
class _CachedResult:
    answer: str
    citations: list[Citation]
    graph_context: GraphContext
    method: str

_cache: dict[tuple, _CachedResult] = {}
_MAX_CACHE = 128


def _cache_key(question: str, top_k: int) -> tuple:
    return (question.strip().lower(), top_k)


def _cache_get(question: str, top_k: int) -> _CachedResult | None:
    return _cache.get(_cache_key(question, top_k))


def _cache_set(question: str, top_k: int, result: _CachedResult):
    if len(_cache) >= _MAX_CACHE:
        _cache.pop(next(iter(_cache)))  # evict oldest
    _cache[_cache_key(question, top_k)] = result


# ── Off-topic guard ───────────────────────────────────────────────────────────

_OFF_TOPIC_MSG = "I can only answer questions about Y Combinator companies and founders. Try asking about a specific company, batch, sector, or founder."

_GREETINGS = re.compile(
    r"^(hi|hello|hey|howdy|sup|what'?s up|good (morning|afternoon|evening)|thanks?|thank you|bye|goodbye)[\s!?.]*$",
    re.IGNORECASE,
)


def _is_off_topic(question: str) -> bool:
    q = question.strip()
    if len(q) < 8:
        return True
    if _GREETINGS.match(q):
        return True
    return False


def _off_topic_stream():
    yield f"data: {json.dumps({'type': 'token', 'content': _OFF_TOPIC_MSG})}\n\n"
    yield f"data: {json.dumps({'type': 'done', 'retrieval_method': 'none', 'latency_ms': 0, 'nodes': [], 'edges': [], 'citations': []})}\n\n"


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse)
async def query(request: Request, body: QueryRequest):
    start = time.monotonic()
    try:
        if _is_off_topic(body.question):
            return QueryResponse(
                answer=_OFF_TOPIC_MSG,
                citations=[],
                graph_context=GraphContext(nodes=[], edges=[]),
                retrieval_method="vector",
                latency_ms=0,
            )

        cached = _cache_get(body.question, body.top_k)
        if cached:
            logger.info("Cache hit for query: %s", body.question[:60])
            return QueryResponse(
                answer=cached.answer,
                citations=cached.citations,
                graph_context=cached.graph_context,
                retrieval_method=cached.method,
                latency_ms=int((time.monotonic() - start) * 1000),
            )

        retriever = HybridRetriever(
            neo4j_client=request.app.state.neo4j_client,
            pinecone_index=request.app.state.pinecone_index,
            openai_client=request.app.state.openai_client,
        )
        llm = LLMService(openai_client=request.app.state.openai_client)

        graph_context, vector_matches, method = retriever.retrieve(body.question, body.top_k)
        answer, citations = llm.synthesize(body.question, graph_context, vector_matches)

        _cache_set(body.question, body.top_k, _CachedResult(answer, citations, graph_context, method))

        return QueryResponse(
            answer=answer,
            citations=citations,
            graph_context=graph_context,
            retrieval_method=method,
            latency_ms=int((time.monotonic() - start) * 1000),
        )
    except Exception:
        logger.exception("Query failed")
        return JSONResponse(status_code=500, content={"detail": "Failed to process query"})


@router.post("/query/stream")
def query_stream(request: Request, body: QueryRequest):
    start = time.monotonic()

    if _is_off_topic(body.question):
        return StreamingResponse(
            _off_topic_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    cached = _cache_get(body.question, body.top_k)
    if cached:
        logger.info("Cache hit (stream) for query: %s", body.question[:60])

        def cached_stream():
            # Replay cached answer in one chunk so it feels instant
            yield f"data: {json.dumps({'type': 'token', 'content': cached.answer})}\n\n"
            done = {
                "type": "done",
                "retrieval_method": cached.method,
                "latency_ms": int((time.monotonic() - start) * 1000),
                "nodes": [{"id": n.id, "label": n.label, "properties": n.properties} for n in cached.graph_context.nodes],
                "edges": [{"source": e.source, "target": e.target, "relationship": e.relationship} for e in cached.graph_context.edges],
                "citations": [],
            }
            yield f"data: {json.dumps(done)}\n\n"

        return StreamingResponse(
            cached_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    retriever = HybridRetriever(
        neo4j_client=request.app.state.neo4j_client,
        pinecone_index=request.app.state.pinecone_index,
        openai_client=request.app.state.openai_client,
    )
    llm = LLMService(openai_client=request.app.state.openai_client)

    try:
        graph_context, vector_matches, method = retriever.retrieve(body.question, body.top_k)
    except Exception:
        logger.exception("Retrieval failed")
        def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Retrieval failed'})}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    def event_generator():
        tokens = []
        try:
            for token in llm.synthesize_stream(body.question, graph_context, vector_matches):
                tokens.append(token)
                yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
        except Exception:
            logger.exception("LLM streaming failed")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Answer generation failed'})}\n\n"
            return

        # Cache the completed answer
        full_answer = "".join(tokens)
        _cache_set(body.question, body.top_k, _CachedResult(full_answer, [], graph_context, method))

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
