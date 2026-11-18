# Mindcase MCP server

[![Tests](https://github.com/mindcase-co/mindcase-mcp/actions/workflows/test.yml/badge.svg)](https://github.com/mindcase-co/mindcase-mcp/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)

Give Claude, Cursor or any MCP client **249 web data APIs** with one API key: LinkedIn, Instagram, TikTok, YouTube, X, Reddit, Google Maps, Amazon, quick-commerce apps, job boards, review sites, SEC filings and more. Every API returns clean, structured JSON rows, and you pay per row.

Ask your agent things like:

- *"Find 50 dental clinics in Austin on Google Maps that have no website."*
- *"Pull the last 200 Trustpilot reviews for notion.so and group the complaints."*
- *"Get the LinkedIn profiles of everyone who reacted to this post."*
- *"Compare Blinkit and Zepto prices for Amul butter in Bangalore."*

## Connect

Get an API key at [console.mindcase.co](https://console.mindcase.co).

### Hosted (recommended, nothing to install)

Add a remote MCP server with URL `https://mcp.mindcase.co` and header `Authorization: Bearer mk_live_...`.

```bash
# Claude Code
claude mcp add --transport http mindcase https://mcp.mindcase.co --header "Authorization: Bearer mk_live_..."
```

### Local (stdio, from this repo)

Needs [uv](https://docs.astral.sh/uv/).

```bash
# Claude Code
claude mcp add mindcase -e MINDCASE_API_KEY=mk_live_... -- uvx --from git+https://github.com/mindcase-co/mindcase-mcp mindcase-mcp
```

Claude Desktop, Cursor, Windsurf or VS Code, in your MCP config:

```json
{
  "mcpServers": {
    "mindcase": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/mindcase-co/mindcase-mcp", "mindcase-mcp"],
      "env": { "MINDCASE_API_KEY": "mk_live_..." }
    }
  }
}
```

## Tools

Five fixed tools, so your agent's context stays small however big the catalog gets.

| Tool | What it does | Costs money |
|---|---|---|
| `list_agents(search, group)` | Find an API by keyword or platform. Returns path, description and price per row. | No, and no key needed |
| `get_agent_schema(agent)` | Parameters, output fields and a ready-to-run example for one API. | No, and no key needed |
| `run_agent(agent, params)` | Runs the API and returns the rows (first 100 inline). | Yes, rows x price |
| `fetch_results(job_id, offset, limit)` | Pages through a finished run, or checks on a long one. | No |
| `get_balance()` | Your wallet balance in USD. | No |

Runs that fail are not charged. Every run is sent with an `Idempotency-Key`, so a retried request never starts a second paid run.

## What's in the catalog

| Area | APIs |
|---|---|
| **LinkedIn** | [profiles](https://mindcase.co/api/linkedin/profiles), [companies](https://mindcase.co/api/linkedin/companies), company employees, [jobs](https://mindcase.co/api/linkedin/jobs), posts, post reactions and comments, work emails, ads library |
| **Social** | Instagram, TikTok, Facebook, YouTube, X, Threads, Reddit, Telegram, Bluesky: profiles, posts, comments, followers, hashtags, stories, ads, trends |
| **Google** | [Maps places](https://mindcase.co/api/google-maps/places) and reviews, search, news, shopping, images, Play Store |
| **E-commerce** | [Amazon](https://mindcase.co/api/amazon/products), eBay (incl. sold listings), AliExpress, Walmart, Best Buy, Home Depot, StockX, ASOS, TikTok Shop |
| **Quick commerce (India)** | [Blinkit](https://mindcase.co/api/blinkit/products), [Zepto](https://mindcase.co/api/zepto/products), [Swiggy Instamart](https://mindcase.co/api/instamart/products), BigBasket, Flipkart Minutes, Amazon Now |
| **Reviews** | G2, Capterra, Trustpilot, Glassdoor, Yelp, TripAdvisor, App Store, Booking, Airbnb |
| **People and companies** | enrichment, work and personal email finders, phone lookup, domain lookup, tech stack, [YC founders](https://mindcase.co/api/ycombinator/founders) |
| **Jobs** | LinkedIn, Indeed, Glassdoor, Upwork, Internshala, H1B salaries |
| **Finance** | SEC filings and insider trades, Yahoo Finance, crypto, customs shipment records |
| **Web and AI** | scrape, crawl, map, extract, backlinks, site traffic, AI assistant answers with citations |

Full list with prices: [mindcase.co/api](https://mindcase.co/api).

## Not using MCP?

It's a plain REST API. The full agent-readable reference is at [mindcase.co/skills.md](https://mindcase.co/skills.md), and the docs are at [docs.mindcase.co](https://docs.mindcase.co).

## Development

```bash
uv venv && uv pip install -e ".[test]"
uv run --no-project pytest -q
MINDCASE_API_KEY=mk_live_... uv run --no-project mindcase-mcp   # stdio
```

Environment: `MINDCASE_API_KEY` (required for paid tools), `MINDCASE_BASE_URL` (default `https://api.mindcase.co/v1`), `MINDCASE_RUN_TIMEOUT` seconds (default 600).

## License

MIT
