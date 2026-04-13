"""API helpers for OeBB (Austrian Federal Railways) train data."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

import aiohttp

from oebb_mcp_server.const import (
    OEBB_API_ENDPOINT,
    OEBB_API_LANG,
    OEBB_API_TIMEOUT,
    OEBB_API_VERSION,
    OEBB_AUTH_AID,
    OEBB_CLIENT_ID,
    OEBB_CLIENT_L,
    OEBB_CLIENT_NAME,
    OEBB_CLIENT_TYPE,
)

_LOGGER = logging.getLogger(__name__)


def _build_request_body(svc_req_list: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the OeBB mgate.exe POST request envelope."""
    return {
        "id": "1",
        "ver": OEBB_API_VERSION,
        "lang": OEBB_API_LANG,
        "auth": {"type": "AID", "aid": OEBB_AUTH_AID},
        "client": {
            "id": OEBB_CLIENT_ID,
            "type": OEBB_CLIENT_TYPE,
            "name": OEBB_CLIENT_NAME,
            "l": OEBB_CLIENT_L,
        },
        "formatted": False,
        "svcReqL": svc_req_list,
    }


def _format_oebb_time(date_str: str, time_str: str) -> str:
    """Combine OeBB YYYYMMDD date and HHMMSS time into ISO 8601."""
    try:
        dt = datetime.strptime(f"{date_str}{time_str}", "%Y%m%d%H%M%S")  # noqa: DTZ007
        return dt.isoformat()
    except (ValueError, TypeError):
        return f"{date_str} {time_str}"


async def _async_loc_match(
    session: aiohttp.ClientSession,
    query: str,
    max_results: int = 10,
) -> list[dict[str, Any]]:
    """Call LocMatch and return the raw locL list."""
    body = _build_request_body(
        [
            {
                "meth": "LocMatch",
                "req": {
                    "input": {
                        "field": "S",
                        "loc": {"name": query, "type": "ALL"},
                        "maxLoc": max_results,
                    },
                },
            }
        ]
    )
    async with asyncio.timeout(OEBB_API_TIMEOUT):
        response = await session.post(OEBB_API_ENDPOINT, json=body)
        data = await response.json()

    svc_res = data.get("svcResL", [{}])[0]
    if svc_res.get("err", "OK") != "OK":
        _LOGGER.warning("OeBB LocMatch error: %s", svc_res.get("errTxt", "Unknown"))
        return []

    return svc_res.get("res", {}).get("match", {}).get("locL", [])


async def _async_resolve_station(
    session: aiohttp.ClientSession,
    station_id: str | None,
    station_name: str | None,
) -> dict[str, Any] | None:
    """Resolve a station to a lid/name/extId dict.

    If station_id is given, constructs the lid directly.
    If station_name is given, calls LocMatch to resolve.
    Returns None if resolution fails.
    """
    if station_id:
        lid = f"A=1@L={station_id}@"
        return {"lid": lid, "name": station_id, "extId": station_id}

    if station_name:
        locations = await _async_loc_match(session, station_name, max_results=1)
        if locations:
            loc = locations[0]
            return {
                "lid": loc.get("lid", ""),
                "name": loc.get("name", station_name),
                "extId": loc.get("extId", ""),
            }
        _LOGGER.warning("OeBB station not found: %s", station_name)

    return None


async def async_oebb_search_station(
    session: aiohttp.ClientSession,
    query: str,
    max_results: int = 10,
) -> dict[str, Any]:
    """Search OeBB stations by name.

    Returns a dict with results_count and stations list.
    Returns a dict with just 'message' on error.
    """
    try:
        locations = await _async_loc_match(session, query, max_results)

        stations = []
        for loc in locations:
            crd = loc.get("crd", {})
            stations.append(
                {
                    "name": loc.get("name", ""),
                    "station_id": loc.get("extId", ""),
                    "lid": loc.get("lid", ""),
                    "type": loc.get("type", ""),
                    "latitude": crd.get("y", 0) / 1_000_000 if crd.get("y") else None,
                    "longitude": crd.get("x", 0) / 1_000_000 if crd.get("x") else None,
                }
            )

        return {
            "results_count": len(stations),
            "stations": stations,
        }

    except TimeoutError:
        _LOGGER.error("Timeout searching OeBB stations for '%s'", query)
        return {"message": "Timeout"}
    except aiohttp.ClientError as err:
        _LOGGER.error("Error searching OeBB stations: %s", err)
        return {"message": "No data"}
    except Exception as err:
        _LOGGER.warning("Unexpected error searching OeBB stations: %s", err)
        return {"message": "No data"}


