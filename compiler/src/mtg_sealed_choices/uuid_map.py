"""Build a UUID index from streaming AllPrintings parser events.

The consumer owns file/network I/O and supplies ijson-compatible events, keeping
this package independent of a JSON parser or an HTTP client.
"""

from collections.abc import Iterable
from typing import Any


def uuid_map_from_events(events: Iterable[tuple[str, str, Any]]) -> dict:
    result: dict = {}
    set_code = ""
    section = ""
    record: dict = {}
    for prefix, event, value in events:
        if prefix == "data" and event == "map_key":
            set_code = value
            result[set_code.lower()] = {
                "booster": set(),
                "decks": set(),
                "sealedProduct": {},
                "cards": {},
                "tokens": {},
            }
            section = ""
        elif prefix == f"data.{set_code}" and event == "map_key":
            section = value
        elif section == "booster" and prefix == f"data.{set_code}.booster" and event == "map_key":
            result[set_code.lower()]["booster"].add(value)
        elif section == "decks" and prefix == f"data.{set_code}.decks.item.name":
            result[set_code.lower()]["decks"].add(value)
        elif section in {"sealedProduct", "cards", "tokens"}:
            item = f"data.{set_code}.{section}.item"
            if prefix == item and event == "start_map":
                record = {"name": "", "number": "", "uuid": "", "side": "a"}
            elif prefix == item and event == "end_map":
                target = result[set_code.lower()][section]
                if section == "sealedProduct":
                    target[record["name"]] = record["uuid"]
                elif record["side"] == "a":
                    target[record["number"]] = (record["uuid"], record["name"])
            elif prefix in (f"{item}.name", f"{item}.number", f"{item}.uuid", f"{item}.side"):
                record[prefix.rsplit(".", 1)[1]] = value
    return result
