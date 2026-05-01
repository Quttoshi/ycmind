"""
Intent classifier + Cypher template engine.
Classifies the user question into one of ~10 intent templates, extracts parameters,
then executes the matching Cypher query against Neo4j via HTTP Query API.
"""

import json
import re

from openai import OpenAI

from models import GraphContext, GraphEdge, GraphNode
from neo4j_http import Neo4jHTTPClient

INTENT_TEMPLATES = {
    "founders_by_batch_and_sector": {
        "description": "Find founders in a specific YC batch and sector",
        "params": ["batch", "sector"],
        "cypher": """
            MATCH (f:Founder)-[:FOUNDED]->(c:Company)-[:IN_BATCH]->(b:Batch)
            MATCH (c)-[:IN_SECTOR]->(s:Sector)
            WHERE b.name = $batch AND toLower(s.name) CONTAINS toLower($sector)
            RETURN f.name AS founder_name, f.role AS role, f.linkedin_url AS linkedin,
                   c.name AS company, c.batch AS batch, c.status AS status,
                   c.one_liner AS one_liner, c.url AS url, s.name AS sector
            LIMIT $limit
        """,
    },
    "founders_by_previous_company": {
        "description": "Find YC founders who previously worked at a specific company",
        "params": ["company_name"],
        "cypher": """
            MATCH (f:Founder)-[:FOUNDED]->(c:Company)
            WHERE toLower(f.previous_company) CONTAINS toLower($company_name)
            RETURN f.name AS founder_name, f.role AS role, f.previous_company AS previous_company,
                   c.name AS company, c.batch AS batch, c.status AS status, c.url AS url
            LIMIT $limit
        """,
    },
    "companies_by_batch": {
        "description": "List all companies in a specific YC batch",
        "params": ["batch"],
        "cypher": """
            MATCH (c:Company)-[:IN_BATCH]->(b:Batch {name: $batch})
            OPTIONAL MATCH (f:Founder)-[:FOUNDED]->(c)
            RETURN c.name AS company, c.status AS status, c.one_liner AS one_liner,
                   c.url AS url, b.name AS batch,
                   collect(f.name) AS founders
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
            RETURN c.name AS company, c.batch AS batch, c.status AS status,
                   c.one_liner AS one_liner, c.url AS url, s.name AS sector,
                   collect(f.name) AS founders
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
            RETURN c.name AS company, c.batch AS batch, c.status AS status,
                   c.one_liner AS one_liner, c.url AS url, collect(f.name) AS founders
            LIMIT $limit
        """,
    },
    "founders_by_university": {
        "description": "Find YC founders who studied at a specific university",
        "params": ["university"],
        "cypher": """
            MATCH (f:Founder)-[:FOUNDED]->(c:Company)
            WHERE toLower(f.university) CONTAINS toLower($university)
            RETURN f.name AS founder_name, f.university AS university,
                   c.name AS company, c.batch AS batch, c.url AS url
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
            RETURN c.name AS company, c.batch AS batch, c.status AS status,
                   c.one_liner AS one_liner, c.description AS description,
                   c.url AS url, c.founded_year AS founded_year,
                   collect(DISTINCT f.name) AS founders,
                   collect(DISTINCT s.name) AS sectors
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
            RETURN c.name AS company, c.status AS status, c.one_liner AS one_liner,
                   c.url AS url, b.name AS batch, s.name AS sector,
                   collect(f.name) AS founders
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
            RETURN c.name AS company, c.batch AS batch, c.status AS status,
                   c.one_liner AS one_liner, c.url AS url,
                   collect(DISTINCT f.name) AS founders,
                   collect(DISTINCT s.name) AS sectors
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


class GraphRetriever:
    def __init__(self, neo4j_client: Neo4jHTTPClient, openai_client: OpenAI):
        self.client = neo4j_client
        self.openai_client = openai_client

    def classify_intent(self, question: str) -> tuple[str, dict]:
        intents_desc = "\n".join(
            f"- {name}: {tmpl['description']} (params: {tmpl['params']})"
            for name, tmpl in INTENT_TEMPLATES.items()
        )
        prompt = CLASSIFY_PROMPT.format(intents=intents_desc, question=question)

        resp = self.openai_client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        text = resp.choices[0].message.content.strip()

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
        params["limit"] = top_k * 3
        return self.client.run(cypher, params)

    def format_results(self, records: list[dict]) -> GraphContext:
        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        for i, record in enumerate(records):
            company_name = record.get("company")
            if company_name:
                node_id = f"company_{company_name}"
                if node_id not in nodes:
                    nodes[node_id] = GraphNode(
                        id=node_id,
                        label="Company",
                        properties={
                            "name": company_name,
                            "batch": record.get("batch", ""),
                            "status": record.get("status", ""),
                            "one_liner": record.get("one_liner", ""),
                            "description": record.get("description", ""),
                            "url": record.get("url", ""),
                            "founded_year": record.get("founded_year"),
                            "sectors": record.get("sectors", []),
                        },
                    )

            founder_name = record.get("founder_name")
            if founder_name:
                node_id = f"founder_{founder_name}"
                if node_id not in nodes:
                    nodes[node_id] = GraphNode(
                        id=node_id,
                        label="Founder",
                        properties={
                            "name": founder_name,
                            "role": record.get("role", ""),
                            "linkedin_url": record.get("linkedin", ""),
                            "university": record.get("university", ""),
                            "previous_company": record.get("previous_company", ""),
                        },
                    )
                if company_name:
                    edges.append(GraphEdge(
                        source=f"founder_{founder_name}",
                        target=f"company_{company_name}",
                        relationship="FOUNDED",
                    ))

            # Handle collected founders list
            founders_list = record.get("founders", [])
            if isinstance(founders_list, list):
                for fname in founders_list:
                    if fname:
                        fid = f"founder_{fname}"
                        if fid not in nodes:
                            nodes[fid] = GraphNode(
                                id=fid,
                                label="Founder",
                                properties={"name": fname},
                            )
                        if company_name:
                            edges.append(GraphEdge(
                                source=fid,
                                target=f"company_{company_name}",
                                relationship="FOUNDED",
                            ))

            sector = record.get("sector")
            if sector and company_name:
                sid = f"sector_{sector}"
                if sid not in nodes:
                    nodes[sid] = GraphNode(id=sid, label="Sector", properties={"name": sector})
                edges.append(GraphEdge(
                    source=f"company_{company_name}",
                    target=sid,
                    relationship="IN_SECTOR",
                ))

            batch = record.get("batch")
            if batch and company_name:
                bid = f"batch_{batch}"
                if bid not in nodes:
                    nodes[bid] = GraphNode(id=bid, label="Batch", properties={"name": batch})
                edges.append(GraphEdge(
                    source=f"company_{company_name}",
                    target=bid,
                    relationship="IN_BATCH",
                ))

        return GraphContext(nodes=list(nodes.values()), edges=edges)

    def retrieve(self, question: str, top_k: int = 5) -> tuple[GraphContext, str]:
        intent, params = self.classify_intent(question)
        records = self.execute(intent, params, top_k)
        context = self.format_results(records)
        return context, intent
