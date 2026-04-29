"""
Scrapes YC company directory via Algolia — the same index powering ycombinator.com/companies.
App ID and public search key are intentionally public (read-only, embedded in the YC frontend).
Saves raw data to data/raw.json and cleaned data to data/cleaned.json.
"""

import json
import re
import sys
import time
from pathlib import Path

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from tqdm import tqdm

DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

ALGOLIA_APP_ID = "45BWZJ1SGC"
ALGOLIA_SEARCH_KEY = "be9a4e790ed6f837e6d4af3a4e6e57f4"  # public read-only key from YC frontend
ALGOLIA_URL = f"https://{ALGOLIA_APP_ID}-dsn.algolia.net/1/indexes/*/queries"

HEADERS = {
    "X-Algolia-Application-Id": ALGOLIA_APP_ID,
    "X-Algolia-API-Key": ALGOLIA_SEARCH_KEY,
    "Content-Type": "application/json",
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_page(client: httpx.Client, page: int, hits_per_page: int = 200) -> dict:
    payload = {
        "requests": [
            {
                "indexName": "YCCompany_production",
                "params": f"hitsPerPage={hits_per_page}&page={page}&attributesToRetrieve=objectID,name,slug,one_liner,long_description,batch,status,industries,tags,subindustry,launched_at,website,small_logo_thumb_url,founders&filters=",
            }
        ]
    }
    resp = client.post(ALGOLIA_URL, headers=HEADERS, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_all() -> list[dict]:
    hits = []
    page = 0
    total_pages = 1

    with httpx.Client() as client:
        with tqdm(desc="Scraping YC Algolia", unit="page") as pbar:
            while page < total_pages:
                data = fetch_page(client, page)
                result = data["results"][0]

                if page == 0:
                    total_pages = result["nbPages"]
                    pbar.total = total_pages
                    print(f"\nFound {result['nbHits']} companies across {total_pages} pages")

                hits.extend(result["hits"])
                page += 1
                pbar.update(1)
                time.sleep(0.1)  # polite delay

    return hits


def normalize_batch(batch: str) -> str:
    """Normalize batch strings like 'Winter 2023' -> 'W23', 'S21' stays 'S21'."""
    if not batch:
        return ""
    batch = batch.strip()
    # Already short form: W23, S21, etc.
    if re.match(r"^[WS]\d{2}$", batch):
        return batch
    # Long form: Winter 2023, Summer 2021
    m = re.match(r"(Winter|Summer)\s+(\d{4})", batch, re.IGNORECASE)
    if m:
        season = "W" if m.group(1).lower() == "winter" else "S"
        year = m.group(2)[-2:]
        return f"{season}{year}"
    return batch


def clean_record(hit: dict) -> dict:
    founders = []
    for f in hit.get("founders", []):
        founders.append({
            "name": f"{f.get('first_name', '')} {f.get('last_name', '')}".strip(),
            "role": f.get("title", ""),
            "linkedin_url": f.get("linkedin_url", ""),
        })

    industries = hit.get("industries", []) or []
    tags = hit.get("tags", []) or []
    sectors = list({*industries, *tags})

    launched_at = hit.get("launched_at")
    founded_year = None
    if launched_at:
        try:
            from datetime import datetime, timezone
            founded_year = datetime.fromtimestamp(launched_at, tz=timezone.utc).year
        except Exception:
            pass

    return {
        "id": hit.get("objectID", ""),
        "name": hit.get("name", ""),
        "slug": hit.get("slug", ""),
        "one_liner": hit.get("one_liner", ""),
        "description": hit.get("long_description", ""),
        "batch": normalize_batch(hit.get("batch", "")),
        "status": hit.get("status", "Active"),
        "sectors": sectors,
        "url": hit.get("website", ""),
        "logo_url": hit.get("small_logo_thumb_url", ""),
        "founded_year": founded_year,
        "founders": founders,
    }


def main():
    print("=== YC Algolia Scraper ===")

    raw_path = DATA_DIR / "raw.json"
    cleaned_path = DATA_DIR / "cleaned.json"

    print("Fetching companies from Algolia...")
    raw_hits = fetch_all()

    print(f"\nSaving {len(raw_hits)} raw records to {raw_path}")
    raw_path.write_text(json.dumps(raw_hits, indent=2))

    print("Cleaning records...")
    cleaned = [clean_record(h) for h in raw_hits]

    # Deduplicate by slug
    seen = set()
    deduped = []
    for c in cleaned:
        if c["slug"] not in seen:
            seen.add(c["slug"])
            deduped.append(c)

    print(f"Saving {len(deduped)} cleaned records to {cleaned_path}")
    cleaned_path.write_text(json.dumps(deduped, indent=2))

    print("\nDone!")
    print(f"  Raw:     {raw_path}")
    print(f"  Cleaned: {cleaned_path}")

    # Quick stats
    batches = {c["batch"] for c in deduped if c["batch"]}
    statuses = {}
    for c in deduped:
        statuses[c["status"]] = statuses.get(c["status"], 0) + 1

    print(f"\nStats:")
    print(f"  Total companies: {len(deduped)}")
    print(f"  Batches found:   {len(batches)}")
    print(f"  Status breakdown: {statuses}")


if __name__ == "__main__":
    main()
