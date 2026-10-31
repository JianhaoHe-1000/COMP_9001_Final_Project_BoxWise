"""Convert a generated packing plan into a readable report."""

import math


def format_plan(planner):
    """Describe box labels, contents, warnings and actual allocation decisions."""
    packed_count = sum(len(box.items) for box in planner.boxes)
    packed_weight = math.fsum(box.total_weight() for box in planner.boxes)
    lines = [
        "PACKING OVERVIEW",
        f"{len(planner.boxes)} boxes | {packed_count} packed | "
        f"{len(planner.unallocated)} unallocated",
        f"Packed weight: {packed_weight:g} kg | Box limit: {planner.max_weight:g} kg",
        "Suggested plan; minimum box count is not guaranteed.",
    ]
    for box in planner.boxes:
        rooms = ", ".join(sorted({item.room for item in box.items}))
        labels = []
        if any(item.fragile for item in box.items):
            labels.append("FRAGILE - handle with care")
        if any(item.category == "Liquid" for item in box.items):
            labels.append("LIQUID - keep upright")
        if any(item.category == "Electronics" for item in box.items):
            labels.append("ELECTRONICS")
        lines.extend(["", f"BOX {box.box_id} | {rooms}",
                      f"Weight: {box.total_weight():g} / {box.max_weight:g} kg",
                      "Labels: " + ("; ".join(labels) if labels else "General")])
        for item in box.items:
            fragile = " | Fragile" if item.fragile else ""
            lines.append(f"  - {item.name} | {item.weight:g} kg | {item.room} | "
                         f"{item.category}{fragile}")
    lines.extend(["", "UNALLOCATED ITEMS"])
    if not planner.unallocated:
        lines.append("None - all items were packed.")
    for item, reason in planner.unallocated:
        lines.append(f"- {item.name} ({item.weight:g} kg): {reason}")
    lines.extend(["", "WHY THIS PLAN?"])
    lines.append("Room order, then heavier items first. Same-room boxes are tried first.")
    for number, (item, explanation) in enumerate(planner.decisions, 1):
        lines.append(f"{number}. {item.name}: {explanation.strip()}")
    return "\n".join(lines)
