# BoxWise — Moving & Packing Planner

A Python desktop application that helps people organise their belongings into moving boxes using clear packing rules.

## Run

1. Install Python 3 with Tkinter available.
2. Download this repository using **Code → Download ZIP**, then extract it.
3. Open a terminal in the extracted folder and run:

```text
python main.py
```

No third-party Python packages are required. The program uses Tkinter, CSV, JSON and other Python standard-library modules.

## Quick demonstration

1. Click **Load demo** to load the included `sample_items.csv`.
2. Open **Packing board**, keep the box limit at **5 kg**, and click **Generate plan**.
3. Click a box card to see its contents. Double-click an item to mark it packed.
4. In **Items & finder**, search for `Charger` and double-click the result to locate its box.
5. Use **Save project** to preserve assignments and packing progress, or **Export plan · HTML** to produce a report that opens in a browser.

## Features

- Add, edit, delete, search and filter item records.
- Generate a suggested packing plan with same-room preference.
- Inspect box cards, weights, care labels and allocation explanations.
- Track individual-item and whole-box packing progress.
- Import/export item CSV files and save/reopen complete JSON projects.
- Export the existing plan and current progress as a standalone HTML snapshot.

## Packing rules and limitations

- A box cannot exceed the specified weight limit.
- Liquids and electronics cannot share a box.
- A fragile item cannot share a box with another item weighing **3 kg or more**.
- Same-room items are preferred where compatible space allows.
- An item heavier than the box limit is left unallocated with a reason.

This is a practical rule-based suggestion. It does not model item dimensions or guarantee the minimum possible number of boxes. Packed marks are user-entered progress confirmations.

## Included runtime files

Keep `main.py`, `item.py`, `box.py`, `packing_planner.py`, `plan_export.py`, `project_storage.py`, `report.py`, `storage.py` and `sample_items.csv` together.

This is a local Tkinter application: the GitHub repository hosts the source code; viewing the repository does not run the desktop application in a browser. Download and run it locally to try the interactive features.