async def async_oebb_station_board(
    session: aiohttp.ClientSession,
    station_id: str | None = None,
    station_name: str | None = None,
    board_type: str = "DEP",
    max_journeys: int = 10,
) -> dict[str, Any]:
    """Fetch departures or arrivals at an OeBB station.

    Accepts station_id (extId) or station_name (auto-resolved via LocMatch).
    Returns a dict with station info and journeys list.
    Returns a dict with just 'message' on error.
    """
    try:
        station = await _async_resolve_station(session, station_id, station_name)
        if not station:
            return {"message": "Station not found"}

        now = datetime.now()  # noqa: DTZ005
        body = _build_request_body(
            [
                {
                    "meth": "StationBoard",
                    "req": {
                        "stbLoc": {"lid": station["lid"], "type": "S"},
                        "date": now.strftime("%Y%m%d"),
                        "time": now.strftime("%H%M%S"),
                        "type": board_type,
                        "maxJny": max_journeys,
                    },
                }
            ]
        )

        async with asyncio.timeout(OEBB_API_TIMEOUT):
            response = await session.post(OEBB_API_ENDPOINT, json=body)
            data = await response.json()

        svc_res = data.get("svcResL", [{}])[0]
        if svc_res.get("err", "OK") != "OK":
            _LOGGER.warning(
                "OeBB StationBoard error: %s", svc_res.get("errTxt", "Unknown")
            )
            return {"message": svc_res.get("errTxt", "API error")}

        res = svc_res.get("res", {})
        common = res.get("common", {})
        prod_list = common.get("prodL", [])
        jny_list = res.get("jnyL", [])

        journeys = []
        for jny in jny_list:
            prod_idx = jny.get("prodX", -1)
            product = (
                prod_list[prod_idx].get("name", "Unknown")
                if 0 <= prod_idx < len(prod_list)
                else "Unknown"
            )

            stb_stop = jny.get("stbStop", {})
            date_str = jny.get("date", now.strftime("%Y%m%d"))

            time_planned = stb_stop.get("dTimeS") or stb_stop.get("aTimeS", "")
            time_real = stb_stop.get("dTimeR") or stb_stop.get("aTimeR")

            platform = stb_stop.get("dPltfS", {}).get("txt") or stb_stop.get(
                "aPltfS", {}
            ).get("txt")

            journeys.append(
                {
                    "product": product,
                    "direction": jny.get("dirTxt", ""),
                    "time_planned": (
                        _format_oebb_time(date_str, time_planned)
                        if time_planned
                        else None
                    ),
                    "time_real": (
                        _format_oebb_time(date_str, time_real) if time_real else None
                    ),
                    "platform": platform,
                }
            )

        return {
            "station_name": station["name"],
            "station_id": station["extId"],
            "board_type": board_type,
            "journeys_count": len(journeys),
            "journeys": journeys,
        }

    except TimeoutError:
        _LOGGER.error("Timeout fetching OeBB station board for %s", station_id)
        return {"message": "Timeout"}
    except aiohttp.ClientError as err:
        _LOGGER.error("Error fetching OeBB station board: %s", err)
        return {"message": "No data"}
    except Exception as err:
        _LOGGER.warning("Unexpected error fetching OeBB station board: %s", err)
        return {"message": "No data"}


