"""The API surface athena-mcp depends on, versioned as a single integer.

athena-mcp lives in its own repository and runs on each user's own
machine, so the client talking to this deployment can be any age — people
update on their own schedule, and nothing here can make them. The two
numbers below are the whole handshake: /health advertises them, and the
client refuses to start when it falls outside the range. That turns "a
tool quietly stopped working mid-conversation" into one sentence at
connect time.

Bump MCP_CONTRACT_VERSION whenever an endpoint athena-mcp calls changes
in a way a client could notice: a renamed or removed response field, a
new required request field, a different status code, a moved route. The
list of what counts is CONTRACT.md in the athena-mcp repository, and its
scripts/smoke_test.py is the check.

Raise MCP_CONTRACT_MIN only when you deliberately drop support for older
clients. It breaks every deployed client below it, so raise it with a
release note telling people to update, never as a side effect of a
refactor.
"""

MCP_CONTRACT_VERSION = 1
MCP_CONTRACT_MIN = 1
