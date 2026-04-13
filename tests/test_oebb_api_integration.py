"""Integration tests for the OeBB API — hits the real OeBB Scotty API.

Run with: pytest tests/ -v -m integration
These tests are excluded from CI.
"""

from __future__ import annotations

import aiohttp
import pytest

from oebb_mcp_server.oebb_api import (
    async_oebb_search_station,
    async_oebb_service_alerts,
    async_oebb_station_board,
    async_oebb_trip_search,
)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_oebb_search_station() -> None:
    """Search for Wien Hbf and verify it appears in results."""
    async with aiohttp.ClientSession() as session:
        result = await async_oebb_search_station(session, "Wien Hbf")

    assert "message" not in result, f"API error: {result.get('message')}"
    assert result["results_count"] > 0
    names = [s["name"] for s in result["stations"]]
    assert any("Wien" in n for n in names)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_oebb_station_board() -> None:
    """Fetch departures at Wien Hbf (station ID 1190100)."""
    async with aiohttp.ClientSession() as session:
        result = await async_oebb_station_board(session, station_id="1190100")

    assert "message" not in result, f"API error: {result.get('message')}"
    assert result["journeys_count"] > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_oebb_trip_search() -> None:
    """Search connections from Wien Hbf to Salzburg Hbf."""
    async with aiohttp.ClientSession() as session:
        result = await async_oebb_trip_search(
            session,
            from_station_name="Wien Hbf",
            to_station_name="Salzburg Hbf",
        )

    assert "message" not in result, f"API error: {result.get('message')}"
    assert result["connections_count"] > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_oebb_trip_search_direct_only() -> None:
    """Search direct connections from Wien Hbf to Salzburg Hbf."""
    async with aiohttp.ClientSession() as session:
        result = await async_oebb_trip_search(
            session,
            from_station_name="Wien Hbf",
            to_station_name="Salzburg Hbf",
            direct_only=True,
        )

    assert "message" not in result, f"API error: {result.get('message')}"
    assert result["connections_count"] > 0
    for con in result["connections"]:
        assert con["changes"] == 0, f"Expected direct, got {con['changes']} changes"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_oebb_trip_search_future_time() -> None:
    """Search Wien Hbf to Salzburg Hbf departing tomorrow 08:00."""
    from datetime import datetime, timedelta

    tomorrow = datetime.now() + timedelta(days=1)  # noqa: DTZ005
    search_time = tomorrow.replace(hour=8, minute=0, second=0).isoformat()

    async with aiohttp.ClientSession() as session:
        result = await async_oebb_trip_search(
            session,
            from_station_name="Wien Hbf",
            to_station_name="Salzburg Hbf",
            time=search_time,
            time_mode="departure",
        )

    assert "message" not in result, f"API error: {result.get('message')}"
    assert result["connections_count"] > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_oebb_service_alerts() -> None:
    """Fetch current service alerts."""
    async with aiohttp.ClientSession() as session:
        result = await async_oebb_service_alerts(session)

    assert "message" not in result, f"API error: {result.get('message')}"
    # alerts_count may be 0 if no current disruptions, but the key must exist
    assert "alerts_count" in result
    assert "alerts" in result