async def async_oebb_trip_search(
    session: aiohttp.ClientSession,
    from_station_id: str | None = None,
    from_station_name: str | None = None,
    to_station_id: str | None = None,
    to_station_name: str | None = None,
    max_connections: int = 5,
    time: str | None = None,
    time_mode: str = "departure",
    direct_only: bool = False,
) -> dict[str, Any]:
    """Search for train connections between two OeBB stations.

    Accepts station IDs (extId) or station names (auto-resolved via LocMatch)
    for both departure and arrival stations.
    Optionally accepts a time (ISO 8601) and time_mode ("departure" or
    "arrival") to plan future trips. Defaults to current time, departing.
    When direct_only is True, only direct connections (no changes) are
    returned.
    Returns a dict with connection details including legs.
    Returns a dict with just 'message' on error.
    """
    try:
        from_station = await _async_resolve_station(
            session, from_station_id, from_station_name
        )
        if not from_station:
            return {"message": "Departure station not found"}

        to_station = await _async_resolve_station(
            session, to_station_id, to_station_name
        )
        if not to_station:
            return {"message": "Arrival station not found"}

        search_dt = (
            datetime.fromisoformat(time) if time else datetime.now()  # noqa: DTZ005
        )
        out_frwd = time_mode != "arrival"

        trip_req: dict[str, Any] = {
            "depLocL": [{"lid": from_station["lid"], "type": "S"}],
            "arrLocL": [{"lid": to_station["lid"], "type": "S"}],
            "outDate": search_dt.strftime("%Y%m%d"),
            "outTime": search_dt.strftime("%H%M%S"),
            "outFrwd": out_frwd,
            "numF": max_connections,
            "jnyFltrL": [{"type": "PROD", "mode": "INC", "value": "1023"}],
            "getPasslist": False,
            "getPolyline": False,
        }
        if direct_only:
            trip_req["maxChg"] = 0

        body = _build_request_body([{"meth": "TripSearch", "req": trip_req}])

        async with asyncio.timeout(OEBB_API_TIMEOUT):
            response = await session.post(OEBB_API_ENDPOINT, json=body)
            data = await response.json()

        svc_res = data.get("svcResL", [{}])[0]
        if svc_res.get("err", "OK") != "OK":
            _LOGGER.warning(
                "OeBB TripSearch error: %s", svc_res.get("errTxt", "Unknown")
            )
            return {"message": svc_res.get("errTxt", "API error")}

        res = svc_res.get("res", {})
        common = res.get("common", {})
        prod_list = common.get("prodL", [])
        loc_list = common.get("locL", [])
        out_con_list = res.get("outConL", [])

        connections = []
        for con in out_con_list:
            con_date = con.get("date", search_dt.strftime("%Y%m%d"))
            dep = con.get("dep", {})
            arr = con.get("arr", {})

            dep_time = dep.get("dTimeS", "")
            dep_time_real = dep.get("dTimeR")
            arr_time = arr.get("aTimeS", "")
            arr_time_real = arr.get("aTimeR")

            dep_platform = dep.get("dPltfS", {}).get("txt")
            arr_platform = arr.get("aPltfS", {}).get("txt")

            dur_raw = con.get("dur", "")
            duration = ""
            if dur_raw and len(dur_raw) >= 6:
                hours = int(dur_raw[:2])
                minutes = int(dur_raw[2:4])
                duration = f"{hours}:{minutes:02d}"

            legs = []
            for sec in con.get("secL", []):
                if sec.get("type") != "JNY":
                    continue

                jny = sec.get("jny", {})
                prod_idx = jny.get("prodX", -1)
                product = (
                    prod_list[prod_idx].get("name", "Unknown")
                    if 0 <= prod_idx < len(prod_list)
                    else "Unknown"
                )

                sec_dep = sec.get("dep", {})
                sec_arr = sec.get("arr", {})

                dep_loc_idx = sec_dep.get("locX", -1)
                arr_loc_idx = sec_arr.get("locX", -1)
                leg_from = (
                    loc_list[dep_loc_idx].get("name", "Unknown")
                    if 0 <= dep_loc_idx < len(loc_list)
                    else "Unknown"
                )
                leg_to = (
                    loc_list[arr_loc_idx].get("name", "Unknown")
                    if 0 <= arr_loc_idx < len(loc_list)
                    else "Unknown"
                )

                legs.append(
                    {
                        "product": product,
                        "direction": jny.get("dirTxt", ""),
                        "from_station": leg_from,
                        "to_station": leg_to,
                        "departure": _format_oebb_time(
                            con_date, sec_dep.get("dTimeS", "")
                        ),
                        "arrival": _format_oebb_time(
                            con_date, sec_arr.get("aTimeS", "")
                        ),
                        "platform_departure": sec_dep.get("dPltfS", {}).get("txt"),
                        "platform_arrival": sec_arr.get("aPltfS", {}).get("txt"),
                    }
                )

            connections.append(
                {
                    "departure": _format_oebb_time(con_date, dep_time),
                    "departure_real": (
                        _format_oebb_time(con_date, dep_time_real)
                        if dep_time_real
                        else None
                    ),
                    "arrival": _format_oebb_time(con_date, arr_time),
                    "arrival_real": (
                        _format_oebb_time(con_date, arr_time_real)
                        if arr_time_real
                        else None
                    ),
                    "duration": duration,
                    "changes": con.get("chg", 0),
                    "platform_departure": dep_platform,
                    "platform_arrival": arr_platform,
                    "legs": legs,
                }
            )

        return {
            "from_station": from_station["name"],
            "to_station": to_station["name"],
            "connections_count": len(connections),
            "connections": connections,
        }

    except TimeoutError:
        _LOGGER.error("Timeout searching OeBB trips")
        return {"message": "Timeout"}
    except aiohttp.ClientError as err:
        _LOGGER.error("Error searching OeBB trips: %s", err)
        return {"message": "No data"}
    except Exception as err:
        _LOGGER.warning("Unexpected error searching OeBB trips: %s", err)
        return {"message": "No data"}


