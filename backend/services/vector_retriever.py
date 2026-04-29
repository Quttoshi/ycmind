from openai import OpenAI
from pinecone import Index

EMBED_MODEL = "text-embedding-3-small"


class VectorRetriever:
    def __init__(self, index: Index, openai_client: OpenAI):
        self.index = index
        self.openai_client = openai_client

    def embed(self, text: str) -> list[float]:
        resp = self.openai_client.embeddings.create(model=EMBED_MODEL, input=[text])
        return resp.data[0].embedding

    def retrieve(self, question: str, top_k: int = 5, filter: dict | None = None) -> list[dict]:
        vector = self.embed(question)
        kwargs = {
            "vector": vector,
            "top_k": top_k,
            "include_metadata": True,
            "namespace": "companies",
        }
        if filter:
            kwargs["filter"] = filter

        result = self.index.query(**kwargs)
        matches = []
        for m in result.matches:
            matches.append({
                "score": m.score,
                "company_name": m.metadata.get("name", ""),
                "slug": m.metadata.get("slug", ""),
                "batch": m.metadata.get("batch", ""),
                "status": m.metadata.get("status", ""),
                "sectors": m.metadata.get("sectors", []),
                "url": m.metadata.get("url", ""),
                "one_liner": m.metadata.get("one_liner", ""),
                "founders": m.metadata.get("founders", []),
            })
        return matches
