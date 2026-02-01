"""
Interior Quotation Generator – Space_Craft style with material-based pricing.
Room-wise woodwork + false ceiling; materials DB; grade + materials dropdown per section.
Run: streamlit run quotation_app.py (from space-cut folder)
"""
import streamlit as st
import pandas as pd
import json
import os
import uuid
from io import BytesIO
from datetime import datetime, date
from openpyxl import load_workbook

st.set_page_config(page_title="Interior Quotation", layout="wide")

# --- Paths ---
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
MATERIALS_DB_PATH = os.path.join(DATA_DIR, "materials_db.json")
PROJECTS_PATH = os.path.join(DATA_DIR, "projects.json")

# --- Dropdown options ---
ROOMS = [
    "Living Room",
    "Kitchen",
    "MBR (Master Bedroom)",
    "Kids Bedroom",
    "Guest Bedroom",
    "Dining",
]
# Items per room (Item dropdown filters by selected Room)
ROOM_ITEMS = {
    "Living Room": [
        "Tv Unit Full Wall Panel",
        "Tv Unit Vertical Box",
        "Tv Unit Base Box",
        "Pooja Mandir",
        "Partition",
        "Other",
    ],
    "Kitchen": [
        "Base Box",
        "Loft",
        "Middle Box",
        "Tall Unit",
        "Partition",
        "Other",
    ],
    "MBR (Master Bedroom)": [
        "Wardrobe",
        "Wardrobe Loft",
        "Study",
        "Dressing Table",
        "Partition",
        "Other",
    ],
    "Kids Bedroom": [
        "Wardrobe + Study",
        "Wardrobe Loft",
        "Dressing Table",
        "Study",
        "Partition",
        "Other",
    ],
    "Guest Bedroom": [
        "Wardrobe",
        "Wardrobe Loft",
        "Dressing Table",
        "Partition",
        "Other",
    ],
    "Dining": [
        "Partition",
        "Workstation",
        "Other",
    ],
}
WOODWORK_ITEMS_ALL = [
    "Tv Unit Full Wall Panel", "Tv Unit Vertical Box", "Tv Unit Base Box", "Pooja Mandir",
    "Base Box", "Loft", "Middle Box", "Tall Unit",
    "Wardrobe", "Wardrobe Loft", "Wardrobe + Study", "Study", "Dressing Table",
    "Partition", "Workstation", "Other",
]
MATERIAL_GRADES = ["Premium", "Standard", "Basic"]
FALSE_CEILING_PLACES = ROOMS + ["Painting"]
PER_SFT_CEILING_OPTIONS = [25, 75, 100]


def get_items_for_room(room):
    return ROOM_ITEMS.get(room, WOODWORK_ITEMS_ALL)


