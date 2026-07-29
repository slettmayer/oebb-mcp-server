"""MCP server exposing OeBB train data tools."""

from __future__ import annotations

import json
from typing import Any

import aiohttp
from mcp.server import MCPServer

from oebb_mcp_server import __version__
from oebb_mcp_server.const import OEBB_ALL_PRODUCTS
from oebb_mcp_server.oebb_api import (
    async_oebb_search_station,
    async_oebb_service_alerts,
    async_oebb_station_board,
    async_oebb_trip_search,
)

mcp = MCPServer(
    "oebb",
    # v2 advertises this verbatim and defaults it to "" (v1 had no such
    # parameter and reported the SDK's own version instead).
    version=__version__,
    instructions=(
        "OeBB (Austrian Federal Railways) train data server. "
        "Use search_station to find station IDs, station_board for "
        "live departures/arrivals, trip_search for connections between "
        "stations, and service_alerts for current disruptions."
    ),
)


def _format_result(result: dict[str, Any]) -> str:
    """Format an API result dict as JSON string."""
    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def search_station(query: str, max_results: int = 10) -> str:
    """Search OeBB stations by name.

    Use this to find station IDs needed for other tools.
    Returns matching stations with IDs, coordinates, and types.

    Args:
        query: Station name to search for (e.g. "Wien Hbf", "Salzburg")
        max_results: Maximum number of results to return (default 10)
    """
    async with aiohttp.ClientSession() as session:
        result = await async_oebb_search_station(session, query, max_results)
    return _format_result(result)


@mcp.tool()
async def station_board(
    station_id: str | None = None,
    station_name: str | None = None,
    board_type: str = "DEP",
    max_journeys: int = 10,
) -> str:
    """Fetch live departures or arrivals at an OeBB station.

    Provide either station_id or station_name (name is auto-resolved).
    Returns train products, directions, planned/real times, and platforms.

    Args:
        station_id: OeBB station ID (e.g. "1190100" for Wien Hbf)
        station_name: Station name to search for (e.g. "Wien Hbf")
        board_type: "DEP" for departures (default), "ARR" for arrivals
        max_journeys: Maximum number of journeys to return (default 10)
    """
    async with aiohttp.ClientSession() as session:
        result = await async_oebb_station_board(
            session, station_id, station_name, board_type, max_journeys
        )
    return _format_result(result)


@mcp.tool()
async def trip_search(
    from_station_id: str | None = None,
    from_station_name: str | None = None,
    to_station_id: str | None = None,
    to_station_name: str | None = None,
    max_connections: int = 5,
    time: str | None = None,
    time_mode: str = "departure",
    direct_only: bool = False,
) -> str:
    """Search train connections between two OeBB stations.

    Provide station IDs or names for departure and arrival stations.
    Supports future trip planning via time/time_mode parameters.
    Returns connections with departure/arrival times, duration, changes, and legs.

    Args:
        from_station_id: Departure station ID (e.g. "1190100")
        from_station_name: Departure station name (e.g. "Wien Hbf")
        to_station_id: Arrival station ID (e.g. "8100002")
        to_station_name: Arrival station name (e.g. "Salzburg Hbf")
        max_connections: Maximum connections to return (default 5)
        time: ISO 8601 time (e.g. "2026-04-15T08:00:00"), defaults to now
        time_mode: "departure" (default) or "arrival"
        direct_only: Only show direct connections without changes (default false)
    """
    async with aiohttp.ClientSession() as session:
        result = await async_oebb_trip_search(
            session,
            from_station_id,
            from_station_name,
            to_station_id,
            to_station_name,
            max_connections,
            time,
            time_mode,
            direct_only,
        )
    return _format_result(result)


@mcp.tool()
async def service_alerts(
    max_alerts: int = 20,
    product_filter: int = OEBB_ALL_PRODUCTS,
) -> str:
    """Fetch current OeBB service alerts and disruptions.

    Returns active alerts with headlines, descriptions, affected stations,
    and date ranges.

    Args:
        max_alerts: Maximum number of alerts to return (default 20)
        product_filter: Product bitmask — 1=ICE/RJX, 2=IC/EC, 4=NJ,
            8=D/EN, 16=REX/R, 32=S-Bahn, 64=Bus,
            4096=private operators (Westbahn/RegioJet), 65535=all
    """
    async with aiohttp.ClientSession() as session:
        result = await async_oebb_service_alerts(session, max_alerts, product_filter)
    return _format_result(result)


def main() -> None:
    """Run the OeBB MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
