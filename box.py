"""Box capacity and packing compatibility rules for BoxWise."""

import math

from item import Item


class Box:
    """Store packed items and enforce weight and compatibility rules."""

    HEAVY_ITEM_WEIGHT = 3.0

    def __init__(self, box_id, max_weight):
        if isinstance(max_weight, bool):
            raise ValueError("Maximum box weight must be a number.")
        try:
            max_weight = float(max_weight)
        except (TypeError, ValueError):
            raise ValueError("Maximum box weight must be a number.") from None
        if not math.isfinite(max_weight) or max_weight <= 0:
            raise ValueError("Maximum box weight must be finite and greater than 0.")

        self.box_id = box_id
        self.max_weight = max_weight
        self.items = []

    def total_weight(self):
        """Calculate total weight from the current contents."""
        return math.fsum(item.weight for item in self.items)

    def get_rejection_reason(self, item):
        """Return the first rejection reason, or an empty string if allowed.

        Checking an item does not change the box contents.
        """
        new_weight = math.fsum([self.total_weight(), item.weight])
        # Allow only tiny floating-point differences at the weight boundary.
        if new_weight > self.max_weight and not math.isclose(
            new_weight, self.max_weight, rel_tol=1e-12, abs_tol=0.0
        ):
            return f"Adding {item.name} would exceed the box weight limit."

        for packed_item in self.items:
            if (
                item.category == "Liquid"
                and packed_item.category == "Electronics"
            ) or (
                item.category == "Electronics"
                and packed_item.category == "Liquid"
            ):
                return (
                    f"{item.name} conflicts with {packed_item.name}: "
                    "liquids and electronics cannot share a box."
                )

            if (
                item.fragile
                and packed_item.weight >= self.HEAVY_ITEM_WEIGHT
            ) or (
                packed_item.fragile
                and item.weight >= self.HEAVY_ITEM_WEIGHT
            ):
                return (
                    f"{item.name} conflicts with {packed_item.name}: "
                    "fragile items cannot share a box with another item "
                    f"weighing {self.HEAVY_ITEM_WEIGHT:g} kg or more."
                )

        return ""

    def add_item(self, item):
        """Return True after adding an allowed item; otherwise return False."""
        if self.get_rejection_reason(item):
            return False
        self.items.append(item)
        return True


if __name__ == "__main__":
    box = Box(1, 10.0)
    books = Item("Books", "Bedroom", 3.0, "General", False)
    cup = Item("Glass cup", "Kitchen", 0.3, "General", True)
    print("Add books:", box.add_item(books))
    print("Cup rejection reason:", box.get_rejection_reason(cup))
    print("Add cup:", box.add_item(cup))
    print("Total weight:", box.total_weight(), "kg")
    print("Item count:", len(box.items))
