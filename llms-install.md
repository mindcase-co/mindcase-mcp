# Installing the Mindcase MCP server

These steps are for an AI agent (Cline, Claude Code, Cursor, etc.) setting up this server for a user.

## 1. Get an API key

Ask the user for their Mindcase API key. It starts with `mk_live_` and comes from https://console.mindcase.co. Browsing the catalog works without a key; running an API needs one.

## 2. Pick a connection

**Option A, hosted (no install).** If the client supports remote MCP servers over Streamable HTTP, add:

- URL: `https://mcp.mindcase.co`
- Header: `Authorization: Bearer <API key>`

**Option B, local (stdio).** Requires `uv` (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`). Add this to the MCP settings file (for Cline: `cline_mcp_settings.json`):

```json
{
  "mcpServers": {
    "mindcase": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/mindcase-co/mindcase-mcp", "mindcase-mcp"],
      "env": { "MINDCASE_API_KEY": "<API key>" },
      "disabled": false,
      "autoApprove": ["list_agents", "get_agent_schema", "get_balance"]
    }
  }
}
```

Leave `run_agent` out of `autoApprove`: it spends the user's balance.

## 3. Verify

Call `get_balance`. A response like `{"usd_remaining": 9.11, ...}` means the key works. Then try `list_agents` with `{"search": "linkedin"}`.

## Troubleshooting

- `missing_api_key`: `MINDCASE_API_KEY` isn't set in the server's `env`.
- `401`: the key is wrong or revoked; ask the user for a new one.
- `uvx: command not found`: install uv (step 2B) or use the hosted option.
