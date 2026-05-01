"""
Loads cleaned YC company data into Neo4j Aura via HTTP Query API.
Uses UNWIND batching to minimize HTTP requests.
Uses MERGE for all nodes and relationships — fully idempotent, safe to re-run.
"""

import json
import sys
import time
from pathlib import Path

from tqdm import tqdm

sys.path.append(str(Path(__file__).parent.parent))
from neo4j_http import Neo4jHTTPClient

DATA_DIR = Path(__file__).parent.parent.parent / "data"
BATCH_SIZE = 200


class GraphBuilder:
    def __init__(self):
        self.client = Neo4jHTTPClient()

    def create_schema(self):
        print("Creating schema (constraints + indexes)...")
        statements = [
            "CREATE CONSTRAINT company_name IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT batch_name IF NOT EXISTS FOR (b:Batch) REQUIRE b.name IS UNIQUE",
            "CREATE CONSTRAINT sector_name IF NOT EXISTS FOR (s:Sector) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT founder_id IF NOT EXISTS FOR (f:Founder) REQUIRE f.id IS UNIQUE",
            "CREATE INDEX company_batch IF NOT EXISTS FOR (c:Company) ON (c.batch)",
            "CREATE INDEX company_status IF NOT EXISTS FOR (c:Company) ON (c.status)",
        ]
        for stmt in statements:
            self.client.run(stmt)
        print("  Schema ready.")

    def upsert_batches(self, companies: list[dict]):
        print("Upserting Batch nodes...")
        batches = {}
        for c in companies:
            b = c.get("batch", "")
            if b and b not in batches:
                season = "Winter" if b.startswith("W") else "Summer"
                year_short = b[1:]
                try:
                    year = int("20" + year_short) if int(year_short) < 50 else int("19" + year_short)
                except ValueError:
                    year = 0
                batches[b] = {"name": b, "season": season, "year": year}

        batch_list = list(batches.values())
        self.client.run(
            """
            UNWIND $batches AS b
            MERGE (batch:Batch {name: b.name})
            SET batch.season = b.season, batch.year = b.year
            """,
            {"batches": batch_list},
        )
        print(f"  {len(batch_list)} batches upserted.")

    def upsert_sectors(self, companies: list[dict]):
        print("Upserting Sector nodes...")
        sectors = list({s for c in companies for s in c.get("sectors", []) if s})
        sector_list = [{"name": s} for s in sectors]

        self.client.run(
            """
            UNWIND $sectors AS s
            MERGE (sector:Sector {name: s.name})
            """,
            {"sectors": sector_list},
        )
        print(f"  {len(sector_list)} sectors upserted.")

    def upsert_companies(self, companies: list[dict]):
        print("Upserting Company nodes...")
        for i in tqdm(range(0, len(companies), BATCH_SIZE)):
            batch = [
                {
                    "name": c.get("name", ""),
                    "slug": c.get("slug", ""),
                    "one_liner": c.get("one_liner", ""),
                    "description": c.get("description", ""),
                    "batch": c.get("batch", ""),
                    "status": c.get("status", "Active"),
                    "url": c.get("url", ""),
                    "logo_url": c.get("logo_url", ""),
                    "founded_year": c.get("founded_year"),
                }
                for c in companies[i: i + BATCH_SIZE]
            ]
            self.client.run(
                """
                UNWIND $companies AS c
                MERGE (company:Company {name: c.name})
                SET company.slug         = c.slug,
                    company.one_liner    = c.one_liner,
                    company.description  = c.description,
                    company.batch        = c.batch,
                    company.status       = c.status,
                    company.url          = c.url,
                    company.logo_url     = c.logo_url,
                    company.founded_year = c.founded_year
                """,
                {"companies": batch},
            )
            time.sleep(0.2)
        print(f"  {len(companies)} companies upserted.")

    def upsert_founders(self, companies: list[dict]):
        print("Upserting Founder nodes + FOUNDED relationships...")
        founders = []
        for c in companies:
            for f in c.get("founders", []):
                if not f.get("name"):
                    continue
                founders.append({
                    "id": f"{f['name']}::{c['slug']}",
                    "name": f["name"],
                    "role": f.get("role", ""),
                    "linkedin_url": f.get("linkedin_url", ""),
                    "university": f.get("university", ""),
                    "previous_company": f.get("previous_company", ""),
                    "company_name": c["name"],
                })

        for i in tqdm(range(0, len(founders), BATCH_SIZE)):
            batch = founders[i: i + BATCH_SIZE]
            self.client.run(
                """
                UNWIND $founders AS f
                MERGE (founder:Founder {id: f.id})
                SET founder.name             = f.name,
                    founder.role             = f.role,
                    founder.linkedin_url     = f.linkedin_url,
                    founder.university       = f.university,
                    founder.previous_company = f.previous_company
                WITH founder, f
                MATCH (company:Company {name: f.company_name})
                MERGE (founder)-[:FOUNDED]->(company)
                """,
                {"founders": batch},
            )
            time.sleep(0.2)
        print(f"  {len(founders)} founders upserted.")

    def create_relationships(self, companies: list[dict]):
        print("Creating Company->Batch relationships...")
        batch_rels = [
            {"name": c["name"], "batch": c["batch"]}
            for c in companies if c.get("batch")
        ]
        for i in tqdm(range(0, len(batch_rels), BATCH_SIZE)):
            self.client.run(
                """
                UNWIND $rels AS r
                MATCH (c:Company {name: r.name}), (b:Batch {name: r.batch})
                MERGE (c)-[:IN_BATCH]->(b)
                """,
                {"rels": batch_rels[i: i + BATCH_SIZE]},
            )
            time.sleep(0.2)

        print("Creating Company->Sector relationships...")
        sector_rels = [
            {"name": c["name"], "sector": s}
            for c in companies
            for s in c.get("sectors", []) if s
        ]
        for i in tqdm(range(0, len(sector_rels), 50)):
            self.client.run(
                """
                UNWIND $rels AS r
                MATCH (c:Company {name: r.name}), (s:Sector {name: r.sector})
                MERGE (c)-[:IN_SECTOR]->(s)
                """,
                {"rels": sector_rels[i: i + 50]},
            )
            time.sleep(0.5)
        print("  Relationships created.")

    def run(self):
        cleaned_path = DATA_DIR / "cleaned.json"
        if not cleaned_path.exists():
            print(f"ERROR: {cleaned_path} not found. Run scrape_yc.py first.")
            sys.exit(1)

        companies = json.loads(cleaned_path.read_text())
        print(f"Loaded {len(companies)} companies from {cleaned_path}\n")

        self.create_schema()
        self.upsert_batches(companies)
        self.upsert_sectors(companies)
        self.upsert_companies(companies)
        self.upsert_founders(companies)
        self.create_relationships(companies)
        print("\nGraph build complete!")


if __name__ == "__main__":
    GraphBuilder().run()
