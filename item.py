"""Item records and input validation for BoxWise."""

import math


class Item:
    """Store one item's validated packing information; weight is in kg."""

    CATEGORIES = ("General", "Liquid", "Electronics")

    def __init__(self, name, room, weight, category, fragile):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Item name cannot be empty.")
        if not isinstance(room, str) or not room.strip():
            raise ValueError("Room cannot be empty.")

        if isinstance(weight, bool):
            raise ValueError("Weight must be a number.")
        try:
            weight = float(weight)
        except (TypeError, ValueError):
            raise ValueError("Weight must be a number.") from None
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError("Weight must be a finite number greater than 0.")

        if category not in self.CATEGORIES:
            raise ValueError("Category must be General, Liquid, or Electronics.")
        if not isinstance(fragile, bool):
            raise ValueError("Fragile must be True or False.")

        self.name = name.strip()
        self.room = room.strip()
        self.weight = weight
        self.category = category
        self.fragile = fragile

    def __str__(self):
        fragile_text = "Yes" if self.fragile else "No"
        return (
            f"{self.name} | Room: {self.room} | "
            f"Weight: {self.weight} kg | Category: {self.category} | "
            f"Fragile: {fragile_text}"
        )


if __name__ == "__main__":
    sample_item = Item("Glass cup", "Kitchen", 0.3, "General", True)
    print(sample_item)
