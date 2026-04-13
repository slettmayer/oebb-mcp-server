# oebb-mcp-server

MCP server for [OeBB](https://www.oebb.at) (Austrian Federal Railways) train data. Query Austrian train stations, departures, connections, and service alerts directly from LLMs via the [Model Context Protocol](https://modelcontextprotocol.io).

## Installation

### Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "oebb": {
      "command": "uvx",
      "args": ["oebb-mcp-server"]
    }
  }
}
```

### Claude Code

```bash
claude mcp add oebb -- uvx oebb-mcp-server
```

### From source (development)

```json
{
  "mcpServers": {
    "oebb": {
      "command": "uvx",
      "args": ["--from", "/path/to/oebb-mcp-server", "oebb-mcp-server"]
    }
  }
}
```

## Tools

### `search_station`

Search OeBB stations by name. Returns matching stations with IDs, coordinates, and types.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | string | required | Station name (e.g. "Wien Hbf") |
| `max_results` | int | 10 | Maximum results |

### `station_board`

Fetch live departures or arrivals at a station. Provide either `station_id` or `station_name`.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `station_id` | string | — | OeBB station ID (e.g. "1190100") |
| `station_name` | string | — | Station name (auto-resolved) |
| `board_type` | string | "DEP" | "DEP" for departures, "ARR" for arrivals |
| `max_journeys` | int | 10 | Maximum journeys |

### `trip_search`

Search train connections between two stations. Supports time planning and direct-only filtering.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `from_station_id` | string | — | Departure station ID |
| `from_station_name` | string | — | Departure station name |
| `to_station_id` | string | — | Arrival station ID |
| `to_station_name` | string | — | Arrival station name |
| `max_connections` | int | 5 | Maximum connections |
| `time` | string | now | ISO 8601 time (e.g. "2026-04-15T08:00:00") |
| `time_mode` | string | "departure" | "departure" or "arrival" |
| `direct_only` | bool | false | Only direct connections |

### `service_alerts`

Fetch current OeBB service alerts and disruptions.

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `max_alerts` | int | 20 | Maximum alerts |
| `product_filter` | int | 1023 | Product bitmask (1=ICE/RJX, 2=IC/EC, 4=NJ, 8=D/EN, 16=REX/R, 32=S-Bahn, 64=Bus, 128=Ferry, 256=U-Bahn, 512=Tram, 1023=all) |

## Development

```bash
# Install dependencies
uv sync

# Lint & format
ruff check .
ruff format .

# Run unit tests
pytest tests/ -v -m "not integration"

# Run integration tests (hits real OeBB API)
pytest tests/ -v -m integration
```

## License

MIT
