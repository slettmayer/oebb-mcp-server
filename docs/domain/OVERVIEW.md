# Domain Overview

## Purpose
Documents the business domain, core concepts, feature boundaries, terminology, and external integrations.

## Responsibilities
- Defining core domain concepts and their relationships
- Mapping feature boundaries and data ownership
- Maintaining the domain terminology glossary
- Documenting external integrations

## Non-Responsibilities
- Technical architecture and module layout (see [../tech/ARCHITECTURE.md](../tech/ARCHITECTURE.md))
- API response parsing implementation (see source in `src/oebb_mcp_server/oebb_api.py`)

## Overview

### Domain Classification
Read-only MCP gateway between LLMs and OeBB (Austrian Federal Railways) live train data. Enables AI assistants to query Austrian train stations, departure/arrival boards, route connections, and service disruptions.

Industry: public transport / developer tooling (AI integration).

### Core Concepts

**Station** -- A physical rail stop in the Austrian network.
- Key fields: `name`, `station_id`/`extId` (numeric identifier, e.g. "1190100"), `lid` (HAFAS location ID string `A=1@L={id}@`), `type`, `latitude`, `longitude`
- Returned by station search; used as input to all other queries

**Journey** -- A single train service on a station board.
- Key fields: `product` (e.g. "RJ 162"), `direction`, `time_planned`, `time_real` (nullable), `platform`

**Connection** -- A complete travel option between two stations, potentially multi-leg.
- Key fields: `departure`, `arrival`, `departure_real`, `arrival_real`, `duration`, `changes`, `legs`

**Leg** -- One segment of a Connection on a single train service.
- Key fields: `product`, `direction`, `from_station`, `to_station`, `departure`, `arrival`

**ServiceAlert** -- An active disruption or operational notice from OeBB HIM.
- Key fields: `id` (e.g. "HIM_12345"), `headline`, `text`, `priority`, `start_date`, `end_date`, `from_station`, `to_station`

**Product** -- Train service type, represented as a bitmask.
- 1=ICE/RJX, 2=IC/EC, 4=NJ, 8=D/EN, 16=REX/R, 32=S-Bahn, 64=Bus, 128=Ferry, 256=U-Bahn, 512=Tram

### Feature Boundaries

| Feature | MCP Tool | API Function | Owns | Depends On |
|---------|----------|-------------|------|------------|
| Station Search | `search_station` | `async_oebb_search_station` | Location lookup, name matching | Nothing |
| Station Board | `station_board` | `async_oebb_station_board` | Live departures/arrivals | Station Search (name resolution) |
| Trip Search | `trip_search` | `async_oebb_trip_search` | Route planning, connections | Station Search (both endpoints) |
| Service Alerts | `service_alerts` | `async_oebb_service_alerts` | Disruption information | Nothing |

Station Search acts as a dependency resolver: when other tools receive a station name instead of an ID, they call `_async_resolve_station` -> `_async_loc_match` to resolve it first.

### Terminology Glossary

| Term | Definition |
|------|-----------|
| **MCP** | Model Context Protocol -- the protocol by which LLMs invoke tools in this server (stdio transport) |
| **OeBB** | Osterreichische Bundesbahnen -- Austrian Federal Railways |
| **Scotty API** | Informal name for the OeBB journey-planning backend at `fahrplan.oebb.at` |
| **HAFAS** | HaCon Fahrplan-Auskunfts-System -- European public transport routing engine/API protocol used by OeBB |
| **mgate.exe** | The OeBB API endpoint path; a HAFAS gateway |
| **extId** | External/public OeBB station identifier (numeric string) |
| **lid** | HAFAS structured station reference string, e.g. `A=1@L=1190100@` |
| **HIM** | Hafas Information Manager -- subsystem for service disruption messages |
| **prodX** | Zero-based index into shared `prodL` product list in HAFAS responses |
| **outFrwd** | HAFAS boolean: `true` = depart after time, `false` = arrive before time |

### External Integrations

**OeBB Scotty API (HAFAS)** -- sole external integration.
- Endpoint: `https://fahrplan.oebb.at/bin/mgate.exe`
- Purpose: live station search, departure/arrival boards, trip routing, service disruptions
- Auth: hardcoded AID token
- Format: proprietary JSON-RPC-like envelope (`svcReqL`/`svcResL`)
- Status: reverse-engineered, no official documentation

### Compliance
None. Read-only server, no user data stored, no payment processing, no PII handling. All data is publicly available train timetable and disruption information.

## Dependencies
- OeBB Scotty API is the sole external data source
- No internal domain dependencies between features (except Station Search as resolver)

## Design Decisions
- **No domain model objects**: data represented as plain dicts. Appropriate for a thin gateway that transforms API responses without business logic.
- **No caching**: all data fetched live per request. Correct for real-time transit data where staleness is unacceptable.
- **Name resolution on demand**: station names are resolved to IDs per call rather than maintaining a local station database.

## Known Risks
- OeBB API is reverse-engineered -- any field, method, or envelope change breaks the server without warning.
- No rate limiting or circuit breaker on outbound API calls.
- HAFAS terminology (`prodX`, `lid`, `svcReqL`) creates a learning curve for new contributors.

## Extension Guidelines
- New domain features: add a new MCP tool in `server.py` + corresponding `async_oebb_*()` in `oebb_api.py`
- New HAFAS methods: follow the existing request envelope pattern in `_build_request_body`
- Update this glossary when introducing new HAFAS or OeBB-specific terms
