"""The handshake that keeps separately-installed MCP clients honest.

athena-mcp ships from its own repository, so these two numbers are the
only thing standing between a backend change and ten tools failing on
someone else's machine. See app/core/contract.py.
"""

from app.api.routes import health
from app.core.contract import MCP_CONTRACT_MIN, MCP_CONTRACT_VERSION


def test_health_advertises_the_contract_a_client_can_check():
    body = health.health()
    assert body["status"] == "ok"
    assert body["mcp_contract"] == MCP_CONTRACT_VERSION
    assert body["mcp_contract_min"] == MCP_CONTRACT_MIN


def test_the_oldest_supported_client_is_not_newer_than_the_contract():
    """A minimum above the current contract would refuse every client,
    including one built from this very commit."""
    assert MCP_CONTRACT_MIN <= MCP_CONTRACT_VERSION
