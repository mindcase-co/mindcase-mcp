import json

import httpx
import pytest
import respx

from mindcase_mcp import server

API = "https://api.mindcase.co/v1"
CATALOG = {"agents": [
    {"group": "linkedin", "slug": "profiles", "name": "LinkedIn Profiles API", "description": "profiles", "price_per_record": 0.004, "unit": "profiles"},
    {"group": "amazon", "slug": "reviews", "name": "Amazon Reviews API", "description": "reviews", "price_per_record": 0.001, "unit": "reviews"},
]}


@pytest.fixture(autouse=True)
def key(monkeypatch):
    monkeypatch.setenv("MINDCASE_API_KEY", "mk_live_test")
    monkeypatch.setattr(server.asyncio, "sleep", _nosleep)


async def _nosleep(_):
    return None


@respx.mock
async def test_list_agents_filters_and_needs_no_key(monkeypatch):
    monkeypatch.delenv("MINDCASE_API_KEY")
    route = respx.get(f"{API}/data/all").respond(json=CATALOG)
    out = json.loads(await server.list_agents(search="review"))
    assert [a["path"] for a in out["agents"]] == ["amazon/reviews"]
    assert "authorization" not in route.calls[0].request.headers


@respx.mock
async def test_schema_drops_example_keys_that_are_not_parameters():
    respx.get(f"{API}/data/linkedin/profiles").respond(json={
        "group": "linkedin", "slug": "profiles", "parameters": {"queries": {"type": "array", "required": False}},
        "sample_input": {"queries": ["x"], "internal": 1}, "output_schema": [{"name": "Full Name", "apiField": "fullName"}]})
    out = json.loads(await server.get_agent_schema("linkedin/profiles"))
    assert out["example"] == {"queries": ["x"]} and out["output_fields"] == ["fullName"]


@respx.mock
async def test_run_inline_rows_with_idempotency_key():
    route = respx.post(f"{API}/data/linkedin/profiles/run").respond(json={
        "job_id": "j1", "status": "completed", "truncated": False, "usd_charged": 0.004, "data": [{"fullName": "A"}]})
    out = json.loads(await server.run_agent("linkedin/profiles", {"queries": ["x"]}))
    req = route.calls[0].request
    assert out["ok"] and out["data"] == [{"fullName": "A"}]
    assert req.url.params["wait"] == "true" and req.headers["idempotency-key"]
    assert json.loads(req.content) == {"params": {"queries": ["x"]}}


@respx.mock
async def test_run_polls_then_pages_large_results():
    respx.post(f"{API}/data/a/b/run").respond(json={"job_id": "j2", "status": "running"})
    respx.get(f"{API}/jobs/j2").mock(side_effect=[httpx.Response(200, json={"status": "running"}),
                                                  httpx.Response(200, json={"status": "completed"})])
    respx.get(f"{API}/jobs/j2/results").respond(json={"data": [{"i": i} for i in range(250)]})
    out = json.loads(await server.run_agent("a/b", {}))
    assert out["row_count"] == 250 and len(out["data"]) == 100 and "fetch_results" in out["note"]


@respx.mock
async def test_failed_run_and_error_envelope():
    respx.post(f"{API}/data/a/b/run").respond(json={"job_id": "j3", "status": "rejected_balance",
                                                    "message": "Top up", "error_code": "insufficient_balance"})
    out = json.loads(await server.run_agent("a/b", {}))
    assert not out["ok"] and out["status"] == "rejected_balance" and out["code"] == "insufficient_balance"

    respx.post(f"{API}/data/a/c/run").respond(422, json={"error": {
        "code": "invalid_params", "message": "Unknown parameters: bogus", "request_id": "req_1", "retryable": False}})
    out = json.loads(await server.run_agent("a/c", {"bogus": 1}))
    assert out == {"ok": False, "error": "Unknown parameters: bogus", "code": "invalid_params",
                   "retryable": False, "request_id": "req_1"}


async def test_paid_tools_explain_missing_key(monkeypatch):
    monkeypatch.delenv("MINDCASE_API_KEY")
    out = json.loads(await server.get_balance())
    assert out["code"] == "missing_api_key"


async def test_bad_agent_path():
    out = json.loads(await server.run_agent("linkedin", {}))
    assert out["code"] == "invalid_agent_path"
