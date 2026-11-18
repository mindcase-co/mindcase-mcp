---
name: mindcase
description: Pull structured web data (LinkedIn, Instagram, TikTok, YouTube, X, Reddit, Google Maps, Amazon, Blinkit/Zepto/Instamart, G2/Trustpilot/Glassdoor reviews, job boards, SEC filings and more) through the Mindcase API. Use when the user wants rows of real data from a website or platform, such as leads, profiles, posts, reviews, prices, listings or jobs, instead of a hand-written scraper.
---

# Mindcase web data

Mindcase is one REST API with 249 ready-made data APIs. Each returns clean JSON rows. Pricing is per row, and failed runs are free.

## Setup

Needs `MINDCASE_API_KEY` (`mk_live_...`, from https://console.mindcase.co). If the Mindcase MCP server is connected (tools `list_agents`, `get_agent_schema`, `run_agent`), use those tools instead of curl.

## Workflow

1. **Find the API.** The catalog is public, no key needed:
   `curl -s https://api.mindcase.co/v1/data/all` and match on `group`, `slug`, `name`, `description`. Paths look like `linkedin/profiles`, `google-maps/places`, `amazon/reviews`.
2. **Read its schema** before running: `curl -s https://api.mindcase.co/v1/data/{group}/{slug}`.
   - `parameters`: the only keys you may send. Enum values are in each parameter's `options`.
   - `sample_input`: a working example (drop any key not in `parameters`).
   - `output_schema[].apiField`: the key each row is returned under.
3. **Set the row limit.** Most APIs take `maxResults`, `maxItems`, `limit` or similar. Cost is rows x `price_per_record`, so cap it at what the user needs, and tell the user the expected cost for big runs.
4. **Run it** in one request:

```bash
curl -s -X POST "https://api.mindcase.co/v1/data/google-maps/places/run?wait=true" \
  -H "Authorization: Bearer $MINDCASE_API_KEY" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{"params": {"keywords": "dental clinic", "location": "Austin, Texas", "maxResults": 20}}'
```

The response has `status`, `row_count` and `data` (the rows, first 100 inline).

5. **Long or large runs.** If the response says `"status": "running"` (60s ceiling) or `"truncated": true`, poll `GET /v1/jobs/{job_id}` every few seconds until `status` is `completed`, then read `GET /v1/jobs/{job_id}/results`. Terminal states are `completed`, `failed`, `cancelled` and `rejected_balance`; stop polling on any of them.

## Errors

Errors look like `{"error": {"code", "message", "retryable", "request_id"}}`. Branch on `code`.
- `401`: bad key, ask the user for a valid one.
- `402` or `rejected_balance`: wallet empty, the user tops up at https://console.mindcase.co/account?tab=billing.
- `422 invalid_params`: the message lists the allowed parameters. Fix and retry; nothing was charged.
- `429`: wait for `Retry-After`.
- A failed run with `retryable: true` can be retried with the same `Idempotency-Key`, which never double-charges.

Balance: `GET /v1/balance` returns `usd_remaining`. Full reference: https://mindcase.co/skills.md