def load_materials_db():
    if not os.path.exists(MATERIALS_DB_PATH):
        return {"materials": [], "item_defaults": {}}
    with open(MATERIALS_DB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_materials_db(db):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(MATERIALS_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2)


def get_materials_by_grade(db, grade=None):
    mats = db.get("materials", [])
    if grade:
        return [m for m in mats if m.get("grade") == grade]
    return mats


def get_material_by_id(db, mid):
    for m in db.get("materials", []):
        if m.get("id") == mid:
            return m
    return None


def rate_per_sft_for_selection(db, material_ids):
    total = 0
    for mid in material_ids:
        m = get_material_by_id(db, mid)
        if m:
            total += float(m.get("rate_per_sft", 0))
    return total


def default_material_ids_for_item(db, item):
    defaults = db.get("item_defaults", {}).get(item, [])
    all_ids = [m["id"] for m in db.get("materials", [])]
    return [d for d in defaults if d in all_ids]


# --- Projects save/load ---
def load_projects():
    if not os.path.exists(PROJECTS_PATH):
        return []
    with open(PROJECTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_projects(projects):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(PROJECTS_PATH, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2)


def load_project_into_session(project):
    """Load a saved project into session state so form and tables show its data."""
    st.session_state["project_name"] = project.get("project_name", "")
    st.session_state["location"] = project.get("location", "")
    st.session_state["margin_pct"] = float(project.get("margin_pct", 0))
    st.session_state["discount_pct"] = float(project.get("discount_pct", 0))
    st.session_state["woodwork_rows"] = project.get("woodwork_rows", [])
    st.session_state["ceiling_rows"] = project.get("ceiling_rows", [])
    qd = project.get("quote_date")
    if isinstance(qd, str):
        try:
            st.session_state["qdate"] = date.fromisoformat(qd[:10])
        except Exception:
            st.session_state["qdate"] = datetime.now().date()
    else:
        st.session_state["qdate"] = datetime.now().date()
    st.session_state["validity"] = project.get("validity", "30 days")
    st.session_state["current_project_id"] = project.get("id", "")


# --- Session state ---
if "woodwork_rows" not in st.session_state:
    st.session_state["woodwork_rows"] = []
if "ceiling_rows" not in st.session_state:
    st.session_state["ceiling_rows"] = []
if "current_project_id" not in st.session_state:
    st.session_state["current_project_id"] = None

# Load materials DB once per run
materials_db = load_materials_db()

# --- Header ---
st.title("Interior Work Breakdown – Quotation")
st.caption("Room-wise woodwork and false ceiling. Select materials per section; price = sft × sum(material rates).")

# --- Open / Save / Delete project ---
projects_list = load_projects()
project_options = ["— New project —"] + [
    f"{p.get('project_name', 'Untitled')} | {p.get('location', '')} | {p.get('updated_at', '')[:10]}"
    for p in projects_list
]
project_ids = [None] + [p.get("id") for p in projects_list]

col_open, col_save, col_del = st.columns([2, 1, 1])
with col_open:
    current_pid = st.session_state.get("current_project_id")
    default_idx = next((i for i, pid in enumerate(project_ids) if pid == current_pid), 0)
    selected_label = st.selectbox(
        "Open saved project",
        project_options,
        index=default_idx,
        key="open_project",
        help="Select a flat to resume editing. Data loads below.",
    )
    selected_idx = project_options.index(selected_label) if selected_label in project_options else 0
    if selected_idx == 0:
        if current_pid is not None:
            st.session_state["current_project_id"] = None
            st.session_state["open_project"] = project_options[0]
            st.rerun()
    elif selected_idx > 0 and project_ids[selected_idx]:
        if current_pid != project_ids[selected_idx]:
            load_project_into_session(projects_list[selected_idx - 1])
            st.session_state["current_project_id"] = project_ids[selected_idx]
            st.session_state["open_project"] = project_options[selected_idx]
            st.rerun()
with col_save:
    if st.button("Save project", type="primary", help="Save current quote so you can resume later."):
        project_name = st.session_state.get("project_name", "")
        location = st.session_state.get("location", "")
        margin_pct = st.session_state.get("margin_pct", 0.0)
        discount_pct = st.session_state.get("discount_pct", 0.0)
        qdate = st.session_state.get("qdate", datetime.now().date())
        validity = st.session_state.get("validity", "30 days")
        woodwork_rows = st.session_state.get("woodwork_rows", [])
        ceiling_rows = st.session_state.get("ceiling_rows", [])
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
        pid = st.session_state.get("current_project_id")
        projects = load_projects()
        if pid and any(p.get("id") == pid for p in projects):
            for p in projects:
                if p.get("id") == pid:
                    p.update({
                        "project_name": project_name or "Untitled",
                        "location": location,
                        "margin_pct": margin_pct,
                        "discount_pct": discount_pct,
                        "quote_date": str(qdate),
                        "validity": validity,
                        "woodwork_rows": woodwork_rows,
                        "ceiling_rows": ceiling_rows,
                        "updated_at": updated_at,
                    })
                    break
        else:
            pid = str(uuid.uuid4())[:8]
            projects.append({
                "id": pid,
                "project_name": project_name or "Untitled",
                "location": location,
                "margin_pct": margin_pct,
                "discount_pct": discount_pct,
                "quote_date": str(qdate),
                "validity": validity,
                "woodwork_rows": woodwork_rows,
                "ceiling_rows": ceiling_rows,
                "updated_at": updated_at,
            })
            st.session_state["current_project_id"] = pid
        save_projects(projects)
        st.success("Project saved. You can open it later from the dropdown.")
        st.rerun()
with col_del:
    if st.session_state.get("current_project_id") and st.button("Delete this project", help="Remove saved project from list."):
        pid = st.session_state["current_project_id"]
        projects = [p for p in load_projects() if p.get("id") != pid]
        save_projects(projects)
        st.session_state["current_project_id"] = None
        st.session_state["project_name"] = ""
        st.session_state["location"] = ""
        st.session_state["woodwork_rows"] = []
        st.session_state["ceiling_rows"] = []
        st.success("Project removed.")
        st.rerun()

# --- Project info ---
with st.expander("Project / Client details", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        project_name = st.text_input(
            "Flat No. / Project name",
            value=st.session_state.get("project_name", ""),
            placeholder="e.g. Flat No. 302, Lorven Lavender",
            key="project_name",
        )
    with c2:
        location = st.text_input(
            "Location / Layout",
            value=st.session_state.get("location", ""),
            placeholder="e.g. Pai Layout",
            key="location",
        )
    c3, c4 = st.columns(2)
    with c3:
        margin_pct = st.number_input("Margin (%) – applied to each line", 0.0, 100.0, float(st.session_state.get("margin_pct", 0)), step=0.5, key="margin_pct",
                                      help="Each line price increases by this %. E.g. 20% → ₹50,000 becomes ₹60,000.")
    with c4:
        discount_pct = st.number_input("Discount (%) – on total after margin", 0.0, 100.0, float(st.session_state.get("discount_pct", 0)), step=0.5, key="discount_pct",
                                       help="Reduction on subtotal (after margin). E.g. 10% on ₹1,80,000 = ₹1,62,000.")

# --- Section 1: Detailed Woodwork Estimate (material-based) ---
st.subheader("1. Detailed Woodwork Estimate")
st.caption("Room-wise: select item, dimensions, material grade and materials. Per Sft Price = sum of selected material rates from DB.")

# Add woodwork row: Room, Item (filtered by room), L, W, Grade, Materials
with st.container():
    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
    with col1:
        w_room = st.selectbox("Room", ROOMS, key="w_room")
    with col2:
        items_for_room = get_items_for_room(w_room)
        w_item = st.selectbox("Item", items_for_room, key="w_item")
    with col3:
        w_len = st.number_input("Length (ft)", 0.0, 100.0, 6.0, step=0.1, key="w_len")
    with col4:
        w_wid = st.number_input("Width (ft)", 0.0, 50.0, 10.0, step=0.1, key="w_wid")

    # Grade dropdown → filter materials by grade; default materials for this item
    w_grade = st.selectbox("Material grade", MATERIAL_GRADES, key="w_grade")
    materials_in_grade = get_materials_by_grade(materials_db, w_grade)
    default_ids = default_material_ids_for_item(materials_db, w_item)
    # Only keep defaults that are in current grade
    default_ids = [d for d in default_ids if get_material_by_id(materials_db, d) and get_material_by_id(materials_db, d).get("grade") == w_grade]
    if not default_ids and materials_in_grade:
        default_ids = [materials_in_grade[0]["id"]]

    if not materials_in_grade:
        st.caption("No materials for this grade. Add in **Manage materials DB** below or choose another grade.")
    material_ids_selected = st.multiselect(
        "Materials used (price = sft × sum of rates)",
        options=[m["id"] for m in materials_in_grade],
        default=default_ids,
        format_func=lambda mid: next((f"{m['name']} (₹{m['rate_per_sft']}/sft)" for m in materials_in_grade if m["id"] == mid), mid),
        key="w_materials",
    )

    if st.button("Add woodwork row", type="primary", key="add_wood"):
        if not material_ids_selected:
            st.warning("Select at least one material.")
        else:
            total_sft = round(w_len * w_wid, 2)
            per_sft_rate = rate_per_sft_for_selection(materials_db, material_ids_selected)
            price_unit = round(total_sft * per_sft_rate, 2)
            material_names = ", ".join(
                get_material_by_id(materials_db, mid).get("name", mid) for mid in material_ids_selected
            )
            st.session_state["woodwork_rows"].append({
                "Room": w_room,
                "Item": w_item,
                "Measurements In Feet": f"{w_len}×{w_wid}",
                "Total Sft": total_sft,
                "Materials": material_names,
                "Grade": w_grade,
                "Per Sft Price": round(per_sft_rate, 2),
                "Price Per Unit": price_unit,
            })
            st.rerun()

if st.session_state["woodwork_rows"]:
    df_wood = pd.DataFrame(st.session_state["woodwork_rows"])
    df_display = df_wood.copy()
    df_display["Price (after margin)"] = (df_display["Price Per Unit"] * (1 + margin_pct / 100)).round(2)
    edited_wood = st.data_editor(
        df_display,
        column_config={
            "Room": st.column_config.TextColumn("Room", width="medium"),
            "Item": st.column_config.TextColumn("Item", width="large"),
            "Measurements In Feet": st.column_config.TextColumn("Measurements (ft)", width="medium"),
            "Total Sft": st.column_config.NumberColumn("Total Sft", format="%.2f"),
            "Materials": st.column_config.TextColumn("Materials", width="large"),
            "Grade": st.column_config.TextColumn("Grade", width="small"),
            "Per Sft Price": st.column_config.NumberColumn("Per Sft Price (₹)", format="₹%.2f"),
            "Price Per Unit": st.column_config.NumberColumn("Price Per Unit (₹)", format="₹%.2f"),
            "Price (after margin)": st.column_config.NumberColumn("Price (after margin) (₹)", format="₹%.2f", disabled=True),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
    )
    base_cols = [c for c in edited_wood.columns if c != "Price (after margin)"]
    st.session_state["woodwork_rows"] = edited_wood[base_cols].to_dict("records")
    wood_total_sft = edited_wood["Total Sft"].sum()
    wood_total_price_base = edited_wood["Price Per Unit"].sum()
else:
    wood_total_sft = 0.0
    wood_total_price_base = 0.0
    st.info("Add woodwork items above (enter dimensions and select materials).")

# --- Section 2: False Ceiling Estimate ---
st.subheader("2. False Ceiling Estimate")
st.caption("Measurements and pricing for false ceiling (and painting) by room.")

with st.container():
    cc1, cc2, cc3, cc4, cc5 = st.columns([2, 1, 1, 1, 1.5])
    with cc1:
        c_place = st.selectbox("Place", FALSE_CEILING_PLACES, key="c_place")
    with cc2:
        c_len = st.number_input("Length (ft)", 0.0, 100.0, 11.0, step=0.1, key="c_len")
    with cc3:
        c_wid = st.number_input("Width (ft)", 0.0, 50.0, 17.0, step=0.1, key="c_wid")
    with cc4:
        c_total_override = st.number_input("Total Sft (override)", 0.0, 2000.0, 0.0, step=1.0, key="c_override", help="Leave 0 to use L×W")
    with cc5:
        per_sft_ceil_choice = st.selectbox(
            "Per Sft Price (₹)",
            [f"₹{p}" for p in PER_SFT_CEILING_OPTIONS] + ["Custom"],
            key="per_sft_ceil",
        )
        if per_sft_ceil_choice == "Custom":
            per_sft_ceil_val = st.number_input("Custom rate (₹/sft)", 0, 500, 75, key="custom_ceil")
        else:
            per_sft_ceil_val = int(per_sft_ceil_choice.replace("₹", ""))

    if st.button("Add false ceiling row", type="primary", key="add_ceil"):
        total_sft = c_total_override if c_total_override > 0 else round(c_len * c_wid, 2)
        price_unit = round(total_sft * per_sft_ceil_val, 2)
        st.session_state["ceiling_rows"].append({
            "Place": c_place,
            "Measurements In Feet": f"{c_len}×{c_wid}" if c_total_override <= 0 else f"{total_sft} sft",
            "Total Sft": total_sft,
            "Per Sft Price": per_sft_ceil_val,
            "Price Per Unit": price_unit,
        })
        st.rerun()

if st.session_state["ceiling_rows"]:
    df_ceil = pd.DataFrame(st.session_state["ceiling_rows"])
    df_ceil_display = df_ceil.copy()
    df_ceil_display["Price (after margin)"] = (df_ceil_display["Price Per Unit"] * (1 + margin_pct / 100)).round(2)
    edited_ceil = st.data_editor(
        df_ceil_display,
        column_config={
            "Place": st.column_config.TextColumn("Place", width="medium"),
            "Measurements In Feet": st.column_config.TextColumn("Measurements (ft)", width="medium"),
            "Total Sft": st.column_config.NumberColumn("Total Sft", format="%.2f"),
            "Per Sft Price": st.column_config.NumberColumn("Per Sft Price (₹)", format="₹%d"),
            "Price Per Unit": st.column_config.NumberColumn("Price Per Unit (₹)", format="₹%.2f"),
            "Price (after margin)": st.column_config.NumberColumn("Price (after margin) (₹)", format="₹%.2f", disabled=True),
        },
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
    )
    ceil_base_cols = [c for c in edited_ceil.columns if c != "Price (after margin)"]
    st.session_state["ceiling_rows"] = edited_ceil[ceil_base_cols].to_dict("records")
    ceil_total_sft = edited_ceil["Total Sft"].sum()
    ceil_total_price = edited_ceil["Price Per Unit"].sum()
    st.metric("False ceiling total", f"₹ {ceil_total_price:,.2f}", f"{ceil_total_sft:.2f} sft")
else:
    ceil_total_sft = 0.0
    ceil_total_price = 0.0
    st.info("Add false ceiling / painting rows above.")

# --- Totals (after margin & discount) ---
st.divider()
st.subheader("Totals")
# Compute after-margin and final totals
wood_total_base = wood_total_price_base if st.session_state["woodwork_rows"] else 0.0
ceil_total_base = ceil_total_price if st.session_state["ceiling_rows"] else 0.0
subtotal_base = wood_total_base + ceil_total_base
subtotal_after_margin = subtotal_base * (1 + margin_pct / 100)
discount_amt = subtotal_after_margin * (discount_pct / 100)
final_total = subtotal_after_margin - discount_amt

# Show totals
st.metric("Subtotal (base)", f"₹ {subtotal_base:,.2f}", f"Woodwork ₹{wood_total_base:,.2f} + Ceiling ₹{ceil_total_base:,.2f}")
st.metric("Subtotal (after margin)", f"₹ {subtotal_after_margin:,.2f}", f"Margin {margin_pct}% applied to each line")
st.metric("Discount", f"− ₹ {discount_amt:,.2f}", f"{discount_pct}% on subtotal")
st.metric("Final total", f"₹ {final_total:,.2f}", None)

# --- Manage Materials DB (sidebar or expander) ---
with st.expander("Manage materials DB (add/edit materials and rates)"):
    st.caption("Add or edit materials. Rate = cost per sqft. Item defaults define which materials are pre-selected for each item type.")
    all_mats = materials_db.get("materials", [])
    for i, m in enumerate(all_mats):
        with st.container():
            c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
            with c1:
                new_name = st.text_input("Material name", value=m.get("name", ""), key=f"mat_name_{m.get('id', i)}")
            with c2:
                new_grade = st.selectbox("Grade", MATERIAL_GRADES, index=MATERIAL_GRADES.index(m.get("grade", "Standard")) if m.get("grade") in MATERIAL_GRADES else 1, key=f"mat_grade_{m.get('id', i)}")
            with c3:
                new_rate = st.number_input("Rate (₹/sft)", 0, 5000, int(m.get("rate_per_sft", 0)), key=f"mat_rate_{m.get('id', i)}")
            with c4:
                if st.button("Update", key=f"mat_upd_{m.get('id', i)}"):
                    materials_db["materials"][i]["name"] = new_name
                    materials_db["materials"][i]["grade"] = new_grade
                    materials_db["materials"][i]["rate_per_sft"] = new_rate
                    save_materials_db(materials_db)
                    st.rerun()
    st.divider()
    st.subheader("Add new material")
    add_id = st.text_input("ID (e.g. ply_custom)", value="", key="add_mat_id")
    add_name = st.text_input("Name", value="", key="add_mat_name")
    add_grade = st.selectbox("Grade", MATERIAL_GRADES, key="add_mat_grade")
    add_rate = st.number_input("Rate (₹/sft)", 0, 5000, 500, key="add_mat_rate")
    if st.button("Add material") and add_id and add_name:
        if any(x["id"] == add_id for x in materials_db["materials"]):
            st.warning("ID already exists.")
        else:
            materials_db["materials"].append({"id": add_id, "name": add_name, "grade": add_grade, "rate_per_sft": add_rate})
            save_materials_db(materials_db)
            st.rerun()

# --- Export Excel ---
st.subheader("Export")
quote_date = st.date_input("Quote date", value=datetime.now().date(), key="qdate")
validity = st.text_input("Valid until", value="30 days", key="validity")

def build_excel():
    buf = BytesIO()
    # No Place column: Room, Item, Measurements, Total Sft, Materials, Grade, Per Sft Price, Price Per Unit (after margin)
    wood_cols = ["Room", "Item", "Measurements In Feet", "Total Sft", "Materials", "Grade", "Per Sft Price", "Price Per Unit"]
    with pd.ExcelWriter(buf, engine="openpyxl") as xl:
        row = 0
        summary = pd.DataFrame([
            ["Project", project_name or "—"],
            ["Location", location or "—"],
            ["Quote date", str(quote_date)],
            ["Valid until", validity],
            ["Margin (%)", margin_pct],
            ["Discount (%)", discount_pct],
        ], columns=["Field", "Value"])
        summary.to_excel(xl, sheet_name="Quotation", index=False, startrow=row)
        row += summary.shape[0] + 2

        # 1. Woodwork – export with Price Per Unit = after margin
        pd.DataFrame([["1. Detailed Woodwork Estimate"] + [""] * 7], columns=wood_cols).to_excel(
            xl, sheet_name="Quotation", index=False, startrow=row, header=False
        )
        row += 1
        if st.session_state["woodwork_rows"]:
            wood_df = pd.DataFrame(st.session_state["woodwork_rows"])
            wood_export = wood_df[["Room", "Item", "Measurements In Feet", "Total Sft", "Materials", "Grade", "Per Sft Price"]].copy()
            wood_export["Price Per Unit"] = (wood_df["Price Per Unit"] * (1 + margin_pct / 100)).round(2)
            wood_export.to_excel(xl, sheet_name="Quotation", index=False, startrow=row)
            row += len(wood_export) + 1
            wood_total_after = wood_export["Price Per Unit"].sum()
        else:
            pd.DataFrame(columns=wood_cols).to_excel(xl, sheet_name="Quotation", index=False, startrow=row)
            row += 2
            wood_total_after = 0.0
        pd.DataFrame([["Total (Woodwork)", "", "", round(wood_total_sft, 2), "", "", "", round(wood_total_after, 2)]], columns=wood_cols).to_excel(
            xl, sheet_name="Quotation", index=False, startrow=row, header=False
        )
        row += 3

        # 2. False Ceiling – Room (area name), no Place column
        ceil_cols = ["Room", "Measurements In Feet", "Total Sft", "Per Sft Price", "Price Per Unit"]
        pd.DataFrame([["2. False Ceiling Estimate"] + [""] * 4], columns=ceil_cols).to_excel(
            xl, sheet_name="Quotation", index=False, startrow=row, header=False
        )
        row += 1
        if st.session_state["ceiling_rows"]:
            ceil_df = pd.DataFrame(st.session_state["ceiling_rows"])
            ceil_export = ceil_df[["Place", "Measurements In Feet", "Total Sft", "Per Sft Price"]].copy()
            ceil_export = ceil_export.rename(columns={"Place": "Room"})
            ceil_export["Price Per Unit"] = (ceil_df["Price Per Unit"] * (1 + margin_pct / 100)).round(2)
            ceil_export.to_excel(xl, sheet_name="Quotation", index=False, startrow=row)
            row += len(ceil_export) + 1
            ceil_total_after = ceil_export["Price Per Unit"].sum()
        else:
            pd.DataFrame(columns=ceil_cols).to_excel(xl, sheet_name="Quotation", index=False, startrow=row)
            row += 2
            ceil_total_after = 0.0
        pd.DataFrame([["Total (False Ceiling)", "", round(ceil_total_sft, 2), "", round(ceil_total_after, 2)]], columns=ceil_cols).to_excel(
            xl, sheet_name="Quotation", index=False, startrow=row, header=False
        )
        row += 2
        pd.DataFrame([["Subtotal (after margin)", "", "", "", round(subtotal_after_margin, 2)]], columns=ceil_cols).to_excel(
            xl, sheet_name="Quotation", index=False, startrow=row, header=False
        )
        row += 1
        pd.DataFrame([["Discount (%)", "", "", "", discount_pct]], columns=ceil_cols).to_excel(
            xl, sheet_name="Quotation", index=False, startrow=row, header=False
        )
        row += 1
        pd.DataFrame([["Discount amount", "", "", "", round(discount_amt, 2)]], columns=ceil_cols).to_excel(
            xl, sheet_name="Quotation", index=False, startrow=row, header=False
        )
        row += 1
        pd.DataFrame([["Final total", "", "", "", round(final_total, 2)]], columns=ceil_cols).to_excel(
            xl, sheet_name="Quotation", index=False, startrow=row, header=False
        )

    buf.seek(0)
    out = BytesIO()
    load_workbook(buf).save(out)
    out.seek(0)
    return out

st.download_button(
    "Download quotation (Excel)",
    data=build_excel(),
    file_name=f"interior_quote_{(project_name or 'project').replace(' ', '_')[:30]}_{quote_date}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
