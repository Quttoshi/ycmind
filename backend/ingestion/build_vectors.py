"""
Embeds YC company descriptions into Pinecone using OpenAI text-embedding-3-small.
Vector ID = company slug so it can be cross-referenced with Neo4j nodes.
"""

import json
import sys
import time
from pathlib import Path

from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent.parent))
from config import settings

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EMBED_MODEL = "text-embedding-3-small"
EMBED_DIM = 1536
BATCH_SIZE = 100


def build_text(company: dict) -> str:
    parts = [
        company.get("name", ""),
        company.get("one_liner", ""),
        company.get("description", ""),
        f"Batch: {company.get('batch', '')}",
        f"Status: {company.get('status', '')}",
        "Founders: " + ", ".join(f["name"] for f in company.get("founders", []) if f.get("name")),
        "Sectors: " + ", ".join(company.get("sectors", [])),
    ]
    return " | ".join(p for p in parts if p.strip())


def embed_batch(client: OpenAI, texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [r.embedding for r in resp.data]


def create_index_if_not_exists(pc: Pinecone):
    existing = [idx.name for idx in pc.list_indexes()]
    if settings.pinecone_index_name not in existing:
        print(f"Creating Pinecone index '{settings.pinecone_index_name}'...")
        pc.create_index(
            name=settings.pinecone_index_name,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        # Wait for index to be ready
        while not pc.describe_index(settings.pinecone_index_name).status["ready"]:
            time.sleep(1)
        print("  Index created.")
    else:
        print(f"Index '{settings.pinecone_index_name}' already exists.")


def main():
    cleaned_path = DATA_DIR / "cleaned.json"
    if not cleaned_path.exists():
        print(f"ERROR: {cleaned_path} not found. Run scrape_yc.py first.")
        sys.exit(1)

    companies = json.loads(cleaned_path.read_text())
    print(f"Loaded {len(companies)} companies\n")

    openai_client = OpenAI(api_key=settings.openai_api_key)
    pc = Pinecone(api_key=settings.pinecone_api_key)

    create_index_if_not_exists(pc)
    index = pc.Index(settings.pinecone_index_name)

    print(f"Embedding and upserting to Pinecone (batch size={BATCH_SIZE})...")
    for i in tqdm(range(0, len(companies), BATCH_SIZE)):
        batch = companies[i : i + BATCH_SIZE]
        texts = [build_text(c) for c in batch]
        embeddings = embed_batch(openai_client, texts)

        vectors = []
        for company, embedding in zip(batch, embeddings):
            vectors.append({
                "id": company["slug"] or company["id"],
                "values": embedding,
                "metadata": {
                    "name": company["name"],
                    "slug": company["slug"],
                    "batch": company["batch"],
                    "status": company["status"],
                    "sectors": company.get("sectors", []),
                    "url": company.get("url", ""),
                    "one_liner": company.get("one_liner", ""),
                    "founders": [f["name"] for f in company.get("founders", []) if f.get("name")],
                },
            })

        index.upsert(vectors=vectors, namespace="companies")
        time.sleep(0.05)  # polite delay

    stats = index.describe_index_stats()
    print(f"\nDone! Pinecone index stats: {stats}")


if __name__ == "__main__":
    main()
