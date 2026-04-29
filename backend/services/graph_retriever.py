"""
Intent classifier + Cypher template engine.
Classifies the user question into one of ~10 intent templates, extracts parameters,
then executes the matching Cypher query against Neo4j.
More reliable than end-to-end NL->Cypher generation.
"""

import json
import re

from anthropic import Anthropic
from neo4j import Driver

from models import GraphContext, GraphEdge, GraphNode

INTENT_TEMPLATES = {
    "founders_by_batch_and_sector": {
        "description": "Find founders in a specific YC batch and sector",
        "params": ["batch", "sector"],
        "cypher": """
            MATCH (f:Founder)-[:FOUNDED]->(c:Company)-[:IN_BATCH]->(b:Batch)
            MATCH (c)-[:IN_SECTOR]->(s:Sector)
            WHERE b.name = $batch AND toLower(s.name) CONTAINS toLower($sector)
            RETURN f, c, b, s
            LIMIT $limit
        """,
    },
    "founders_by_previous_company": {
        "description": "Find YC founders who previously worked at a specific company",
        "params": ["company_name"],
        "cypher": """
            MATCH (f:Founder)-[:FOUNDED]->(c:Company)
            WHERE toLower(f.previous_company) CONTAINS toLower($company_name)
            RETURN f, c
            LIMIT $limit
        """,
    },
    "companies_by_batch": {
        "description": "List all companies in a specific YC batch",
        "params": ["batch"],
        "cypher": """
            MATCH (c:Company)-[:IN_BATCH]->(b:Batch {name: $batch})
            OPTIONAL MATCH (f:Founder)-[:FOUNDED]->(c)
            RETURN c, b, f
            LIMIT $limit
        """,
    },
    "companies_by_sector": {
        "description": "Find YC companies in a specific sector or industry",
        "params": ["sector"],
        "cypher": """
            MATCH (c:Company)-[:IN_SECTOR]->(s:Sector)
            WHERE toLower(s.name) CONTAINS toLower($sector)
            OPTIONAL MATCH (f:Founder)-[:FOUNDED]->(c)
            RETURN c, s, f
            LIMIT $limit
        """,
    },
    "acquired_companies": {
        "description": "Find YC companies that have been acquired",
        "params": [],
        "cypher": """
            MATCH (c:Company)
            WHERE c.status = 'Acquired'
            OPTIONAL MATCH (f:Founder)-[:FOUNDED]->(c)
            RETURN c, f
            LIMIT $limit
        """,
    },
    "founders_by_university": {
        "description": "Find YC founders who studied at a specific university",
        "params": ["university"],
        "cypher": """
            MATCH (f:Founder)-[:FOUNDED]->(c:Company)
            WHERE toLower(f.university) CONTAINS toLower($university)
            RETURN f, c
            LIMIT $limit
        """,
    },
    "company_details": {
        "description": "Get details about a specific YC company",
        "params": ["company_name"],
        "cypher": """
            MATCH (c:Company)
            WHERE toLower(c.name) CONTAINS toLower($company_name)
            OPTIONAL MATCH (f:Founder)-[:FOUNDED]->(c)
            OPTIONAL MATCH (c)-[:IN_BATCH]->(b:Batch)
            OPTIONAL MATCH (c)-[:IN_SECTOR]->(s:Sector)
            RETURN c, f, b, s
            LIMIT $limit
        """,
    },
    "companies_by_batch_and_sector": {
        "description": "Find companies in a specific batch and sector combination",
        "params": ["batch", "sector"],
        "cypher": """
            MATCH (c:Company)-[:IN_BATCH]->(b:Batch {name: $batch})
            MATCH (c)-[:IN_SECTOR]->(s:Sector)
            WHERE toLower(s.name) CONTAINS toLower($sector)
            OPTIONAL MATCH (f:Founder)-[:FOUNDED]->(c)
            RETURN c, b, s, f
            LIMIT $limit
        """,
    },
    "general_search": {
        "description": "General search across companies and founders by keyword",
        "params": ["keyword"],
        "cypher": """
            MATCH (c:Company)
            WHERE toLower(c.name) CONTAINS toLower($keyword)
               OR toLower(c.one_liner) CONTAINS toLower($keyword)
               OR toLower(c.description) CONTAINS toLower($keyword)
            OPTIONAL MATCH (f:Founder)-[:FOUNDED]->(c)
            OPTIONAL MATCH (c)-[:IN_BATCH]->(b:Batch)
            OPTIONAL MATCH (c)-[:IN_SECTOR]->(s:Sector)
            RETURN c, f, b, s
            LIMIT $limit
        """,
    },
}

