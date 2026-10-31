"""Generate a practical, rule-based packing plan for BoxWise."""

from box import Box
from item import Item


class PackingPlanner:
    """Prefer same-room boxes, then other compatible boxes, then a new box.

    This heuristic does not guarantee the minimum possible number of boxes.
    """

    def __init__(self, max_weight):
        # Reuse Box's capacity validation instead of maintaining a second rule.
        capacity_check = Box(1, max_weight)
        self.max_weight = capacity_check.max_weight
        self.boxes = []
        self.unallocated = []
        self.decisions = []

    def generate_plan(self, items):
        """Return (boxes, unallocated) for a fresh plan.

        Each input entry must be a validated Item. Each unallocated entry is
        an (item, reason) tuple. Input order and item attributes are unchanged.
        """
        # Replace the lists so repeated calls do not retain the previous plan.
        self.boxes = []
        self.unallocated = []
        self.decisions = []

        ordered_items = sorted(items, key=lambda item: (item.room, -item.weight))

        for item in ordered_items:
            attempts = []
            # False sorts before True, putting same-room boxes first.
            candidate_boxes = sorted(
                self.boxes,
                key=lambda box: not any(
                    packed_item.room == item.room for packed_item in box.items
                ),
            )

            packed = False
            for box in candidate_boxes:
                same_room = any(packed.room == item.room for packed in box.items)
                if box.add_item(item):
                    preference = "same-room preference" if same_room else "compatible space in another room's box"
                    self.decisions.append((item, f"Placed in Box {box.box_id}: {preference}. "
                                           + " ".join(attempts)))
                    packed = True
                    break
                attempts.append(f"Box {box.box_id}: {box.get_rejection_reason(item)}")

            if packed:
                continue

            new_box = Box(len(self.boxes) + 1, self.max_weight)
            reason = new_box.get_rejection_reason(item)
            if reason:
                # With unlimited boxes, a valid item is unallocated only if
                # its weight exceeds the capacity of an empty box.
                self.unallocated.append((item, reason))
                self.decisions.append((item, f"Unallocated: {reason}"))
            else:
                new_box.add_item(item)
                self.boxes.append(new_box)
                explanation = "No existing boxes yet." if not attempts else " ".join(attempts)
                self.decisions.append((item, f"Opened Box {new_box.box_id}. {explanation}"))

        return self.boxes, self.unallocated


if __name__ == "__main__":
    demo_items = [
        Item("Books", "Bedroom", 3.0, "General", False),
        Item("Clothes", "Bedroom", 2.0, "General", False),
        Item("Charger", "Bedroom", 0.2, "Electronics", False),
        Item("Shampoo", "Bathroom", 0.5, "Liquid", False),
        Item("Glass cup", "Kitchen", 0.3, "General", True),
        Item("Large vase", "Living room", 3.5, "General", True),
        Item("Desk", "Study", 8.0, "General", False),
    ]

    planner = PackingPlanner(5.0)
    boxes, unallocated = planner.generate_plan(demo_items)

    for box in boxes:
        names = ", ".join(item.name for item in box.items)
        print(f"Box {box.box_id}: {names} | {box.total_weight():g} kg")

    print("Unallocated items:")
    for item, reason in unallocated:
        print(f"- {item.name}: {reason}")
