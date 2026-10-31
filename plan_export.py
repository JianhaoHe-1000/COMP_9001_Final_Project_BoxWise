"""Export the current plan as a standalone, printable HTML snapshot."""

from datetime import datetime
from html import escape
import math
import os
from pathlib import Path
import tempfile


def build_plan_html(planner, packed):
    """Render existing assignments and packed marks without recalculating them."""
    if planner is None:
        raise ValueError("Generate or open a packing plan before exporting.")
    allocated = [item for box in planner.boxes for item in box.items]
    done_count = sum(item in packed for item in allocated)
    percent = round(100 * done_count / len(allocated)) if allocated else 0
    total_weight = math.fsum(box.total_weight() for box in planner.boxes)
    exported_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z")

    def text(value):
        return escape(str(value), quote=True)

    cards = []
    links = []
    for number, box in enumerate(planner.boxes, 1):
        rooms = ", ".join(sorted({item.room for item in box.items}))
        done = sum(item in packed for item in box.items)
        progress = round(100 * done / len(box.items)) if box.items else 0
        weight_percent = min(100, 100 * box.total_weight() / box.max_weight)
        badges = []
        if any(item.fragile for item in box.items):
            badges.append("FRAGILE · HANDLE WITH CARE")
        if any(item.category == "Liquid" for item in box.items):
            badges.append("LIQUID · KEEP UPRIGHT")
        if any(item.category == "Electronics" for item in box.items):
            badges.append("ELECTRONICS")
        if done == len(box.items):
            badges.append("PACKING COMPLETE")
        badge_html = "".join(f'<span class="badge">{text(badge)}</span>' for badge in badges)
        rows = []
        for item in box.items:
            status = "Packed" if item in packed else "To pack"
            status_class = "done" if item in packed else "pending"
            rows.append(f'''<tr><td><span class="status {status_class}">{status}</span></td>
                <td class="item-name">{text(item.name)}</td><td>{text(item.room)}</td>
                <td>{item.weight:g} kg</td><td>{text(item.category)}</td>
                <td>{"Yes" if item.fragile else "No"}</td></tr>''')
        links.append(f'<a href="#box-{number}">Box {text(box.box_id)}</a>')
        cards.append(f'''<section class="box" id="box-{number}">
            <div class="box-heading"><div><p class="eyebrow">PACKING LABEL</p>
            <h2>Box {text(box.box_id)}</h2><p class="rooms">{text(rooms)}</p></div>
            <div class="box-total">{box.total_weight():g}<small> / {box.max_weight:g} kg</small></div></div>
            <div class="badges">{badge_html}</div>
            <div class="bars"><div><div class="bar-title"><span>Weight capacity</span>
            <strong>{weight_percent:.0f}%</strong></div><div class="track"><div class="weight-fill" style="width:{weight_percent:.6f}%"></div></div></div>
            <div><div class="bar-title"><span>Packed items</span><strong>{done} / {len(box.items)}</strong></div>
            <div class="track"><div class="packed-fill" style="width:{progress}%"></div></div></div></div>
            <div class="table-wrap"><table><thead><tr><th>Status</th><th>Item</th><th>Room</th>
            <th>Weight</th><th>Category</th><th>Fragile</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>
            </section>''')
    rejected_rows = "".join(f'<li><strong>{text(item.name)}</strong> · {item.weight:g} kg — {text(reason)}</li>'
                            for item, reason in planner.unallocated)
    rejected_html = (f'<ul>{rejected_rows}</ul>' if planner.unallocated
                     else '<p>All items have been allocated to boxes.</p>')
    reasons = "".join(f'<li><strong>{text(item.name)}</strong><p>{text(reason)}</p></li>'
                      for item, reason in planner.decisions)
    css = """
        :root{--ink:#183b4b;--muted:#647a88;--teal:#087f7a;--line:#e1e9ed}
        *{box-sizing:border-box}html{scroll-behavior:smooth}
        body{margin:0;background:#f2f6f7;color:var(--ink);font:15px/1.6 'Segoe UI',Arial,sans-serif}
        main{max-width:1080px;margin:40px auto;padding:0 24px 40px}
        header{padding:38px 40px;background:#163a48;color:white;border-radius:20px;position:relative}
        header .eyebrow{color:#8edbd1}h1{font-size:38px;line-height:1.15;margin:8px 0 14px;letter-spacing:-1px}
        header p{margin:5px 0;color:#d3e4e8}.eyebrow{font-size:11px;letter-spacing:2px;font-weight:700;margin:0;color:var(--teal)}
        .snapshot{font-size:12px;opacity:.85}.metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:22px 0}
        .metric{background:white;border:1px solid var(--line);border-radius:14px;padding:20px}
        .metric span{display:block;font-size:11px;letter-spacing:1px;color:var(--muted);font-weight:700}
        .metric strong{font-size:31px;font-weight:650}.metric small{font-size:14px;color:var(--muted)}
        .overview{display:flex;gap:24px;justify-content:space-between;align-items:center;background:#e4f3ef;border-radius:12px;padding:18px 22px}
        .overview p{margin:3px 0}.overview .track{width:230px;height:9px}.note{font-size:13px;color:var(--muted)}
        nav{display:flex;gap:8px;flex-wrap:wrap;margin:22px 0}nav a{color:var(--ink);text-decoration:none;background:white;
        border:1px solid var(--line);border-radius:24px;padding:7px 17px}nav a:hover{background:#e4f3ef}
        .box{background:white;border:1px solid var(--line);border-radius:16px;margin:22px 0;overflow:hidden;scroll-margin-top:20px}
        .box-heading{display:flex;justify-content:space-between;align-items:center;padding:26px 28px 8px;border-top:5px solid #12877f}
        h2{font-size:26px;line-height:1.2;margin:6px 0}.rooms{margin:4px 0;color:var(--muted);overflow-wrap:anywhere}
        .box-total{font-size:29px;font-weight:600}.box-total small{font-size:15px;color:var(--muted);font-weight:400}
        .badges{padding:0 28px 12px;display:flex;gap:6px;flex-wrap:wrap}.badge{background:#eaf5f2;color:#136c62;border-radius:6px;padding:4px 9px;font-size:10px;font-weight:700;letter-spacing:.4px}
        .bars{display:grid;grid-template-columns:1fr 1fr;gap:24px;padding:0 28px 22px}.bar-title{display:flex;justify-content:space-between;font-size:12px;margin-bottom:6px;color:var(--muted)}
        .track{height:7px;background:#e8eff2;border-radius:6px;overflow:hidden}.weight-fill{height:100%;background:#6a9cb3}.packed-fill{height:100%;background:#12877f}
        .table-wrap{overflow:auto}table{width:100%;border-collapse:collapse;font-size:13px}th{background:#f7fafb;color:var(--muted);font-size:10px;text-transform:uppercase;letter-spacing:.7px;text-align:left;padding:12px 18px}
        td{padding:15px 18px;border-top:1px solid #edf1f3;vertical-align:top;overflow-wrap:anywhere}td.item-name{font-weight:600}
        .status{display:inline-block;border-radius:18px;padding:3px 9px;font-size:11px;white-space:nowrap}.done{background:#e2f4eb;color:#18714c}.pending{background:#f0f3f6;color:#647383}
        .section{background:white;border:1px solid var(--line);border-radius:16px;padding:25px 28px;margin:22px 0}
        .section h2{font-size:22px}.warning{background:#fff7ed;border-color:#f0dbbb}.section ul,.section ol{padding-left:22px}
        .section li{margin:12px 0;overflow-wrap:anywhere}.section li p{margin:3px 0;color:var(--muted);font-size:13px}
        footer{padding:15px 0;font-size:12px;color:var(--muted)}
        @media(max-width:650px){main{padding:0 12px;margin:16px auto}header{padding:25px}h1{font-size:30px}.metrics{grid-template-columns:repeat(2,1fr)}.overview{display:block}.overview .track{width:100%;margin-top:12px}.bars{grid-template-columns:1fr}.box-heading{align-items:start}.box-total{font-size:22px}td,th{padding:10px}}
        @media print{@page{size:A4;margin:14mm}body{background:white;font-size:11px}main{max-width:none;margin:0;padding:0}header{background:white;color:var(--ink);border:1px solid var(--line);padding:20px}header p,header .eyebrow{color:var(--muted)}h1{font-size:28px}nav,.print-tip{display:none}.metric{padding:12px}.metric strong{font-size:24px}.box{break-inside:avoid;border-radius:0}.table-wrap{overflow:visible}tr{break-inside:avoid}thead{display:table-header-group}td,th{padding:8px}.section{border-radius:0}.section li{break-inside:avoid}.track{border:1px solid #bccbd2}*{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
    """
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>BoxWise | Packing plan</title><style>{css}</style></head><body><main>
<header><p class="eyebrow">BOXWISE / PLAN · FIND · PACK</p><h1>Your packing plan.</h1>
<p>A clear view of every box, every item and your packing progress.</p>
<p class="snapshot">Snapshot exported {text(exported_at)} · Box limit {planner.max_weight:g} kg</p></header>
<div class="metrics"><div class="metric"><span>BOXES</span><strong>{len(planner.boxes)}</strong></div>
<div class="metric"><span>ALLOCATED ITEMS</span><strong>{len(allocated)}</strong></div>
<div class="metric"><span>UNALLOCATED</span><strong>{len(planner.unallocated)}</strong></div>
<div class="metric"><span>PACKED / ALLOCATED</span><strong>{done_count}<small> / {len(allocated)}</small></strong></div></div>
<div class="overview"><div><strong>{percent}% of allocated items packed</strong><p class="note">Total allocated weight: {total_weight:g} kg. Unallocated items are excluded from packing progress.</p></div>
<div class="track"><div class="packed-fill" style="width:{percent}%"></div></div></div>
<p class="note print-tip">Open this file in any browser. Press Ctrl+P (or Command+P) to print or save as PDF.</p>
<nav aria-label="Jump to a box">{"".join(links)}<a href="#unallocated">Unallocated</a><a href="#reasons">Allocation reasons</a></nav>
{"".join(cards)}<section class="section {'warning' if planner.unallocated else ''}" id="unallocated"><p class="eyebrow">REVIEW</p>
<h2>Unallocated items ({len(planner.unallocated)})</h2>{rejected_html}</section>
<section class="section" id="reasons"><p class="eyebrow">WHY THIS PLAN?</p><h2>Allocation decisions</h2>
<p class="note">Room order, then heavier items first. Same-room boxes are tried before other compatible boxes.</p><ol>{reasons}</ol></section>
<footer>This is a read-only snapshot of the existing plan and packed marks at export time. Later app changes do not update this file.
Use the BoxWise project JSON to resume editing. The plan is a rule-based suggestion; minimum box count and physical fit are not guaranteed.</footer>
</main></body></html>'''


def export_plan_html(path, planner, packed):
    """Write a self-contained UTF-8 report, replacing the destination on success."""
    document = build_plan_html(planner, packed)
    path = Path(path)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(document)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()
