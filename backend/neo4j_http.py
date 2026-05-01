"""
HTTP-based Neo4j client using the Query API v2 (port 443).
Used when Bolt (port 7687) is blocked by firewall/ISP.
Recreates the httpx client on timeout to handle connection drops.
"""

import time

import httpx
from config import settings

TIMEOUT = httpx.Timeout(60.0, connect=30.0)


class Neo4jHTTPClient:
    def __init__(self):
        self.url = settings.neo4j_query_url
        self.auth = (settings.neo4j_username, settings.neo4j_password)

    def _new_client(self):
        return httpx.Client(auth=self.auth, timeout=TIMEOUT)

    def run(self, cypher: str, parameters: dict = None, retries: int = 3) -> list[dict]:
        payload = {"statement": cypher, "parameters": parameters or {}}
        last_exc = None

        for attempt in range(retries):
            try:
                with self._new_client() as client:
                    resp = client.post(
                        self.url,
                        json=payload,
                        headers={"Content-Type": "application/json"},
                    )
                resp.raise_for_status()
                data = resp.json()

                if "errors" in data and data["errors"]:
                    raise Exception(f"Neo4j error: {data['errors']}")

                rows = []
                results = data.get("data", {}).get("values", [])
                keys = data.get("data", {}).get("fields", [])
                for row in results:
                    rows.append(dict(zip(keys, row)))
                return rows

            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ConnectError) as e:
                last_exc = e
                wait = 2 ** attempt
                print(f"\n  Connection error (attempt {attempt + 1}/{retries}), retrying in {wait}s...")
                time.sleep(wait)

        raise last_exc

    def verify_connectivity(self):
        result = self.run("RETURN 1 AS n")
        assert result[0]["n"] == 1
        return True
