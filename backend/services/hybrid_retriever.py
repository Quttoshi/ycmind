"""
Reciprocal Rank Fusion (RRF) over graph and vector results.
Falls back to vector-only if graph retrieval returns nothing.
"""

from collections import defaultdict

from anthropic import Anthropic
from neo4j import Driver
from openai import OpenAI
from pinecone import Index

from models import GraphContext, GraphEdge, GraphNode
from services.graph_retriever import GraphRetriever
from services.vector_retriever import VectorRetriever


def rrf_score(rank: int, k: int = 60) -> float:
    return 1.0 / (k + rank)


class HybridRetriever:
    def __init__(
        self,
        driver: Driver,
        pinecone_index: Index,
        openai_client: OpenAI,
        anthropic_client: Anthropic,
    ):
        self.graph = GraphRetriever(driver, anthropic_client)
        self.vector = VectorRetriever(pinecone_index, openai_client)

    def retrieve(self, question: str, top_k: int = 5) -> tuple[GraphContext, list[dict], str]:
        graph_context, intent = self.graph.retrieve(question, top_k)
        vector_matches = self.vector.retrieve(question, top_k)

        has_graph = bool(graph_context.nodes)
        has_vector = bool(vector_matches)

        if has_graph and has_vector:
            method = "hybrid"
        elif has_graph:
            method = "graph"
        else:
            method = "vector"

        # Merge graph node names and vector match names for RRF scoring
        scores: dict[str, float] = defaultdict(float)

        graph_names = [
            node.properties.get("name", node.id)
            for node in graph_context.nodes
            if node.label == "Company"
        ]
        for i, name in enumerate(graph_names):
            scores[name] += rrf_score(i)

        for i, match in enumerate(vector_matches):
            scores[match["company_name"]] += rrf_score(i)

        # Re-rank vector matches by RRF score
        vector_matches.sort(
            key=lambda m: scores.get(m["company_name"], 0),
            reverse=True,
        )

        return graph_context, vector_matches, method