CLASSIFY_PROMPT = """You are a query classifier for a YC company knowledge graph.

Given a user question, identify which intent template best matches and extract the required parameters.

Available intents:
{intents}

User question: {question}

Respond with JSON only:
{{
  "intent": "<intent_name>",
  "params": {{
    "<param>": "<value>"
  }}
}}

Rules:
- Batch format is like "W23", "S21", "W24" (season letter + 2-digit year)
- If no specific intent matches well, use "general_search" with a keyword
- Extract exact values mentioned in the question
- If a parameter is not mentioned, omit it from params"""


def node_to_dict(node) -> dict:
    props = dict(node)
    props["_labels"] = list(node.labels)
    return props


def get_node_label(node) -> str:
    labels = list(node.labels)
    return labels[0] if labels else "Unknown"


class GraphRetriever:
    def __init__(self, driver: Driver, anthropic_client: Anthropic):
        self.driver = driver
        self.anthropic_client = anthropic_client

    def classify_intent(self, question: str) -> tuple[str, dict]:
        intents_desc = "\n".join(
            f"- {name}: {tmpl['description']} (params: {tmpl['params']})"
            for name, tmpl in INTENT_TEMPLATES.items()
        )
        prompt = CLASSIFY_PROMPT.format(intents=intents_desc, question=question)

        resp = self.anthropic_client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()

        # Extract JSON from response
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if not json_match:
            return "general_search", {"keyword": question[:50]}

        try:
            parsed = json.loads(json_match.group())
            intent = parsed.get("intent", "general_search")
            params = parsed.get("params", {})
            if intent not in INTENT_TEMPLATES:
                intent = "general_search"
                params = {"keyword": question[:50]}
            return intent, params
        except json.JSONDecodeError:
            return "general_search", {"keyword": question[:50]}

    def execute(self, intent: str, params: dict, top_k: int) -> list[dict]:
        template = INTENT_TEMPLATES[intent]
        cypher = template["cypher"]
        params["limit"] = top_k * 3  # over-fetch, dedup later

        with self.driver.session() as session:
            result = session.run(cypher, **params)
            return [dict(record) for record in result]

    def format_results(self, records: list[dict]) -> GraphContext:
        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        for record in records:
            for key, value in record.items():
                if value is None:
                    continue

                # Handle Neo4j Node objects
                if hasattr(value, "labels"):
                    label = get_node_label(value)
                    props = node_to_dict(value)
                    node_id = str(value.element_id)
                    name = props.get("name", node_id)

                    if node_id not in nodes:
                        nodes[node_id] = GraphNode(
                            id=node_id,
                            label=label,
                            properties=props,
                        )

                # Handle Neo4j Relationship objects
                elif hasattr(value, "type"):
                    start_id = str(value.start_node.element_id)
                    end_id = str(value.end_node.element_id)
                    edges.append(GraphEdge(
                        source=start_id,
                        target=end_id,
                        relationship=value.type,
                    ))

        return GraphContext(nodes=list(nodes.values()), edges=edges)

    def retrieve(self, question: str, top_k: int = 5) -> tuple[GraphContext, str]:
        intent, params = self.classify_intent(question)
        records = self.execute(intent, params, top_k)
        context = self.format_results(records)
        return context, intent
