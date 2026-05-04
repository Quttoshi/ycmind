import logging

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from models import GraphContext, GraphEdge, GraphNode

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/graph", response_model=GraphContext)
async def get_subgraph(
    request: Request,
    entity: str = Query(..., description="Entity name to build subgraph around"),
    depth: int = Query(default=2, ge=1, le=3),
):
    try:
        client = request.app.state.neo4j_client
        nodes: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        company_records = client.run(
            """
            MATCH (c:Company)
            WHERE toLower(c.name) CONTAINS toLower($entity)
            OPTIONAL MATCH (f:Founder)-[:FOUNDED]->(c)
            OPTIONAL MATCH (c)-[:IN_BATCH]->(b:Batch)
            OPTIONAL MATCH (c)-[:IN_SECTOR]->(s:Sector)
            RETURN c.name AS company, c.batch AS batch, c.status AS status,
                   c.one_liner AS one_liner, c.url AS url,
                   f.name AS founder_name, f.role AS role,
                   b.name AS batch_name, s.name AS sector_name
            LIMIT 50
            """,
            {"entity": entity},
        )

        for record in company_records:
            cname = record.get("company")
            if cname:
                cid = f"company_{cname}"
                if cid not in nodes:
                    nodes[cid] = GraphNode(
                        id=cid,
                        label="Company",
                        properties={
                            "name": cname,
                            "batch": record.get("batch", ""),
                            "status": record.get("status", ""),
                            "one_liner": record.get("one_liner", ""),
                            "url": record.get("url", ""),
                        },
                    )

            fname = record.get("founder_name")
            if fname and cname:
                fid = f"founder_{fname}"
                if fid not in nodes:
                    nodes[fid] = GraphNode(
                        id=fid,
                        label="Founder",
                        properties={"name": fname, "role": record.get("role", "")},
                    )
                edges.append(GraphEdge(source=fid, target=f"company_{cname}", relationship="FOUNDED"))

            batch = record.get("batch_name")
            if batch and cname:
                bid = f"batch_{batch}"
                if bid not in nodes:
                    nodes[bid] = GraphNode(id=bid, label="Batch", properties={"name": batch})
                edges.append(GraphEdge(source=f"company_{cname}", target=bid, relationship="IN_BATCH"))

            sector = record.get("sector_name")
            if sector and cname:
                sid = f"sector_{sector}"
                if sid not in nodes:
                    nodes[sid] = GraphNode(id=sid, label="Sector", properties={"name": sector})
                edges.append(GraphEdge(source=f"company_{cname}", target=sid, relationship="IN_SECTOR"))

        return GraphContext(nodes=list(nodes.values()), edges=edges)

    except Exception:
        logger.exception("Graph query failed")
        return JSONResponse(status_code=500, content={"detail": "Failed to fetch graph"})
