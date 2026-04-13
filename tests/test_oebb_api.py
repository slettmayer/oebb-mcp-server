"""Tests for the OeBB API helper."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from oebb_mcp_server.oebb_api import (
    _build_request_body,
    _format_oebb_time,
    async_oebb_search_station,
    async_oebb_service_alerts,
    async_oebb_station_board,
    async_oebb_trip_search,
)


def _make_session(
    json_data: dict | list[dict],
    raise_error: Exception | None = None,
) -> MagicMock:
    """Create a mock aiohttp session for OeBB POST requests.

    If json_data is a list, successive calls return successive items.
    """
    session = MagicMock(spec=aiohttp.ClientSession)
    if raise_error:
        session.post = AsyncMock(side_effect=raise_error)
    elif isinstance(json_data, list):
        responses = []
        for d in json_data:
            resp = AsyncMock()
            resp.json = AsyncMock(return_value=d)
            responses.append(resp)
        session.post = AsyncMock(side_effect=responses)
    else:
        response = AsyncMock()
        response.json = AsyncMock(return_value=json_data)
        session.post = AsyncMock(return_value=response)
    return session


# --- Sample API responses ---

SAMPLE_LOC_MATCH_RESPONSE = {
    "svcResL": [
        {
            "err": "OK",
            "res": {
                "match": {
                    "locL": [
                        {
                            "lid": "A=1@O=Wien Hbf@X=16375326@Y=48185089@U=81@L=1190100@",  # noqa: E501
                            "type": "S",
                            "name": "Wien Hbf",
                            "extId": "1190100",
                            "crd": {"x": 16375326, "y": 48185089},
                            "pCls": 127,
                        },
                        {
                            "lid": "A=1@O=Wien Meidling@X=16333041@Y=48174837@U=81@L=8100514@",  # noqa: E501
                            "type": "S",
                            "name": "Wien Meidling",
                            "extId": "8100514",
                            "crd": {"x": 16333041, "y": 48174837},
                            "pCls": 127,
                        },
                    ]
                }
            },
        }
    ]
}

SAMPLE_LOC_MATCH_EMPTY = {
    "svcResL": [
        {
            "err": "OK",
            "res": {"match": {"locL": []}},
        }
    ]
}

SAMPLE_STATION_BOARD_RESPONSE = {
    "svcResL": [
        {
            "err": "OK",
            "res": {
                "common": {
                    "prodL": [
                        {"name": "RJ 162", "cls": 1},
                        {"name": "S1", "cls": 32},
                    ]
                },
                "jnyL": [
                    {
                        "prodX": 0,
                        "dirTxt": "Salzburg Hbf",
                        "date": "20260410",
                        "stbStop": {
                            "dTimeS": "143000",
                            "dTimeR": "143200",
                            "dPltfS": {"txt": "5"},
                        },
                    },
                    {
                        "prodX": 1,
                        "dirTxt": "Flughafen Wien",
                        "date": "20260410",
                        "stbStop": {
                            "dTimeS": "144500",
                            "dPltfS": {"txt": "2"},
                        },
                    },
                ],
            },
        }
    ]
}

SAMPLE_TRIP_SEARCH_RESPONSE = {
    "svcResL": [
        {
            "err": "OK",
            "res": {
                "common": {
                    "prodL": [
                        {"name": "RJ 162", "cls": 1},
                        {"name": "REX 3", "cls": 16},
                    ],
                    "locL": [
                        {"name": "Wien Hbf", "extId": "1190100"},
                        {"name": "Salzburg Hbf", "extId": "8100002"},
                        {"name": "Linz Hbf", "extId": "8100013"},
                    ],
                },
                "outConL": [
                    {
                        "date": "20260410",
                        "dur": "025200",
                        "chg": 0,
                        "dep": {
                            "dTimeS": "143000",
                            "dTimeR": "143200",
                            "dPltfS": {"txt": "5"},
                        },
                        "arr": {
                            "aTimeS": "172200",
                            "aPltfS": {"txt": "3"},
                        },
                        "secL": [
                            {
                                "type": "JNY",
                                "jny": {"prodX": 0, "dirTxt": "Salzburg Hbf"},
                                "dep": {
                                    "locX": 0,
                                    "dTimeS": "143000",
                                    "dPltfS": {"txt": "5"},
                                },
                                "arr": {
                                    "locX": 1,
                                    "aTimeS": "172200",
                                    "aPltfS": {"txt": "3"},
                                },
                            }
                        ],
                    },
                    {
                        "date": "20260410",
                        "dur": "034500",
                        "chg": 1,
                        "dep": {
                            "dTimeS": "150000",
                            "dPltfS": {"txt": "7"},
                        },
                        "arr": {
                            "aTimeS": "184500",
                            "aPltfS": {"txt": "1"},
                        },
                        "secL": [
                            {
                                "type": "JNY",
                                "jny": {"prodX": 1, "dirTxt": "Linz Hbf"},
                                "dep": {
                                    "locX": 0,
                                    "dTimeS": "150000",
                                    "dPltfS": {"txt": "7"},
                                },
                                "arr": {
                                    "locX": 2,
                                    "aTimeS": "163000",
                                    "aPltfS": {"txt": "2"},
                                },
                            },
                            {
                                "type": "JNY",
                                "jny": {"prodX": 0, "dirTxt": "Salzburg Hbf"},
                                "dep": {
                                    "locX": 2,
                                    "dTimeS": "164500",
                                    "dPltfS": {"txt": "4"},
                                },
                                "arr": {
                                    "locX": 1,
                                    "aTimeS": "184500",
                                    "aPltfS": {"txt": "1"},
                                },
                            },
                        ],
                    },
                ],
            },
        }
    ]
}

SAMPLE_API_ERROR = {
    "svcResL": [
        {
            "err": "PARSE",
            "errTxt": "Invalid request",
        }
    ]
}


# --- Tests for _build_request_body ---


def test_build_request_body_structure() -> None:
    """Test that the envelope has correct auth and client fields."""
    body = _build_request_body([{"meth": "Test"}])

    assert body["id"] == "1"
    assert body["ver"] == "1.67"
    assert body["lang"] == "deu"
    assert body["auth"] == {"type": "AID", "aid": "OWDL4fE4ixNiPBBm"}
    assert body["client"]["id"] == "OEBB"
    assert body["client"]["type"] == "WEB"
    assert body["formatted"] is False
    assert body["svcReqL"] == [{"meth": "Test"}]


# --- Tests for _format_oebb_time ---


def test_format_oebb_time_valid() -> None:
    """Test combining date and time into ISO 8601."""
    result = _format_oebb_time("20260410", "143000")
    assert result == "2026-04-10T14:30:00"


def test_format_oebb_time_invalid() -> None:
    """Test fallback for invalid input."""
    result = _format_oebb_time("bad", "data")
    assert result == "bad data"


# --- Tests for async_oebb_search_station ---


@pytest.mark.asyncio
async def test_oebb_search_station_success() -> None:
    """Test successful station search."""
    session = _make_session(SAMPLE_LOC_MATCH_RESPONSE)

    result = await async_oebb_search_station(session, "Wien")

    assert "message" not in result
    assert result["results_count"] == 2
    assert result["stations"][0]["name"] == "Wien Hbf"
    assert result["stations"][0]["station_id"] == "1190100"
    assert result["stations"][0]["type"] == "S"
    assert result["stations"][0]["latitude"] == pytest.approx(48.185089, rel=1e-5)
    assert result["stations"][0]["longitude"] == pytest.approx(16.375326, rel=1e-5)
    assert result["stations"][1]["name"] == "Wien Meidling"


@pytest.mark.asyncio
async def test_oebb_search_station_no_results() -> None:
    """Test station search with no matches."""
    session = _make_session(SAMPLE_LOC_MATCH_EMPTY)

    result = await async_oebb_search_station(session, "Nonexistent")

    assert "message" not in result
    assert result["results_count"] == 0
    assert result["stations"] == []


@pytest.mark.asyncio
async def test_oebb_search_station_timeout() -> None:
    """Test timeout handling."""
    session = _make_session({}, raise_error=TimeoutError())

    result = await async_oebb_search_station(session, "Wien")

    assert result == {"message": "Timeout"}


@pytest.mark.asyncio
async def test_oebb_search_station_client_error() -> None:
    """Test aiohttp client error handling."""
    session = _make_session({}, raise_error=aiohttp.ClientError("Connection failed"))

    result = await async_oebb_search_station(session, "Wien")

    assert result == {"message": "No data"}


# --- Tests for async_oebb_station_board ---


@pytest.mark.asyncio
async def test_oebb_station_board_by_id() -> None:
    """Test station board lookup by station ID (skips LocMatch)."""
    session = _make_session(SAMPLE_STATION_BOARD_RESPONSE)

    result = await async_oebb_station_board(session, station_id="1190100")

    assert "message" not in result
    assert result["station_id"] == "1190100"
    assert result["board_type"] == "DEP"
    assert result["journeys_count"] == 2
    # Only one POST call (StationBoard, no LocMatch)
    assert session.post.call_count == 1


@pytest.mark.asyncio
async def test_oebb_station_board_by_name() -> None:
    """Test station board lookup by name (calls LocMatch first)."""
    session = _make_session([SAMPLE_LOC_MATCH_RESPONSE, SAMPLE_STATION_BOARD_RESPONSE])

    result = await async_oebb_station_board(session, station_name="Wien Hbf")

    assert "message" not in result
    assert result["station_name"] == "Wien Hbf"
    assert result["journeys_count"] == 2
    # Two POST calls: LocMatch + StationBoard
    assert session.post.call_count == 2


@pytest.mark.asyncio
async def test_oebb_station_board_resolves_product_names() -> None:
    """Test that product names are resolved from common.prodL."""
    session = _make_session(SAMPLE_STATION_BOARD_RESPONSE)

    result = await async_oebb_station_board(session, station_id="1190100")

    assert result["journeys"][0]["product"] == "RJ 162"
    assert result["journeys"][0]["direction"] == "Salzburg Hbf"
    assert result["journeys"][0]["platform"] == "5"
    assert result["journeys"][1]["product"] == "S1"


@pytest.mark.asyncio
async def test_oebb_station_board_parses_times() -> None:
    """Test that planned and real times are parsed correctly."""
    session = _make_session(SAMPLE_STATION_BOARD_RESPONSE)

    result = await async_oebb_station_board(session, station_id="1190100")

    assert result["journeys"][0]["time_planned"] == "2026-04-10T14:30:00"
    assert result["journeys"][0]["time_real"] == "2026-04-10T14:32:00"
    assert result["journeys"][1]["time_planned"] == "2026-04-10T14:45:00"
    assert result["journeys"][1]["time_real"] is None


@pytest.mark.asyncio
async def test_oebb_station_board_no_station() -> None:
    """Test error when neither station ID nor name is provided."""
    session = _make_session({})

    result = await async_oebb_station_board(session)

    assert result == {"message": "Station not found"}


@pytest.mark.asyncio
async def test_oebb_station_board_station_not_found() -> None:
    """Test error when LocMatch returns no results."""
    session = _make_session(SAMPLE_LOC_MATCH_EMPTY)

    result = await async_oebb_station_board(session, station_name="Nonexistent")

    assert result == {"message": "Station not found"}


@pytest.mark.asyncio
async def test_oebb_station_board_api_error() -> None:
    """Test handling of API-level error response."""
    session = _make_session(SAMPLE_API_ERROR)

    result = await async_oebb_station_board(session, station_id="1190100")

    assert result["message"] == "Invalid request"


# --- Tests for async_oebb_trip_search ---


@pytest.mark.asyncio
async def test_oebb_trip_search_success() -> None:
    """Test successful trip search with connections and legs."""
    session = _make_session(SAMPLE_TRIP_SEARCH_RESPONSE)

    result = await async_oebb_trip_search(
        session, from_station_id="1190100", to_station_id="8100002"
    )

    assert "message" not in result
    assert result["from_station"] == "1190100"
    assert result["to_station"] == "8100002"
    assert result["connections_count"] == 2

    # First connection: direct
    con1 = result["connections"][0]
    assert con1["departure"] == "2026-04-10T14:30:00"
    assert con1["arrival"] == "2026-04-10T17:22:00"
    assert con1["duration"] == "2:52"
    assert con1["changes"] == 0
    assert len(con1["legs"]) == 1
    assert con1["legs"][0]["product"] == "RJ 162"
    assert con1["legs"][0]["from_station"] == "Wien Hbf"
    assert con1["legs"][0]["to_station"] == "Salzburg Hbf"

    # Second connection: with change
    con2 = result["connections"][1]
    assert con2["changes"] == 1
    assert len(con2["legs"]) == 2
    assert con2["legs"][0]["product"] == "REX 3"
    assert con2["legs"][0]["to_station"] == "Linz Hbf"
    assert con2["legs"][1]["product"] == "RJ 162"


@pytest.mark.asyncio
async def test_oebb_trip_search_by_name() -> None:
    """Test trip search with station name resolution."""
    loc_response_1 = {
        "svcResL": [
            {
                "err": "OK",
                "res": {
                    "match": {
                        "locL": [
                            {
                                "lid": "A=1@L=1190100@",
                                "name": "Wien Hbf",
                                "extId": "1190100",
                            }
                        ]
                    }
                },
            }
        ]
    }
    loc_response_2 = {
        "svcResL": [
            {
                "err": "OK",
                "res": {
                    "match": {
                        "locL": [
                            {
                                "lid": "A=1@L=8100002@",
                                "name": "Salzburg Hbf",
                                "extId": "8100002",
                            }
                        ]
                    }
                },
            }
        ]
    }
    session = _make_session(
        [loc_response_1, loc_response_2, SAMPLE_TRIP_SEARCH_RESPONSE]
    )

    result = await async_oebb_trip_search(
        session, from_station_name="Wien Hbf", to_station_name="Salzburg Hbf"
    )

    assert "message" not in result
    assert result["from_station"] == "Wien Hbf"
    assert result["to_station"] == "Salzburg Hbf"
    # Three POST calls: 2x LocMatch + TripSearch
    assert session.post.call_count == 3


@pytest.mark.asyncio
async def test_oebb_trip_search_no_connections() -> None:
    """Test trip search with no connections found."""
    empty_response = {
        "svcResL": [
            {
                "err": "OK",
                "res": {
                    "common": {"prodL": [], "locL": []},
                    "outConL": [],
                },
            }
        ]
    }
    session = _make_session(empty_response)

    result = await async_oebb_trip_search(
        session, from_station_id="1190100", to_station_id="8100002"
    )

    assert "message" not in result
    assert result["connections_count"] == 0
    assert result["connections"] == []


@pytest.mark.asyncio
async def test_oebb_trip_search_missing_from() -> None:
    """Test error when departure station is not provided."""
    session = _make_session({})

    result = await async_oebb_trip_search(session, to_station_id="8100002")

    assert result == {"message": "Departure station not found"}


@pytest.mark.asyncio
async def test_oebb_trip_search_missing_to() -> None:
    """Test error when arrival station is not provided."""
    session = _make_session({})

    result = await async_oebb_trip_search(session, from_station_id="1190100")

    assert result == {"message": "Arrival station not found"}


@pytest.mark.asyncio
async def test_oebb_trip_search_timeout() -> None:
    """Test timeout handling."""
    session = _make_session({}, raise_error=TimeoutError())

    result = await async_oebb_trip_search(
        session, from_station_id="1190100", to_station_id="8100002"
    )

    assert result == {"message": "Timeout"}


@pytest.mark.asyncio
async def test_oebb_trip_search_realtime_times() -> None:
    """Test that real-time departure/arrival times are included."""
    session = _make_session(SAMPLE_TRIP_SEARCH_RESPONSE)

    result = await async_oebb_trip_search(
        session, from_station_id="1190100", to_station_id="8100002"
    )

    con1 = result["connections"][0]
    assert con1["departure_real"] == "2026-04-10T14:32:00"
    assert con1["arrival_real"] is None


@pytest.mark.asyncio
async def test_oebb_trip_search_with_departure_time() -> None:
    """Test trip search with a specific departure time."""
    session = _make_session(SAMPLE_TRIP_SEARCH_RESPONSE)

    result = await async_oebb_trip_search(
        session,
        from_station_id="1190100",
        to_station_id="8100002",
        time="2026-04-15T08:00:00",
        time_mode="departure",
    )

    assert "message" not in result
    assert result["connections_count"] == 2

    # Verify the POST body used the specified time and outFrwd=True
    call_args = session.post.call_args
    body = call_args.kwargs.get("json") or call_args[1].get("json")
    req = body["svcReqL"][0]["req"]
    assert req["outDate"] == "20260415"
    assert req["outTime"] == "080000"
    assert req["outFrwd"] is True


@pytest.mark.asyncio
async def test_oebb_trip_search_with_arrival_time() -> None:
    """Test trip search with arrival time mode sets outFrwd to False."""
    session = _make_session(SAMPLE_TRIP_SEARCH_RESPONSE)

    result = await async_oebb_trip_search(
        session,
        from_station_id="1190100",
        to_station_id="8100002",
        time="2026-04-15T18:00:00",
        time_mode="arrival",
    )

    assert "message" not in result

    # Verify outFrwd is False for arrival mode
    call_args = session.post.call_args
    body = call_args.kwargs.get("json") or call_args[1].get("json")
    req = body["svcReqL"][0]["req"]
    assert req["outDate"] == "20260415"
    assert req["outTime"] == "180000"
    assert req["outFrwd"] is False


@pytest.mark.asyncio
async def test_oebb_trip_search_default_time() -> None:
    """Test that omitting time uses current time (existing behavior)."""
    session = _make_session(SAMPLE_TRIP_SEARCH_RESPONSE)

    result = await async_oebb_trip_search(
        session, from_station_id="1190100", to_station_id="8100002"
    )

    assert "message" not in result

    # Verify outFrwd defaults to True
    call_args = session.post.call_args
    body = call_args.kwargs.get("json") or call_args[1].get("json")
    req = body["svcReqL"][0]["req"]
    assert req["outFrwd"] is True
    # outDate and outTime should be set (to current time, not empty)
    assert len(req["outDate"]) == 8
    assert len(req["outTime"]) == 6


@pytest.mark.asyncio
async def test_oebb_trip_search_direct_only() -> None:
    """Test that direct_only=True sends maxChg=0 to the API."""
    session = _make_session(SAMPLE_TRIP_SEARCH_RESPONSE)

    result = await async_oebb_trip_search(
        session,
        from_station_id="1190100",
        to_station_id="8100002",
        direct_only=True,
    )

    assert "message" not in result

    call_args = session.post.call_args
    body = call_args.kwargs.get("json") or call_args[1].get("json")
    req = body["svcReqL"][0]["req"]
    assert req["maxChg"] == 0


@pytest.mark.asyncio
async def test_oebb_trip_search_direct_only_default() -> None:
    """Test that maxChg is not sent when direct_only is False (default)."""
    session = _make_session(SAMPLE_TRIP_SEARCH_RESPONSE)

    result = await async_oebb_trip_search(
        session, from_station_id="1190100", to_station_id="8100002"
    )

    assert "message" not in result

    call_args = session.post.call_args
    body = call_args.kwargs.get("json") or call_args[1].get("json")
    req = body["svcReqL"][0]["req"]
    assert "maxChg" not in req


# --- Sample HimSearch response ---

SAMPLE_HIM_SEARCH_RESPONSE = {
    "svcResL": [
        {
            "err": "OK",
            "res": {
                "common": {
                    "locL": [
                        {"name": "Wien Hbf", "extId": "1190100"},
                        {"name": "Wien Meidling", "extId": "8100514"},
                        {"name": "Linz Hbf", "extId": "8100013"},
                        {"name": "Wels Hbf", "extId": "8100008"},
                    ]
                },
                "msgL": [
                    {
                        "hid": "HIM_12345",
                        "head": "Bauarbeiten Wien Hbf - Meidling",
                        "text": "Wegen Bauarbeiten kommt es zu Zugausfällen.",
                        "prio": 0,
                        "fLocX": 0,
                        "tLocX": 1,
                        "sDate": "20260410",
                        "eDate": "20260420",
                    },
                    {
                        "hid": "HIM_67890",
                        "head": "Schienenersatzverkehr Linz - Wels",
                        "text": "Busse statt Züge zwischen Linz und Wels.",
                        "prio": 1,
                        "fLocX": 2,
                        "tLocX": 3,
                        "sDate": "20260412",
                        "eDate": "20260415",
                    },
                ],
            },
        }
    ]
}

SAMPLE_HIM_SEARCH_EMPTY = {
    "svcResL": [
        {
            "err": "OK",
            "res": {"common": {"locL": []}, "msgL": []},
        }
    ]
}


# --- Tests for async_oebb_service_alerts ---


@pytest.mark.asyncio
async def test_oebb_service_alerts_success() -> None:
    """Test successful service alerts fetch."""
    session = _make_session(SAMPLE_HIM_SEARCH_RESPONSE)

    result = await async_oebb_service_alerts(session)

    assert "message" not in result
    assert result["alerts_count"] == 2
    assert result["alerts"][0]["id"] == "HIM_12345"
    assert result["alerts"][0]["headline"] == "Bauarbeiten Wien Hbf - Meidling"
    assert result["alerts"][0]["priority"] == 0
    assert result["alerts"][0]["start_date"] == "2026-04-10"
    assert result["alerts"][0]["end_date"] == "2026-04-20"
    assert result["alerts"][0]["from_station"] == "Wien Hbf"
    assert result["alerts"][0]["to_station"] == "Wien Meidling"
    assert result["alerts"][1]["id"] == "HIM_67890"
    assert result["alerts"][1]["priority"] == 1
    assert result["alerts"][1]["from_station"] == "Linz Hbf"
    assert result["alerts"][1]["to_station"] == "Wels Hbf"


@pytest.mark.asyncio
async def test_oebb_service_alerts_empty() -> None:
    """Test service alerts with no active alerts."""
    session = _make_session(SAMPLE_HIM_SEARCH_EMPTY)

    result = await async_oebb_service_alerts(session)

    assert "message" not in result
    assert result["alerts_count"] == 0
    assert result["alerts"] == []


@pytest.mark.asyncio
async def test_oebb_service_alerts_timeout() -> None:
    """Test timeout handling."""
    session = _make_session({}, raise_error=TimeoutError())

    result = await async_oebb_service_alerts(session)

    assert result == {"message": "Timeout"}


@pytest.mark.asyncio
async def test_oebb_service_alerts_client_error() -> None:
    """Test aiohttp client error handling."""
    session = _make_session({}, raise_error=aiohttp.ClientError("Connection failed"))

    result = await async_oebb_service_alerts(session)

    assert result == {"message": "No data"}


@pytest.mark.asyncio
async def test_oebb_service_alerts_api_error() -> None:
    """Test handling of API-level error response."""
    session = _make_session(SAMPLE_API_ERROR)

    result = await async_oebb_service_alerts(session)

    assert result["message"] == "Invalid request"


@pytest.mark.asyncio
async def test_oebb_service_alerts_product_filter() -> None:
    """Test that product filter is passed to the API."""
    session = _make_session(SAMPLE_HIM_SEARCH_EMPTY)

    await async_oebb_service_alerts(session, product_filter=33)

    call_args = session.post.call_args
    body = call_args.kwargs.get("json") or call_args[1].get("json")
    req = body["svcReqL"][0]["req"]
    assert req["himFltrL"][0]["value"] == "33"
