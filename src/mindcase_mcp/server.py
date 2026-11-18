"""Mindcase MCP server (stdio).

Gives any MCP client (Claude Code, Claude Desktop, Cursor, Windsurf, VS Code,
...) the whole Mindcase catalog of web data APIs through five tools:

    list_agents       find an API by keyword or platform (no key needed)
    get_agent_schema  its parameters, output fields and an example input (no key needed)
    run_agent         run it and get rows back (spends wallet balance)
    fetch_results     page through a finished run's rows
    get_balance       wallet balance in USD

Five fixed tools instead of one tool per API keeps the client's context small
however big the catalog gets. Same tools as the hosted server at
https://mcp.mindcase.co, which needs no install.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Dict, Optional

import httpx
from mcp.server.fastmcp import FastMCP

from mindcase_mcp import __version__

logging.getLogger("httpx").setLevel(logging.WARNING)

API_URL = os.environ.get("MINDCASE_BASE_URL", "https://api.mindcase.co/v1").rstrip("/")
INLINE_ROWS = 100
RUN_TIMEOUT = float(os.environ.get("MINDCASE_RUN_TIMEOUT", "600"))
TERMINAL = ("completed", "failed", "cancelled", "rejected_balance")

mcp = FastMCP(
    "mindcase",
    instructions=(
        "Mindcase is a web data API: 240+ ready-made APIs that return structured JSON rows "
        "from LinkedIn, Instagram, TikTok, YouTube, X, Reddit, Google Maps, Amazon, "
        "quick-commerce apps, job boards, review sites, SEC filings and more. Pricing is per row.\n"
        "Workflow: list_agents(search=...) to find the API, get_agent_schema to read its "
        "parameters, then run_agent. Always set the API's row-limit parameter (maxResults, "
        "maxItems, limit, ...) to what the user actually needs, since cost is rows x price."
    ),
)


class ApiError(Exception):
    def __init__(self, message: str, code: Optional[str] = None, retryable: Optional[bool] = None,
                 request_id: Optional[str] = None):
        super().__init__(message)
        self.message, self.code, self.retryable, self.request_id = message, code, retryable, request_id

    def as_dict(self) -> Dict[str, Any]:
        return {"ok": False, "error": self.message, "code": self.code,
                "retryable": self.retryable, "request_id": self.request_id}


def _api_key() -> Optional[str]:
    return os.environ.get("MINDCASE_API_KEY")


async def _call(method: str, path: str, *, params: Optional[dict] = None, body: Optional[dict] = None,
                auth: bool = True, headers: Optional[dict] = None, timeout: float = 90) -> Dict[str, Any]:
    h = {"User-Agent": f"mindcase-mcp/{__version__}", **(headers or {})}
    if auth:
        key = _api_key()
        if not key:
            raise ApiError("No API key. Set MINDCASE_API_KEY in this server's env. "
                           "Get a key at https://console.mindcase.co", code="missing_api_key")
        h["Authorization"] = f"Bearer {key}"
    elif _api_key():
        h["Authorization"] = f"Bearer {_api_key()}"

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.request(method, f"{API_URL}{path}", params=params, json=body, headers=h)
    try:
        data = r.json()
    except ValueError:
        data = {}
    if r.is_success:
        return data
    err = data.get("error") if isinstance(data.get("error"), dict) else {}
    raise ApiError(err.get("message") or data.get("detail") or r.text or f"HTTP {r.status_code}",
                   code=err.get("code"), retryable=err.get("retryable"),
                   request_id=err.get("request_id") or r.headers.get("x-request-id"))


def _dump(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, default=str)


def _fail(e: Exception) -> str:
    return _dump(e.as_dict() if isinstance(e, ApiError) else {"ok": False, "error": str(e)})


def _split(agent: str) -> str:
    parts = agent.strip("/").split("/", 1)
    if len(parts) != 2 or not all(parts):
        raise ApiError(f"API path must be 'group/slug', e.g. 'linkedin/profiles'; got {agent!r}",
                       code="invalid_agent_path")
    return f"{parts[0]}/{parts[1]}"


@mcp.tool(annotations={"readOnlyHint": True})
async def list_agents(search: Optional[str] = None, group: Optional[str] = None) -> str:
    """Find Mindcase APIs. Returns path, name, description and price per row.

    Args:
        search: Keyword matched against path, name and description, e.g. "reviews", "jobs", "email".
        group: Only one platform, e.g. "linkedin", "amazon", "google-maps".
    """
    try:
        agents = (await _call("GET", "/data/all", auth=False)).get("agents", [])
    except Exception as e:  # noqa: BLE001
        return _fail(e)
    if group:
        agents = [a for a in agents if a.get("group") == group]
    if search:
        q = search.lower()
        agents = [a for a in agents
                  if q in f"{a.get('group')}/{a.get('slug')} {a.get('name')} {a.get('description')}".lower()]
    return _dump({
        "count": len(agents),
        "agents": [{
            "path": f"{a['group']}/{a['slug']}",
            "name": a.get("name"),
            "description": a.get("description"),
            "price_per_row_usd": a.get("price_per_record"),
            "unit": a.get("unit"),
        } for a in agents],
    })


@mcp.tool(annotations={"readOnlyHint": True})
async def get_agent_schema(agent: str) -> str:
    """Parameters, output fields and an example input for one API.

    Args:
        agent: API path as "group/slug", e.g. "linkedin/profiles" or "google-maps/places".
    """
    try:
        d = await _call("GET", f"/data/{_split(agent)}", auth=False)
    except Exception as e:  # noqa: BLE001
        return _fail(e)
    params = d.get("parameters") or {}
    return _dump({
        "path": f"{d.get('group')}/{d.get('slug')}",
        "name": d.get("name"),
        "description": d.get("description"),
        "price_per_row_usd": d.get("price_per_record"),
        "unit": d.get("unit"),
        "parameters": {
            k: {kk: v[kk] for kk in ("type", "required", "description", "default", "options") if v.get(kk) is not None}
            for k, v in params.items()
        },
        "input_rules": d.get("require_one_of_hint") or d.get("inputs_description"),
        "output_fields": [c.get("apiField") or c.get("name") for c in d.get("output_schema") or []],
        "example": {k: v for k, v in (d.get("sample_input") or {}).items() if k in params},
    })


async def _wait(job_id: str) -> Dict[str, Any]:
    start = time.monotonic()
    while time.monotonic() - start < RUN_TIMEOUT:
        job = await _call("GET", f"/jobs/{job_id}")
        if job.get("status") in TERMINAL:
            return job
        await asyncio.sleep(2)
    return {"status": "running", "id": job_id}


@mcp.tool()
async def run_agent(agent: str, params: Dict[str, Any]) -> str:
    """Run an API and return its rows (first 100 inline). This spends wallet balance.

    Args:
        agent: API path as "group/slug", e.g. "linkedin/profiles".
        params: The API's parameters as an object, e.g. {"queries": ["https://www.linkedin.com/in/satyanadella"]}.
    """
    try:
        d = await _call("POST", f"/data/{_split(agent)}/run", params={"wait": "true"},
                        body={"params": params}, headers={"Idempotency-Key": str(uuid.uuid4())})
        job_id = d.get("job_id") or d.get("id")
        if d.get("status") == "completed" and not d.get("truncated"):
            rows = d.get("data") or []
        else:
            if d.get("status") not in TERMINAL:
                d = await _wait(job_id)
            if d.get("status") == "running":
                return _dump({"ok": True, "job_id": job_id, "status": "running",
                              "note": "Still running. Call fetch_results(job_id) later."})
            if d.get("status") != "completed":
                return _dump({"ok": False, "job_id": job_id, "status": d.get("status"),
                              "error": d.get("error") or d.get("message") or d.get("stop_message"),
                              "code": d.get("error_code"), "retryable": d.get("retryable")})
            d = await _call("GET", f"/jobs/{job_id}/results")
            rows = d.get("data") or []
    except Exception as e:  # noqa: BLE001
        return _fail(e)
    out: Dict[str, Any] = {"ok": True, "job_id": job_id, "row_count": len(rows),
                           "usd_charged": d.get("usd_charged")}
    if len(rows) > INLINE_ROWS:
        out["note"] = f"Showing {INLINE_ROWS} of {len(rows)} rows. Use fetch_results(job_id, offset={INLINE_ROWS}) for more."
    if d.get("notice"):
        out["notice"] = d["notice"]
    out["data"] = rows[:INLINE_ROWS]
    return _dump(out)


@mcp.tool(annotations={"readOnlyHint": True})
async def fetch_results(job_id: str, offset: int = 0, limit: int = 100) -> str:
    """Rows of a run, paged. Also checks on a run that was still going when run_agent returned.

    Args:
        job_id: The job_id from run_agent.
        offset: First row to return.
        limit: Rows to return (max 500).
    """
    limit = max(1, min(limit, 500))
    try:
        job = await _call("GET", f"/jobs/{job_id}")
        if job.get("status") != "completed":
            return _dump({"ok": job.get("status") in ("queued", "running"), "job_id": job_id,
                          "status": job.get("status"), "error": job.get("error")})
        rows = (await _call("GET", f"/jobs/{job_id}/results")).get("data") or []
    except Exception as e:  # noqa: BLE001
        return _fail(e)
    page = rows[offset:offset + limit]
    return _dump({"ok": True, "job_id": job_id, "row_count": len(rows), "offset": offset,
                  "returned": len(page), "has_more": offset + limit < len(rows), "data": page})


@mcp.tool(annotations={"readOnlyHint": True})
async def get_balance() -> str:
    """Remaining Mindcase wallet balance in USD."""
    try:
        d = await _call("GET", "/balance")
    except Exception as e:  # noqa: BLE001
        return _fail(e)
    return _dump({"usd_remaining": d.get("usd_remaining"),
                  "top_up": "https://console.mindcase.co/account?tab=billing"})


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
