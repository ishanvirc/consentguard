"""Consent Ledger MCP server (stdio transport).

Exposes the consent ledger as a Model Context Protocol server so ANY MCP client
— the ADK agents, Claude Desktop, Gemini CLI, an IDE — can query consent
evidence through one standard interface. This is the interoperability story:
the ledger outlives any single agent framework.

Run standalone:
    uv run python -m mcp_server.consent_ledger

Example client config (Claude Desktop / Gemini CLI style):
    {
      "mcpServers": {
        "consent-ledger": {
          "command": "uv",
          "args": ["run", "python", "-m", "mcp_server.consent_ledger"],
          "cwd": "<path-to>/consentguard"
        }
      }
    }

SECURITY NOTES:
  * Read-mostly surface: the only write tool is record_unsubscribe, which can
    only ever REDUCE contact permission — a hostile client cannot mint consent.
    There is deliberately NO grant_consent tool on this server; consent is
    only ever written by real capture surfaces (forms, POS), not by agents.
  * Responses carry pseudonymous contact_ids and consent facts — never raw PII.
"""

from __future__ import annotations

import json

from mcp.server.fastmcp import FastMCP

from app import ledger

mcp = FastMCP("consent-ledger")


@mcp.tool()
def get_consent(contact_id: str, channel: str) -> str:
    """Latest consent record for a contact on one channel (channel-specific).

    Args:
        contact_id: pseudonymous contact id, e.g. "c_003".
        channel: "email" or "sms".
    """
    e = ledger.get_consent(contact_id, channel)
    return json.dumps({
        "contact_id": e.contact_id,
        "channel": e.channel,
        "basis": e.basis.value,
        "granted_at": e.granted_at.isoformat() if e.granted_at else None,
        "source": e.source,
        "wording": e.wording,
    })


@mcp.tool()
def get_consent_history(contact_id: str) -> str:
    """Chronological consent trail for a contact across all channels."""
    return json.dumps(ledger.get_consent_history(contact_id))


@mcp.tool()
def record_unsubscribe(contact_id: str, channel: str) -> str:
    """Record a consent withdrawal (honored immediately; CASL allows 10 business days)."""
    return json.dumps(ledger.record_unsubscribe(contact_id, channel))


@mcp.tool()
def get_audit_trail(limit: int = 50) -> str:
    """Recent gate decisions and consent events from the append-only audit log."""
    return json.dumps(ledger.get_audit_trail(limit))


if __name__ == "__main__":
    mcp.run(transport="stdio")
