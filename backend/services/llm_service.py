"""
Answer synthesis using Claude Sonnet with citations.
Optionally traces to LangSmith when LANGSMITH_API_KEY is set.
"""

import json
import os
import re

from anthropic import Anthropic

from models import Citation, GraphContext

SYSTEM_PROMPT = """You are an expert analyst of Y Combinator companies and founders.

You will be given:
1. A user question
2. Graph context: entities and relationships retrieved from a Neo4j knowledge graph
3. Vector search matches: semantically similar companies

Your job:
- Answer the question using ONLY the provided context
- If the context doesn't contain enough information, say so clearly
- Cite every claim by referencing specific entity names from the context
- Be concise and factual

Graph schema:
- Company nodes: name, batch, status, one_liner, description, url, founded_year
- Founder nodes: name, role, linkedin_url, university, previous_company
- Batch nodes: name, season, year
- Sector nodes: name
- Relationships: FOUNDED, IN_BATCH, IN_SECTOR, STUDIED_AT, PREVIOUSLY_AT, ACQUIRED_BY

Respond with JSON in this exact format:
{
  "answer": "Your detailed answer here using markdown for formatting",
  "citations": [
    {"entity_name": "Company or Founder name", "entity_type": "Company|Founder|Batch|Sector", "relevance": "Why this entity is relevant"}
  ]
}"""


class LLMService:
    def __init__(self, anthropic_client: Anthropic):
        self.client = anthropic_client
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
                for n in graph_context.nodes[:30]  # cap to avoid token overflow
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

        user_message = f"Question: {question}\n\n{context}"

        resp = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw = resp.content[0].text.strip()

        # Extract JSON from response
        json_match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not json_match:
            return raw, []

        try:
            parsed = json.loads(json_match.group())
            answer = parsed.get("answer", raw)
            citations_raw = parsed.get("citations", [])
            citations = [
                Citation(
                    entity_name=c.get("entity_name", ""),
                    entity_type=c.get("entity_type", ""),
                    relevance=c.get("relevance", ""),
                )
                for c in citations_raw
            ]
            return answer, citations
        except json.JSONDecodeError:
            return raw, []
