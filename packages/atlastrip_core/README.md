# atlastrip-core

The only code the seven services have in common. It is installed into every
virtualenv and contains no agent logic at all.

| Module | What it is |
|---|---|
| `models.py` | The wire contract. Every `DataPart` exchanged between agents validates against one of these pydantic models. |
| `registry.py` | The network directory: who is on it, on which port, advertising which skill. The whole topology on one screen. |
| `a2a_support.py` | Server side: build an Agent Card, read a request out of a message, mount the routes, put it on a port. |
| `a2a_client.py` | Client side: one call to a peer, and the fold of its event stream into a single reply. |
| `mcp_http.py` | A dependency-free MCP client, written against the wire format. About 150 lines. |
| `db.py` | Postgres, including the A2A task store. |
| `documents.py` | TinyDB, for the policy clauses and the audit trail. |
| `audit.py` | The append-only trace of every A2A exchange. |
| `config.py` | One settings object, read from the repository root `.env`. |
| `schema.sql` | The operational schema, dropped and recreated on every seed. |

The agents share this and nothing else. They cannot import each other, and
their dependency trees are mutually unsatisfiable on purpose.
