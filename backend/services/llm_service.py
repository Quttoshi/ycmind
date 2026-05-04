import json
import logging
import os

from openai import OpenAI

logger = logging.getLogger(__name__)
from pydantic import BaseModel

from models import Citation, GraphContext

SYSTEM_PROMPT = """You are an expert analyst of Y Combinator companies and founders.

You will be given a user question plus graph and vector context about YC companies.

IMPORTANT: You MUST write in plain flowing prose only. NEVER use bullet points, numbered lists, dashes, or any markdown list syntax. Every response must be one or more paragraphs of natural sentences. Weave company names, batches, and statuses naturally into the text. Keep it to 3–5 sentences unless the question genuinely requires more. If context is insufficient, say so in one sentence.

Graph schema:
- Company nodes: name, batch, status, one_liner, url
- Founder nodes: name, role, university, previous_company
- Relationships: FOUNDED, IN_BATCH, IN_SECTOR"""


class _CitationSchema(BaseModel):
    entity_name: str
    entity_type: str
    relevance: str


class _ResponseSchema(BaseModel):
    answer: str
    citations: list[_CitationSchema]


class LLMService:
    def __init__(self, openai_client: OpenAI):
        self.client = openai_client
        self._setup_langsmith()

    def _setup_langsmith(self):
        api_key = os.getenv("LANGSMITH_API_KEY")
        if api_key:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = api_key
            os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT", "ycmind")

    def _serialize_context(self, graph_context: GraphContext, vector_matches: list[dict]) -> str:
        graph_summary = {
            "nodes": [
                {"label": n.label, "properties": n.properties}
                for n in graph_context.nodes[:30]
            ],
            "edges": [
                {"source": e.source, "target": e.target, "relationship": e.relationship}
                for e in graph_context.edges[:50]
            ],
        }

        vector_summary = [
            {
                "company": m["company_name"],
                "batch": m["batch"],
                "status": m["status"],
                "one_liner": m["one_liner"],
                "sectors": m["sectors"],
                "founders": m["founders"],
                "score": round(m["score"], 3),
            }
            for m in vector_matches[:10]
        ]

        return (
            f"Graph context:\n{json.dumps(graph_summary, indent=2)}\n\n"
            f"Vector search matches:\n{json.dumps(vector_summary, indent=2)}"
        )

    def synthesize(
        self,
        question: str,
        graph_context: GraphContext,
        vector_matches: list[dict],
    ) -> tuple[str, list[Citation]]:
        context = self._serialize_context(graph_context, vector_matches)
        user_message = f"Question: {question}\n\nAnswer in plain prose only — no bullet points, no numbered lists, no dashes. Just natural sentences.\n\n{context}"

        try:
            resp = self.client.chat.completions.parse(
                model="gpt-4o-mini",
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                response_format=_ResponseSchema,
            )
            parsed = resp.choices[0].message.parsed
            citations = [
                Citation(
                    entity_name=c.entity_name,
                    entity_type=c.entity_type,
                    relevance=c.relevance,
                )
                for c in parsed.citations
            ]
            return parsed.answer, citations
        except Exception as e:
            logger.warning(f"Structured output parsing failed, falling back to plain completion: {e}")
            resp = self.client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=1024,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
            )
            return resp.choices[0].message.content.strip(), []

    def synthesize_stream(
        self,
        question: str,
        graph_context: GraphContext,
        vector_matches: list[dict],
    ):
        context = self._serialize_context(graph_context, vector_matches)
        user_message = f"Question: {question}\n\nAnswer in plain prose only — no bullet points, no numbered lists, no dashes. Just natural sentences.\n\n{context}"

        stream = self.client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            stream=True,
        )
        for chunk in stream:
            content = chunk.choices[0].delta.content
            if content:
                yield content