def _format_oebb_date(date_str: str) -> str:
    """Convert OeBB YYYYMMDD date to ISO 8601 date string."""
    try:
        dt = datetime.strptime(date_str, "%Y%m%d")  # noqa: DTZ007
        return dt.date().isoformat()
    except (ValueError, TypeError):
        return date_str


async def async_oebb_service_alerts(
    session: aiohttp.ClientSession,
    max_alerts: int = 20,
    product_filter: int = 1023,
) -> dict[str, Any]:
    """Fetch current OeBB service alerts and disruptions.

    Returns a dict with alerts_count and alerts list.
    product_filter is a bitmask (1=ICE/RJX, 2=IC/EC, 4=NJ, 8=D/EN,
    16=REX/R, 32=S-Bahn, 64=Bus, 128=Ferry, 256=U-Bahn, 512=Tram,
    1023=all).
    Returns a dict with just 'message' on error.
    """
    try:
        body = _build_request_body(
            [
                {
                    "meth": "HimSearch",
                    "req": {
                        "himFltrL": [
                            {
                                "type": "PROD",
                                "mode": "INC",
                                "value": str(product_filter),
                            }
                        ],
                        "maxNum": max_alerts,
                    },
                }
            ]
        )

        async with asyncio.timeout(OEBB_API_TIMEOUT):
            response = await session.post(OEBB_API_ENDPOINT, json=body)
            data = await response.json()

        svc_res = data.get("svcResL", [{}])[0]
        if svc_res.get("err", "OK") != "OK":
            _LOGGER.warning(
                "OeBB HimSearch error: %s", svc_res.get("errTxt", "Unknown")
            )
            return {"message": svc_res.get("errTxt", "API error")}

        res = svc_res.get("res", {})
        loc_list = res.get("common", {}).get("locL", [])
        msg_list = res.get("msgL", [])

        alerts = []
        for msg in msg_list:
            from_loc_idx = msg.get("fLocX", -1)
            to_loc_idx = msg.get("tLocX", -1)
            from_station = (
                loc_list[from_loc_idx].get("name", "")
                if 0 <= from_loc_idx < len(loc_list)
                else None
            )
            to_station = (
                loc_list[to_loc_idx].get("name", "")
                if 0 <= to_loc_idx < len(loc_list)
                else None
            )

            alerts.append(
                {
                    "id": msg.get("hid", ""),
                    "headline": msg.get("head", ""),
                    "text": msg.get("text", ""),
                    "priority": msg.get("prio", 0),
                    "start_date": _format_oebb_date(msg.get("sDate", "")),
                    "end_date": _format_oebb_date(msg.get("eDate", "")),
                    "from_station": from_station,
                    "to_station": to_station,
                }
            )

        return {
            "alerts_count": len(alerts),
            "alerts": alerts,
        }

    except TimeoutError:
        _LOGGER.error("Timeout fetching OeBB service alerts")
        return {"message": "Timeout"}
    except aiohttp.ClientError as err:
        _LOGGER.error("Error fetching OeBB service alerts: %s", err)
        return {"message": "No data"}
    except Exception as err:
        _LOGGER.warning("Unexpected error fetching OeBB service alerts: %s", err)
        return {"message": "No data"}
