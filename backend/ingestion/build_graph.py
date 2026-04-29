"""
Loads cleaned YC company data into Neo4j Aura.
Uses MERGE for all nodes and relationships — fully idempotent, safe to re-run.
"""

import json
import sys
from pathlib import Path

from neo4j import GraphDatabase
from tqdm import tqdm

sys.path.append(str(Path(__file__).parent.parent))
from config import settings

DATA_DIR = Path(__file__).parent.parent.parent / "data"
BATCH_SIZE = 100


class GraphBuilder:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_username, settings.neo4j_password),
        )

    def close(self):
        self.driver.close()

    def create_schema(self):
        print("Creating schema (constraints + indexes)...")
        constraints = [
            "CREATE CONSTRAINT company_name IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT batch_name IF NOT EXISTS FOR (b:Batch) REQUIRE b.name IS UNIQUE",
            "CREATE CONSTRAINT sector_name IF NOT EXISTS FOR (s:Sector) REQUIRE s.name IS UNIQUE",
            "CREATE CONSTRAINT founder_id IF NOT EXISTS FOR (f:Founder) REQUIRE f.id IS UNIQUE",
        ]
        indexes = [
            "CREATE INDEX company_batch IF NOT EXISTS FOR (c:Company) ON (c.batch)",
            "CREATE INDEX company_status IF NOT EXISTS FOR (c:Company) ON (c.status)",
        ]
        with self.driver.session() as session:
            for stmt in constraints + indexes:
                session.run(stmt)
        print("  Schema ready.")

    def upsert_batches(self, companies: list[dict]):
        print("Upserting Batch nodes...")
        batches = {}
        for c in companies:
            b = c.get("batch", "")
            if b and b not in batches:
                season = "Winter" if b.startswith("W") else "Summer"
                year_short = b[1:]
                year = int("20" + year_short) if int(year_short) < 50 else int("19" + year_short)
                batches[b] = {"name": b, "season": season, "year": year}

        batch_list = list(batches.values())
        with self.driver.session() as session:
            session.run(
                """
                UNWIND $batches AS b
                MERGE (batch:Batch {name: b.name})
                SET batch.season = b.season, batch.year = b.year
                """,
                batches=batch_list,
            )
        print(f"  {len(batch_list)} batches upserted.")

    def upsert_sectors(self, companies: list[dict]):
        print("Upserting Sector nodes...")
        sectors = set()
        for c in companies:
            for s in c.get("sectors", []):
                if s:
                    sectors.add(s)

        sector_list = [{"name": s} for s in sectors]
        with self.driver.session() as session:
            session.run(
                """
                UNWIND $sectors AS s
                MERGE (sector:Sector {name: s.name})
                """,
                sectors=sector_list,
            )
        print(f"  {len(sector_list)} sectors upserted.")

    def upsert_companies(self, companies: list[dict]):
        print("Upserting Company nodes...")
        for i in tqdm(range(0, len(companies), BATCH_SIZE)):
            batch = companies[i : i + BATCH_SIZE]
            with self.driver.session() as session:
                session.run(
                    """
                    UNWIND $companies AS c
                    MERGE (company:Company {name: c.name})
                    SET company.slug        = c.slug,
                        company.one_liner   = c.one_liner,
                        company.description = c.description,
                        company.batch       = c.batch,
                        company.status      = c.status,
                        company.url         = c.url,
                        company.logo_url    = c.logo_url,
                        company.founded_year = c.founded_year
                    """,
                    companies=batch,
                )
        print(f"  {len(companies)} companies upserted.")

    def upsert_founders(self, companies: list[dict]):
        print("Upserting Founder nodes...")
        founders = {}
        for c in companies:
            for f in c.get("founders", []):
                if not f["name"]:
                    continue
                fid = f"{f['name']}::{c['slug']}"
                founders[fid] = {
                    "id": fid,
                    "name": f["name"],
                    "role": f.get("role", ""),
                    "linkedin_url": f.get("linkedin_url", ""),
                    "university": f.get("university", ""),
                    "previous_company": f.get("previous_company", ""),
                    "company_name": c["name"],
                }

        founder_list = list(founders.values())
        for i in tqdm(range(0, len(founder_list), BATCH_SIZE)):
            batch = founder_list[i : i + BATCH_SIZE]
            with self.driver.session() as session:
                session.run(
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
                    founders=batch,
                )
        print(f"  {len(founder_list)} founders upserted.")

    def create_company_relationships(self, companies: list[dict]):
        print("Creating Company->Batch and Company->Sector relationships...")
        for i in tqdm(range(0, len(companies), BATCH_SIZE)):
            batch = companies[i : i + BATCH_SIZE]
            with self.driver.session() as session:
                # Company -> Batch
                session.run(
                    """
                    UNWIND $companies AS c
                    MATCH (company:Company {name: c.name})
                    WHERE c.batch <> ''
                    MATCH (batch:Batch {name: c.batch})
                    MERGE (company)-[:IN_BATCH]->(batch)
                    """,
                    companies=batch,
                )
                # Company -> Sector
                session.run(
                    """
                    UNWIND $companies AS c
                    MATCH (company:Company {name: c.name})
                    UNWIND c.sectors AS sector_name
                    MATCH (sector:Sector {name: sector_name})
                    MERGE (company)-[:IN_SECTOR]->(sector)
                    """,
                    companies=batch,
                )
        print("  Relationships created.")

    def run(self):
        cleaned_path = DATA_DIR / "cleaned.json"
        if not cleaned_path.exists():
            print(f"ERROR: {cleaned_path} not found. Run scrape_yc.py first.")
            sys.exit(1)

        companies = json.loads(cleaned_path.read_text())
        print(f"Loaded {len(companies)} companies from {cleaned_path}\n")

        try:
            self.create_schema()
            self.upsert_batches(companies)
            self.upsert_sectors(companies)
            self.upsert_companies(companies)
            self.upsert_founders(companies)
            self.create_company_relationships(companies)
            print("\nGraph build complete!")
        finally:
            self.close()


if __name__ == "__main__":
    GraphBuilder().run()
