"""BoxWise interactive packing workbench. Run with: python main.py"""

from pathlib import Path
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

from item import Item
from packing_planner import PackingPlanner
from plan_export import export_plan_html
from project_storage import load_project, save_project
from report import format_plan
from storage import load_items, save_items


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "others"
ROOM_COLORS = ("#138a86", "#6561ab", "#bc7331", "#3779ad", "#aa5275")


class BoxWiseApp:
    """Manage item editing, visual box inspection, progress and project files."""

    def __init__(self, root):
        self.root = root
        self.items = []
        self.planner = None
        self.packed = set()  # Item objects, so duplicate names remain independent.
        self.dirty = False
        self.file_path = None
        self.selected_box = None
        self.viewing_unallocated = False
        self._loading = False
        root.title("BoxWise - Packing Workbench")
        root.geometry(f"{min(1360, root.winfo_screenwidth()-60)}x{min(860, root.winfo_screenheight()-80)}")
        root.minsize(1080, 720)
        root.configure(bg="#eef3f7")
        style = ttk.Style(root)
        style.theme_use("clam")
        style.configure("TFrame", background="#eef3f7")
        style.configure("TLabel", background="#eef3f7", foreground="#20384b", font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=(10, 7))
        style.configure("TEntry", padding=6, fieldbackground="white", bordercolor="#d8e2e9")
        style.configure("TCombobox", padding=5, fieldbackground="white")
        style.configure("Accent.TButton", background="#117f80", foreground="white")
        style.map("Accent.TButton", background=[("active", "#086567")])
        style.configure("Treeview", rowheight=34, font=("Segoe UI", 10), background="white",
                        fieldbackground="white", borderwidth=0)
        style.map("Treeview", background=[("selected", "#d4ebe8")], foreground=[("selected", "#153f46")])
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#e7eef3", foreground="#466275", padding=(7, 9))
        style.configure("TNotebook", background="#eef3f7", borderwidth=0)
        style.configure("TNotebook.Tab", font=("Segoe UI", 11), padding=(20, 9))
        style.map("TNotebook.Tab", background=[("selected", "white"), ("!selected", "#e4ebef")],
                  foreground=[("selected", "#08776d"), ("!selected", "#607687")])
        style.configure("TLabelframe", background="#eef3f7")
        style.configure("TLabelframe.Label", background="#eef3f7", font=("Segoe UI", 10, "bold"))
        style.configure("Weight.Horizontal.TProgressbar", background="#6a9cb3", troughcolor="#e3ecf0", thickness=7)
        style.configure("Packed.Horizontal.TProgressbar", background="#138a86", troughcolor="#e3ecf0", thickness=7)
        self.name_var = tk.StringVar()
        self.room_var = tk.StringVar(value="Bedroom")
        self.weight_var = tk.StringVar()
        self.category_var = tk.StringVar(value="General")
        self.fragile_var = tk.BooleanVar(value=False)
        self.max_weight_var = tk.StringVar(value="5")
        self.search_var = tk.StringVar()
        self.room_filter = tk.StringVar(value="All rooms")
        self.file_status = tk.StringVar(value="New project | Not saved")
        self.item_status = tk.StringVar(value="0 items")
        self.plan_status = tk.StringVar(value="No plan generated")
        self.message = tk.StringVar(value="Load demo to explore, or add your own items.")
        self.metric_items = tk.StringVar(value="0")
        self.metric_boxes = tk.StringVar(value="—")
        self.metric_unallocated = tk.StringVar(value="—")
        self.metric_packed = tk.StringVar(value="0 / 0")
        self.detail_title = tk.StringVar(value="Choose a box")
        self.detail_subtitle = tk.StringVar(value="Click a box card to inspect its contents.")
        self.detail_reason = tk.StringVar(value="Select an item to read why it was placed here.")
        self._build_ui()
        self.max_weight_var.trace_add("write", self._capacity_changed)
        self.search_var.trace_add("write", lambda *args: self._refresh_items())
        self.room_filter.trace_add("write", lambda *args: self._refresh_items())
        root.protocol("WM_DELETE_WINDOW", self.close)
        self._refresh_all()

    def _build_ui(self):
        header = tk.Frame(self.root, bg="#17384b", padx=22, pady=17)
        header.pack(fill="x")
        logo = tk.Canvas(header, width=38, height=38, bg="#17384b", highlightthickness=0)
        logo.pack(side="left", padx=(0, 12))
        logo.create_polygon(3, 11, 19, 3, 35, 11, 19, 19, fill="#84d2c3", outline="")
        logo.create_polygon(3, 14, 17, 21, 17, 36, 3, 29, fill="#37a69c", outline="")
        logo.create_polygon(21, 21, 35, 14, 35, 29, 21, 36, fill="#b8e7dc", outline="")
        tk.Label(header, text="BOXWISE", font=("Segoe UI", 24, "bold"), bg="#17384b", fg="white").pack(side="left")
        tk.Label(header, text="A calmer move starts here.", font=("Segoe UI", 10), bg="#17384b", fg="#a9d4d5").pack(side="left", padx=24)
        ttk.Button(header, text="Save project", style="Accent.TButton", command=self.save_current_project).pack(side="right")
        ttk.Button(header, text="Open project", command=self.open_project).pack(side="right", padx=8)
        toolbar = ttk.Frame(self.root, padding=(18, 9))
        toolbar.pack(fill="x")
        self.demo_button = ttk.Button(toolbar, text="Load demo", command=self.load_demo)
        self.demo_button.pack(side="left")
        ttk.Button(toolbar, text="Import CSV", command=self.open_csv).pack(side="left", padx=7)
        ttk.Button(toolbar, text="Export CSV", command=self.save_csv).pack(side="left")
        self.export_button = ttk.Button(toolbar, text="Export plan · HTML", command=self.export_plan)
        self.export_button.pack(side="left", padx=7)
        ttk.Label(toolbar, textvariable=self.file_status).pack(side="right")
        metrics = ttk.Frame(self.root, padding=(18, 0, 18, 10))
        metrics.pack(fill="x")
        for column, (label, variable) in enumerate((("ITEMS", self.metric_items), ("BOXES", self.metric_boxes),
                    ("UNALLOCATED", self.metric_unallocated), ("PACKED / ALLOCATED", self.metric_packed))):
            metrics.columnconfigure(column, weight=1)
            tile = tk.Frame(metrics, bg="white", padx=17, pady=10,
                            highlightthickness=1, highlightbackground="#e1e8ed")
            tile.grid(row=0, column=column, sticky="ew", padx=(0, 8))
            tk.Label(tile, text=label, bg="white", fg="#62798a", font=("Segoe UI", 9, "bold")).pack(anchor="w")
            metric_color = "#117f80" if column == 3 else ("#a96831" if column == 2 else "#17384b")
            tk.Label(tile, textvariable=variable, bg="white", fg=metric_color, font=("Segoe UI", 23, "bold")).pack(anchor="w")
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=18)
        self.items_tab = ttk.Frame(self.notebook, padding=12)
        self.board_tab = ttk.Frame(self.notebook, padding=12)
        self.report_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.items_tab, text="1   Items & finder")
        self.notebook.add(self.board_tab, text="2   Packing board")
        self.notebook.add(self.report_tab, text="3   Reasons & report")
        self._build_items_tab()
        self._build_board_tab()
        report_actions = ttk.Frame(self.report_tab, padding=(0, 0, 0, 10))
        report_actions.pack(fill="x")
        ttk.Label(report_actions, text="Your current plan, ready to read or share.", font=("Segoe UI", 11, "bold")).pack(side="left")
        self.report_export_button = ttk.Button(report_actions, text="Export plan · HTML", style="Accent.TButton", command=self.export_plan)
        self.report_export_button.pack(side="right")
        self.report_text = ScrolledText(self.report_tab, wrap="word", font=("Segoe UI", 10), relief="flat", padx=16, pady=12)
        self.report_text.pack(fill="both", expand=True)
        ttk.Label(self.root, textvariable=self.message, padding=(18, 9)).pack(fill="x")

    def _build_items_tab(self):
        form = ttk.LabelFrame(self.items_tab, text="Item details — Add creates a record; Update edits the selected one", padding=10)
        form.pack(fill="x")
        fields = (("Item name", self.name_var), ("Room", self.room_var), ("Weight (kg)", self.weight_var), ("Category", self.category_var))
        for column, (label, variable) in enumerate(fields):
            form.columnconfigure(column, weight=1)
            ttk.Label(form, text=label).grid(row=0, column=column, sticky="w", padx=4)
            if column == 1:
                control = ttk.Combobox(form, textvariable=variable, values=("Bedroom", "Bathroom", "Kitchen", "Living room", "Study"), width=16)
            elif column == 3:
                control = ttk.Combobox(form, textvariable=variable, values=Item.CATEGORIES, state="readonly", width=16)
            else:
                control = ttk.Entry(form, textvariable=variable, width=18)
            control.grid(row=1, column=column, sticky="ew", padx=4, pady=5)
            if column == 0:
                self.name_entry = control
        actions = ttk.Frame(form)
        actions.grid(row=2, column=0, columnspan=4, sticky="ew", pady=(5, 0))
        ttk.Checkbutton(actions, text="Fragile", variable=self.fragile_var).pack(side="left", padx=(0, 12))
        self.add_button = ttk.Button(actions, text="Add item", style="Accent.TButton", command=self.add_item)
        self.add_button.pack(side="left")
        self.update_button = ttk.Button(actions, text="Update selected", command=self.update_item)
        self.update_button.pack(side="left", padx=6)
        ttk.Button(actions, text="Clear form", command=self.clear_form).pack(side="left")
        self.delete_button = ttk.Button(actions, text="Delete selected", command=self.delete_item)
        self.delete_button.pack(side="right")
        finder = ttk.Frame(self.items_tab, padding=(0, 12))
        finder.pack(fill="x")
        ttk.Label(finder, text="Find item").pack(side="left")
        self.search_entry = ttk.Entry(finder, textvariable=self.search_var, width=25)
        self.search_entry.pack(side="left", padx=8)
        self.room_combo = ttk.Combobox(finder, textvariable=self.room_filter, state="readonly", width=18)
        self.room_combo.pack(side="left")
        ttk.Button(finder, text="Clear filters", command=self.clear_filters).pack(side="left", padx=8)
        ttk.Label(finder, textvariable=self.item_status).pack(side="right")
        self.tree = self._table(self.items_tab, (("name", "Item", 160), ("room", "Room", 110),
            ("weight", "kg", 60), ("category", "Category", 100), ("fragile", "Fragile", 65),
            ("location", "Location", 110), ("progress", "Packing status", 120)))
        self.tree.bind("<<TreeviewSelect>>", self._selection_changed)
        self.tree.bind("<Double-1>", lambda event: self.locate_selected())
        self.tree.tag_configure("packed", foreground="#08776d")
        self.tree.tag_configure("unallocated", foreground="#ab5727")
        bottom = ttk.Frame(self.items_tab, padding=(0, 8, 0, 0))
        bottom.pack(fill="x")
        self.locate_button = ttk.Button(bottom, text="Show selected item in its box →", command=self.locate_selected)
        self.locate_button.pack(side="left")
        ttk.Label(bottom, text="Search names; room filters never change the plan.").pack(side="right")

    def _build_board_tab(self):
        controls = ttk.Frame(self.board_tab)
        controls.pack(fill="x", pady=(0, 10))
        ttk.Label(controls, text="Box limit (kg)").pack(side="left")
        ttk.Entry(controls, textvariable=self.max_weight_var, width=7).pack(side="left", padx=8)
        self.generate_button = ttk.Button(controls, text="Generate plan", style="Accent.TButton", command=self.generate_plan)
        self.generate_button.pack(side="left")
        ttk.Label(controls, textvariable=self.plan_status).pack(side="right")
        panels = ttk.Panedwindow(self.board_tab, orient="horizontal")
        panels.pack(fill="both", expand=True)
        card_panel = ttk.Frame(panels, width=365)
        detail_panel = ttk.Frame(panels, padding=(16, 0, 0, 0))
        panels.add(card_panel, weight=1)
        panels.add(detail_panel, weight=2)
        self.card_canvas = tk.Canvas(card_panel, bg="#eef3f7", highlightthickness=0, width=340)
        scroll = ttk.Scrollbar(card_panel, orient="vertical", command=self.card_canvas.yview)
        self.card_canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.card_canvas.pack(side="left", fill="both", expand=True)
        self.cards = ttk.Frame(self.card_canvas)
        self.cards_window = self.card_canvas.create_window((0, 0), window=self.cards, anchor="nw")
        self.cards.bind("<Configure>", lambda event: self.card_canvas.configure(scrollregion=self.card_canvas.bbox("all")))
        self.card_canvas.bind("<Configure>", lambda event: self.card_canvas.itemconfigure(self.cards_window, width=event.width))
        ttk.Label(detail_panel, textvariable=self.detail_title, font=("Segoe UI", 18, "bold")).pack(anchor="w")
        ttk.Label(detail_panel, textvariable=self.detail_subtitle).pack(anchor="w", pady=(3, 9))
        self.detail_tree = self._table(detail_panel, (("packed", "Packed", 70), ("name", "Item", 140),
            ("room", "Room", 110), ("weight", "kg", 60), ("care", "Care", 100)))
        self.detail_tree.bind("<Double-1>", lambda event: self.toggle_packed())
        self.detail_tree.bind("<Return>", lambda event: self.toggle_packed())
        self.detail_tree.bind("<<TreeviewSelect>>", self._detail_selection)
        self.detail_tree.tag_configure("packed", foreground="#08776d")
        actions = ttk.Frame(detail_panel, padding=(0, 9))
        actions.pack(fill="x")
        self.toggle_button = ttk.Button(actions, text="Toggle selected packed", command=self.toggle_packed)
        self.toggle_button.pack(side="left")
        self.box_progress_button = ttk.Button(actions, text="Mark box packed", command=self.toggle_box_packed)
        self.box_progress_button.pack(side="left", padx=7)
        ttk.Label(detail_panel, text="Double-click an item, or press Enter, to toggle its packed state.").pack(anchor="w")
        ttk.Label(detail_panel, textvariable=self.detail_reason, wraplength=580).pack(anchor="w", pady=(10, 0))

    def _table(self, parent, columns):
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True)
        tree = ttk.Treeview(frame, columns=[column[0] for column in columns], show="headings", selectmode="browse", height=6)
        for name, label, width in columns:
            tree.heading(name, text=label)
            tree.column(name, width=width, minwidth=50)
        vertical = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        tree.tag_configure("alternate", background="#f5f8fa")
        tree.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        return tree

    def _plan_current(self):
        try:
            return self.planner is not None and float(self.max_weight_var.get()) == self.planner.max_weight
        except ValueError:
            return False

    def _locations(self):
        if not self._plan_current():
            return {}
        return {item: box for box in self.planner.boxes for item in box.items}

    def _set_report(self, text):
        self.report_text.configure(state="normal")
        self.report_text.delete("1.0", "end")
        self.report_text.insert("1.0", text)
        self.report_text.configure(state="disabled")

    def _refresh_all(self):
        self._refresh_items()
        self._render_board()
        current = self._plan_current()
        for button in (self.export_button, self.report_export_button):
            button.configure(state="normal" if current else "disabled")
        allocated = sum(len(box.items) for box in self.planner.boxes) if current else 0
        self.metric_items.set(str(len(self.items)))
        self.metric_boxes.set(str(len(self.planner.boxes)) if current else "—")
        self.metric_unallocated.set(str(len(self.planner.unallocated)) if current else "—")
        self.metric_packed.set(f"{len(self.packed) if current else 0} / {allocated}")
        if current:
            self.plan_status.set(f"{len(self.planner.boxes)} boxes | {len(self.planner.unallocated)} unallocated")
            self._set_report(format_plan(self.planner) + f"\n\nPACKING PROGRESS\n{len(self.packed)} / {allocated} allocated items packed.")
        else:
            self.plan_status.set("Generate a current plan")
            self._set_report("No current plan. Open the Packing board and click Generate plan.")

    def _refresh_items(self):
        selected = self.tree.selection()
        self.tree.delete(*self.tree.get_children())
        locations = self._locations()
        query = self.search_var.get().strip().casefold()
        room = self.room_filter.get()
        rooms = sorted({item.room for item in self.items})
        self.room_combo.configure(values=["All rooms"] + rooms)
        for index, item in enumerate(self.items):
            if query not in item.name.casefold() or (room != "All rooms" and room != item.room):
                continue
            location = f"Box {locations[item].box_id}" if item in locations else ("Unallocated" if self._plan_current() else "No current plan")
            status = "Packed" if item in self.packed and item in locations else ("To pack" if item in locations else "—")
            tag = "packed" if item in self.packed and item in locations else ("unallocated" if location == "Unallocated" else "")
            self.tree.insert("", "end", iid=str(index), values=(item.name, item.room, f"{item.weight:g}",
                             item.category, "Yes" if item.fragile else "No", location, status),
                             tags=(tag, "alternate" if index % 2 else ""))
        if selected and self.tree.exists(selected[0]):
            self.tree.selection_set(selected[0])
        self.item_status.set(f"{len(self.tree.get_children())} shown / {len(self.items)} items")
        filename = self.file_path.name if self.file_path else "New project"
        suffix = " | Unsaved changes" if self.dirty else (" | Saved" if self.file_path else " | Not saved")
        self.file_status.set(filename + suffix)

    def _render_board(self):
        for child in self.cards.winfo_children():
            child.destroy()
        if not self._plan_current():
            ttk.Label(self.cards, text="Ready when you are.\n\nAdd items, set the limit,\nthen generate your packing plan.", padding=15).pack(anchor="w")
            self._show_box(None)
            return
        rooms = sorted({item.room for item in self.items})
        colors = {room: ROOM_COLORS[index % len(ROOM_COLORS)] for index, room in enumerate(rooms)}
        for box in self.planner.boxes:
            packed_count = sum(item in self.packed for item in box.items)
            card = tk.Frame(self.cards, bg="white", highlightthickness=2,
                            highlightbackground="#117f80" if self.selected_box == box.box_id else "#e1e8ed", padx=15, pady=13)
            card.pack(fill="x", padx=(0, 8), pady=(0, 12))
            room_names = sorted({item.room for item in box.items})
            tk.Frame(card, bg=colors[room_names[0]], height=4).pack(fill="x", pady=(0, 7))
            tk.Label(card, text=f"BOX {box.box_id}   ·   {packed_count}/{len(box.items)} packed", bg="white",
                     fg="#17384b", font=("Segoe UI", 12, "bold")).pack(anchor="w")
            tk.Label(card, text=", ".join(room_names), bg="white", fg="#60798a", wraplength=300, justify="left").pack(anchor="w", pady=3)
            tk.Label(card, text=f"Weight: {box.total_weight():g} / {box.max_weight:g} kg", bg="white", fg="#60798a").pack(anchor="w")
            ttk.Progressbar(card, style="Weight.Horizontal.TProgressbar", maximum=box.max_weight,
                            value=box.total_weight()).pack(fill="x", pady=(4, 7))
            tk.Label(card, text=f"Packing progress: {packed_count} of {len(box.items)} items", bg="white",
                     fg="#117f80", font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 4))
            ttk.Progressbar(card, style="Packed.Horizontal.TProgressbar", maximum=len(box.items),
                            value=packed_count).pack(fill="x", pady=(0, 6))
            labels = []
            if any(item.fragile for item in box.items):
                labels.append("FRAGILE")
            if any(item.category == "Liquid" for item in box.items):
                labels.append("LIQUID · UPRIGHT")
            if any(item.category == "Electronics" for item in box.items):
                labels.append("ELECTRONICS")
            if packed_count == len(box.items):
                labels.append("COMPLETE")
            tk.Label(card, text="  |  ".join(labels) or "GENERAL", bg="white", fg="#117f80", wraplength=300, justify="left").pack(anchor="w")
            # Clicking the card, its labels or progress bars opens the same box.
            for widget in [card] + card.winfo_children():
                widget.bind("<Button-1>", lambda event, box_id=box.box_id: self.open_box(box_id))
                widget.bind("<MouseWheel>", self._scroll_cards)
        if self.planner.unallocated:
            ttk.Button(self.cards, text=f"!  {len(self.planner.unallocated)} unallocated — review",
                       command=self.open_unallocated).pack(fill="x", padx=(0, 8), pady=4)
        if self.viewing_unallocated:
            self._show_unallocated()
        else:
            box = next((box for box in self.planner.boxes if box.box_id == self.selected_box), None)
            self._show_box(box)

    def _scroll_cards(self, event):
        self.card_canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")
        return "break"

    def _show_box(self, box, focus_index=None):
        previous = self.detail_tree.selection()
        self.detail_tree.delete(*self.detail_tree.get_children())
        self.detail_reason.set("Select an item to read its allocation reason.")
        enabled = box is not None and self._plan_current()
        self.toggle_button.configure(state="normal" if enabled else "disabled")
        self.box_progress_button.configure(state="normal" if enabled else "disabled")
        if not enabled:
            self.detail_title.set("Choose a box")
            self.detail_subtitle.set("Generate a plan, then click a box card.")
            return
        self.detail_title.set(f"Box {box.box_id}")
        packed_count = sum(item in self.packed for item in box.items)
        self.detail_subtitle.set(f"{box.total_weight():g} / {box.max_weight:g} kg  ·  {packed_count}/{len(box.items)} packed")
        self.box_progress_button.configure(text="Unpack whole box" if packed_count == len(box.items) else "Mark whole box packed")
        indexes = {item: index for index, item in enumerate(self.items)}
        for item in box.items:
            done = item in self.packed
            care = "Fragile" if item.fragile else item.category
            self.detail_tree.insert("", "end", iid=str(indexes[item]), values=("[x]" if done else "[ ]", item.name,
                                    item.room, f"{item.weight:g}", care), tags=("packed" if done else "",))
        selection = str(focus_index) if focus_index is not None else (previous[0] if previous else None)
        if selection is not None and self.detail_tree.exists(selection):
            self.detail_tree.selection_set(selection)
            self.detail_tree.see(selection)

    def _show_unallocated(self):
        self._show_box(None)
        self.detail_title.set("Unallocated items")
        self.detail_subtitle.set("These items exceed the box limit. They cannot be marked packed.")
        indexes = {item: index for index, item in enumerate(self.items)}
        for item, reason in self.planner.unallocated:
            self.detail_tree.insert("", "end", iid=str(indexes[item]), values=("—", item.name, item.room, f"{item.weight:g}", "Over limit"))

    def open_box(self, box_id):
        self.selected_box = box_id
        self.viewing_unallocated = False
        self._render_board()

    def open_unallocated(self):
        if self._plan_current():
            self.selected_box = None
            self.viewing_unallocated = True
            self._render_board()

    def _detail_selection(self, event=None):
        selection = self.detail_tree.selection()
        if selection and self._plan_current():
            item = self.items[int(selection[0])]
            reason = next((text for candidate, text in self.planner.decisions if candidate is item), "")
            self.detail_reason.set(reason.strip())

    def toggle_packed(self):
        selection = self.detail_tree.selection()
        if not selection or not self._plan_current() or self.viewing_unallocated:
            return
        item = self.items[int(selection[0])]
        if item not in self._locations():
            return
        if item in self.packed:
            self.packed.remove(item)
        else:
            self.packed.add(item)
        self.dirty = True
        self._refresh_all()
        self.message.set(f"{item.name}: {'packed' if item in self.packed else 'not packed'}. Save project to keep progress.")

    def toggle_box_packed(self):
        if not self._plan_current() or self.viewing_unallocated:
            return
        box = next((box for box in self.planner.boxes if box.box_id == self.selected_box), None)
        if box is None:
            return
        if all(item in self.packed for item in box.items):
            self.packed.difference_update(box.items)
        else:
            self.packed.update(box.items)
        self.dirty = True
        self._refresh_all()
        self.message.set("Box progress updated. Save project to keep it.")

    def locate_selected(self):
        index = self._selected_index()
        if index is None:
            return
        if not self._plan_current():
            messagebox.showinfo("Generate a plan", "Generate a current plan before locating items.", parent=self.root)
            return
        item = self.items[index]
        box = self._locations().get(item)
        self.notebook.select(self.board_tab)
        if box is None:
            self.open_unallocated()
        else:
            self.open_box(box.box_id)
        if self.detail_tree.exists(str(index)):
            self.detail_tree.selection_set(str(index))
            self.detail_tree.see(str(index))
            self._detail_selection()
        self.message.set(f"Found {item.name}: {'Box '+str(box.box_id) if box else 'unallocated' }.")

    def clear_filters(self):
        self.search_var.set("")
        self.room_filter.set("All rooms")

    def _invalidate_plan(self):
        self.planner = None
        self.packed.clear()
        self.selected_box = None
        self.viewing_unallocated = False

    def _capacity_changed(self, *args):
        if not self._loading:
            self.dirty = True
            self._refresh_all()
            self.message.set("Capacity changed. Generate again, or restore the old value to keep the previous plan and progress.")

    def _allow_plan_reset(self):
        return not self.packed or messagebox.askyesno("Reset packing progress?",
            "This operation replaces the plan and resets all packed marks. Continue?", parent=self.root)

    def _form_item(self):
        return Item(self.name_var.get(), self.room_var.get(), self.weight_var.get(), self.category_var.get(), self.fragile_var.get())

    def _selected_index(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Select an item", "Select an item in the list first.", parent=self.root)
            return None
        return int(selection[0])

    def _selection_changed(self, event=None):
        selection = self.tree.selection()
        if selection and int(selection[0]) < len(self.items):
            item = self.items[int(selection[0])]
            self.name_var.set(item.name)
            self.room_var.set(item.room)
            self.weight_var.set(str(item.weight))
            self.category_var.set(item.category)
            self.fragile_var.set(item.fragile)

    def clear_form(self):
        self.tree.selection_remove(*self.tree.selection())
        self.name_var.set("")
        self.room_var.set("Bedroom")
        self.weight_var.set("")
        self.category_var.set("General")
        self.fragile_var.set(False)
        self.name_entry.focus_set()

    def _items_changed(self, message):
        self.dirty = True
        self._invalidate_plan()
        self.clear_form()
        self.clear_filters()
        self._refresh_all()
        self.message.set(message + " Generate a fresh plan on the Packing board.")

    def add_item(self):
        try:
            item = self._form_item()
        except ValueError as error:
            messagebox.showerror("Invalid item", str(error), parent=self.root)
            return
        if self._allow_plan_reset():
            self.items.append(item)
            self._items_changed(f"Added {item.name}.")

    def update_item(self):
        index = self._selected_index()
        if index is None:
            return
        try:
            item = self._form_item()
        except ValueError as error:
            messagebox.showerror("Invalid item", str(error), parent=self.root)
            return
        if self._allow_plan_reset():
            self.items[index] = item
            self._items_changed(f"Updated {item.name}.")

    def delete_item(self):
        index = self._selected_index()
        if index is None:
            return
        item = self.items[index]
        note = " This also resets the plan and all packed marks." if self.packed else ""
        if messagebox.askyesno("Delete item", f"Delete {item.name}?" + note, parent=self.root):
            self.items.pop(index)
            self._items_changed(f"Deleted {item.name}.")

    def generate_plan(self):
        try:
            planner = PackingPlanner(self.max_weight_var.get())
        except ValueError as error:
            messagebox.showerror("Invalid box capacity", str(error), parent=self.root)
            return
        if not self.items:
            messagebox.showinfo("No items", "Add items or load a CSV before generating a plan.", parent=self.root)
            return
        if not self._allow_plan_reset():
            return
        planner.generate_plan(self.items)
        self.planner = planner
        self.packed.clear()
        self.selected_box = planner.boxes[0].box_id if planner.boxes else None
        self.viewing_unallocated = not planner.boxes and bool(planner.unallocated)
        self.dirty = True
        self._refresh_all()
        self.notebook.select(self.board_tab)
        self.card_canvas.yview_moveto(0)
        self.message.set("Plan ready. Click a box, then double-click items to mark them packed.")

    def _confirm_unsaved(self):
        if not self.dirty:
            return True
        answer = messagebox.askyesnocancel("Unsaved project", "Save the current project and packing progress before continuing?", parent=self.root)
        if answer is None:
            return False
        return self.save_current_project() if answer else True

    def _load_path(self, path):
        try:
            items = load_items(path)
        except (OSError, ValueError, UnicodeError) as error:
            messagebox.showerror("Cannot open CSV", str(error), parent=self.root)
            return
        if not self._confirm_unsaved():
            return
        self.items = items
        self._invalidate_plan()
        self.file_path = None
        self.dirty = True
        self.clear_filters()
        self.clear_form()
        self._refresh_all()
        self.message.set(f"Imported {len(items)} items. Save project to keep plans and progress; CSV stores only items.")

    def open_csv(self):
        path = filedialog.askopenfilename(parent=self.root, title="Import item CSV", initialdir=DATA_DIR,
                                          filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
        if path:
            self._load_path(path)

    def load_demo(self):
        self._load_path(PROJECT_DIR / "sample_items.csv")

    def save_csv(self):
        path = filedialog.asksaveasfilename(parent=self.root, title="Export items only", initialdir=DATA_DIR,
                                           initialfile="my_items.csv", defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if not path:
            return False
        try:
            save_items(path, self.items)
        except OSError as error:
            messagebox.showerror("Cannot save CSV", str(error), parent=self.root)
            return False
        self.message.set("Items exported. Use Save project to preserve the plan and packing progress.")
        return True

    def export_plan(self):
        """Export the exact current plan; do not regenerate or change progress."""
        if not self._plan_current():
            messagebox.showinfo("No current plan", "Generate or open a current plan before exporting. Restore the original box limit if it has changed.", parent=self.root)
            return False
        path = filedialog.asksaveasfilename(parent=self.root, title="Export current packing plan",
            initialdir=DATA_DIR, initialfile="BoxWise_packing_plan.html", defaultextension=".html",
            filetypes=[("HTML report — double-click to view", "*.html")])
        if not path:
            return False
        try:
            export_plan_html(path, self.planner, self.packed)
        except OSError as error:
            messagebox.showerror("Cannot export plan", str(error), parent=self.root)
            return False
        self.message.set(f"Plan exported to {path}. This snapshot can be opened in any browser.")
        try:
            opened = webbrowser.open(Path(path).resolve().as_uri())
        except (OSError, webbrowser.Error):
            opened = False
        if not opened:
            messagebox.showinfo("Plan exported", f"Saved successfully:\n{path}\n\nDouble-click the HTML file to view it in a browser.", parent=self.root)
        return True

    def save_current_project(self):
        if self.packed and not self._plan_current():
            messagebox.showerror("Previous plan is stale", "Restore the previous capacity to keep progress, or regenerate and confirm its reset before saving.", parent=self.root)
            return False
        try:
            PackingPlanner(self.max_weight_var.get())
        except ValueError as error:
            messagebox.showerror("Invalid box capacity", str(error), parent=self.root)
            return False
        path = filedialog.asksaveasfilename(parent=self.root, title="Save BoxWise project", initialdir=DATA_DIR,
            initialfile=self.file_path.name if self.file_path else "my_move.boxwise.json", defaultextension=".json",
            filetypes=[("BoxWise project", "*.json")])
        if not path:
            return False
        try:
            save_project(path, self.items, self.max_weight_var.get(), self.planner if self._plan_current() else None, self.packed)
        except (OSError, ValueError) as error:
            messagebox.showerror("Cannot save project", str(error), parent=self.root)
            return False
        self.file_path = Path(path)
        self.dirty = False
        self._refresh_items()
        self.message.set("Project saved with the current plan and packing progress." if self._plan_current()
                         else "Project saved without a plan. Generate one when ready.")
        return True

    def open_project(self):
        path = filedialog.askopenfilename(parent=self.root, title="Open BoxWise project", initialdir=DATA_DIR,
                                          filetypes=[("BoxWise project", "*.json")])
        if not path:
            return
        try:
            items, capacity, planner, packed = load_project(path)
        except (OSError, ValueError, UnicodeError) as error:
            messagebox.showerror("Cannot open project", str(error), parent=self.root)
            return
        if not self._confirm_unsaved():
            return
        self.items, self.planner, self.packed = items, planner, packed
        self._loading = True
        try:
            self.max_weight_var.set(f"{capacity:g}")
        finally:
            self._loading = False
        self.file_path = Path(path)
        self.dirty = False
        self.selected_box = planner.boxes[0].box_id if planner and planner.boxes else None
        self.viewing_unallocated = bool(planner and not planner.boxes and planner.unallocated)
        self.clear_filters()
        self.clear_form()
        self._refresh_all()
        self.notebook.select(self.board_tab if planner else self.items_tab)
        self.message.set("Project restored, including exact assignments and packed marks.")

    def close(self):
        if self._confirm_unsaved():
            self.root.destroy()


def main():
    root = tk.Tk()
    BoxWiseApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
