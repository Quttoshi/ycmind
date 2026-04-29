from fastapi import APIRouter, Query, Request

from models import GraphContext, GraphEdge, GraphNode
from services.graph_retriever import get_node_label, node_to_dict

router = APIRouter()


@router.get("/graph", response_model=GraphContext)
async def get_subgraph(
    request: Request,
    entity: str = Query(..., description="Entity name to build subgraph around"),
    depth: int = Query(default=2, ge=1, le=3),
):
    cypher = """
        MATCH path = (start)-[*1..$depth]-(neighbor)
        WHERE toLower(start.name) CONTAINS toLower($entity)
        RETURN path
        LIMIT 100
    """
    driver = request.app.state.neo4j_driver
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    with driver.session() as session:
        result = session.run(cypher, entity=entity, depth=depth)
        for record in result:
            path = record["path"]
            for node in path.nodes:
                node_id = str(node.element_id)
                if node_id not in nodes:
                    nodes[node_id] = GraphNode(
                        id=node_id,
                        label=get_node_label(node),
                        properties=node_to_dict(node),
                    )
            for rel in path.relationships:
                edges.append(GraphEdge(
                    source=str(rel.start_node.element_id),
                    target=str(rel.end_node.element_id),
                    relationship=rel.type,
                ))

    return GraphContext(nodes=list(nodes.values()), edges=edges)
