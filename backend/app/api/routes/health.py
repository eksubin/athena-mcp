from fastapi import APIRouter

from app.core.contract import MCP_CONTRACT_MIN, MCP_CONTRACT_VERSION

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Also the version handshake for athena-mcp, which is installed
    separately and may be older or newer than this deployment. See
    app/core/contract.py."""
    return {
        "status": "ok",
        "mcp_contract": MCP_CONTRACT_VERSION,
        "mcp_contract_min": MCP_CONTRACT_MIN,
    }
