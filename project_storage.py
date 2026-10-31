"""Save a complete BoxWise session, including assignments and packing progress."""

import json
import os
from pathlib import Path
import tempfile

from box import Box
from item import Item
from packing_planner import PackingPlanner


def save_project(path, items, capacity, planner, packed):
    """Persist items, capacity, the current plan and a set of packed Items."""
    capacity = Box(1, capacity).max_weight
    indexes = {item: index for index, item in enumerate(items)}
    plan = None
    if planner is not None:
        if planner.max_weight != capacity:
            raise ValueError("Regenerate the plan before saving the new box capacity.")
        plan = {
            "boxes": [[indexes[item] for item in box.items] for box in planner.boxes],
            "unallocated": [indexes[item] for item, reason in planner.unallocated],
            "decisions": [[indexes[item], reason] for item, reason in planner.decisions],
        }
    elif packed:
        raise ValueError("Packing progress requires a current plan.")
    data = {"version": 1, "capacity": capacity, "items": [vars(item) for item in items],
            "plan": plan, "packed": sorted(indexes[item] for item in packed)}
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent,
                                         delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(data, handle, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def load_project(path):
    """Validate a whole project before returning (items, capacity, planner, packed)."""
    try:
        with open(path, encoding="utf-8-sig") as handle:
            data = json.load(handle)
        if not isinstance(data, dict) or type(data.get("version")) is not int or data["version"] != 1:
            raise ValueError("Unsupported BoxWise project version.")
        if not isinstance(data["items"], list):
            raise ValueError("Project items must be a list.")
        items = [Item(**record) for record in data["items"]]
        capacity = Box(1, data["capacity"]).max_weight

        def read_indexes(values):
            if not isinstance(values, list) or any(
                type(index) is not int or not 0 <= index < len(items) for index in values
            ) or len(set(values)) != len(values):
                raise ValueError("Invalid or duplicate item reference in project.")
            return values

        packed_indexes = read_indexes(data["packed"])
        record = data["plan"]
        planner = None
        if record is not None:
            planner = PackingPlanner(capacity)
            used = []
            allocated = set()
            if not isinstance(record["boxes"], list):
                raise ValueError("Project boxes must be a list.")
            for box_indexes in record["boxes"]:
                read_indexes(box_indexes)
                if not box_indexes:
                    raise ValueError("A saved box cannot be empty.")
                box = Box(len(planner.boxes) + 1, capacity)
                for index in box_indexes:
                    if not box.add_item(items[index]):
                        raise ValueError("Saved box violates packing rules.")
                planner.boxes.append(box)
                used.extend(box_indexes)
                allocated.update(box_indexes)
            rejected = read_indexes(record["unallocated"])
            for index in rejected:
                reason = Box(1, capacity).get_rejection_reason(items[index])
                if not reason:
                    raise ValueError("An unallocated item could fit in an empty box.")
                planner.unallocated.append((items[index], reason))
            used.extend(rejected)
            if sorted(used) != list(range(len(items))):
                raise ValueError("Saved plan has missing or repeated items.")
            if not isinstance(record["decisions"], list):
                raise ValueError("Invalid saved decisions.")
            decision_indexes = []
            for decision in record["decisions"]:
                if not isinstance(decision, list) or len(decision) != 2 or not isinstance(decision[1], str):
                    raise ValueError("Invalid saved decision.")
                index = read_indexes([decision[0]])[0]
                decision_indexes.append(index)
                planner.decisions.append((items[index], decision[1]))
            if sorted(decision_indexes) != list(range(len(items))):
                raise ValueError("Saved decisions must cover every item once.")
            if not set(packed_indexes) <= allocated:
                raise ValueError("An unallocated item cannot be marked packed.")
        elif packed_indexes:
            raise ValueError("Packing progress requires a saved plan.")
        return items, capacity, planner, {items[index] for index in packed_indexes}
    except (KeyError, TypeError, AttributeError, json.JSONDecodeError) as error:
        raise ValueError("Invalid BoxWise project structure.") from error
