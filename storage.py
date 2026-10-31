"""UTF-8 CSV persistence. Loading succeeds completely or raises an error."""

import csv
import os
from pathlib import Path
import tempfile

from item import Item


FIELDS = ("name", "room", "weight", "category", "fragile")


def load_items(path):
    """Read and validate every row before returning a replacement item list."""
    items = []
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, strict=True)
        try:
            headers = reader.fieldnames
        except csv.Error as error:
            raise ValueError(f"Invalid CSV header: {error}") from None
        if (headers is None or len(headers) != len(FIELDS)
                or set(headers) != set(FIELDS)):
            raise ValueError("CSV headers must be: " + ",".join(FIELDS))
        try:
            for row in reader:
                if None in row or any(value is None for value in row.values()):
                    raise ValueError(f"CSV line {reader.line_num}: incorrect column count.")
                try:
                    flag = row["fragile"].strip().lower()
                    if flag not in ("true", "false"):
                        raise ValueError("Fragile must be True or False.")
                    item = Item(row["name"], row["room"], row["weight"],
                                row["category"], flag == "true")
                except ValueError as error:
                    raise ValueError(f"CSV line {reader.line_num}: {error}") from None
                items.append(item)
        except csv.Error as error:
            raise ValueError(f"CSV line {reader.line_num}: {error}") from None
    return items


def save_items(path, items):
    """Write a temporary file, then replace the destination only on success."""
    path = Path(path)
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", newline="",
                                         dir=path.parent, delete=False) as handle:
            temporary_path = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=FIELDS)
            writer.writeheader()
            for item in items:
                writer.writerow(dict(name=item.name, room=item.room, weight=item.weight,
                                     category=item.category, fragile=item.fragile))
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
