# Travel Inventory MCP server

One Model Context Protocol server holding every tool that touches AtlasTrip's
data. All four specialist agents connect to it over streamable HTTP, each
through its own framework's MCP client.

```bash
mcp_servers/travel_inventory/.venv/bin/python -m travel_inventory_mcp
# http://127.0.0.1:8100/mcp
```

| Tool | Returns |
|---|---|
| `search_flights` | Bookable fares for a city pair on one local departure date |
| `search_hotels` | Rooms in a city, with distance to a customer site |
| `get_ground_transport` | Airport transfer options |
| `lookup_employee` | Grade, passport, cost centre, manager |
| `lookup_venue` | A customer site and its coordinates |
| `get_cost_center_budget` | Allowance, committed, remaining |
| `record_commitment` | Writes money to the ledger |
| `list_airports` | The airports with inventory |

Only `record_commitment` changes anything, and only Ledger calls it.

Because the tools live outside every agent, swapping a framework never means
rewriting a tool. That is the point of the split: MCP gives an agent its tools,
A2A lets agents give each other work.
