"""Version handshake with the Athena backend.

This client is installed on the user's own machine and updates on their
schedule, so it can be older or newer than the deployment it points at.
The backend advertises two integers on /health: the contract it speaks
now, and the oldest client contract it still supports. Comparing them
once at startup is what turns "a tool stopped working" into a sentence
the user can act on.

CONTRACT.md lists what the number covers and when it moves.
"""

# Raise this together with the backend's MCP_CONTRACT_VERSION whenever
# this client starts relying on an API change.
CONTRACT_VERSION = 1


def refusal(health: dict, api_url: str) -> str | None:
    """Why this client must not run against the deployment `health`
    describes, or None when it may.

    A deployment that advertises no contract at all predates the
    handshake (or isn't Athena); there is nothing to compare, so say
    nothing and let the tools speak for themselves.
    """
    minimum = health.get("mcp_contract_min")
    if not isinstance(minimum, int) or CONTRACT_VERSION >= minimum:
        return None
    return (
        f"This athena-mcp speaks API contract {CONTRACT_VERSION}, but the server "
        f"at {api_url} no longer supports anything below {minimum}.\n\n"
        "Update it and restart your assistant:\n\n"
        "  uvx --refresh --from git+https://github.com/eksubin/Athena athena-mcp"
    )


def warning(health: dict) -> str | None:
    """A note for the user when the server is behind this client — the
    tools mostly work, but anything this version added may not be there
    yet. Not fatal: a user who updated early should still be able to work.
    """
    current = health.get("mcp_contract")
    if not isinstance(current, int) or current >= CONTRACT_VERSION:
        return None
    return (
        f"This athena-mcp expects API contract {CONTRACT_VERSION}; the server speaks "
        f"{current}. Older server: newer tools may fail until it is updated."
    )
