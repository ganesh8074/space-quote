import os
from typing import Dict, Any

import streamlit as st
import io

import pandas as pd

from utils import load_inventory, add_material


CATEGORIES_ORDER = [
    "wood types",
    "laminate types",
    "knob types",
    "handle types",
    "acrylic material types",
    "mirror types",
    "edge banding types",
    "strip light types",
    "false ceiling types",
    "granite types",
    "push magnet types",
    "channel types",
    "profile types",
    "tv panel types",
    "profile door types",
]


def pretty_option(name: str, price: float) -> str:
    return f"{name} | Rs {price:.2f}"


def parse_option(option: str) -> str:
    # option format: "Name | Rs price"
    return option.split(" | ")[0]


def sanitize_key(s: str) -> str:
    return s.replace(" ", "_").replace("/", "_")


# Note: explicit rerun logic was removed because it caused navigation/hang issues
# on some Streamlit versions. Widget interactions (button presses) cause Streamlit
# to rerun the script automatically, so explicit reruns are unnecessary here.


def main():
    st.set_page_config(page_title="Interior Quotation Generator", layout="wide")
    st.title("Interior Quotation Generator")

    st.markdown("Select multiple materials per category, enter quantities, or add new materials to the inventory.")

    inventory = load_inventory()

    # initialize per-category row counts in session state
    for cat in CATEGORIES_ORDER:
        rows_key = f"rows_count_{sanitize_key(cat)}"
        if rows_key not in st.session_state:
            st.session_state[rows_key] = 1

    col1, col2 = st.columns([2, 1])

    with col2:
        st.header("Project")
        project_name = st.text_input("Project name", value="My Project")
        client = st.text_input("Client name")
        note = st.text_area("Notes / Description")

    items_selected = []

    with col1:
        st.header("Materials & Quantities")
        for cat in CATEGORIES_ORDER:
            with st.expander(cat.title(), expanded=False):
                cat_items: Dict[str, Any] = inventory.get(cat, {})
                options = [pretty_option(n, i["price"]) for n, i in cat_items.items()]
                options = ["-- select --"] + options + ["Other"]

                rows_key = f"rows_count_{sanitize_key(cat)}"
                count = int(st.session_state.get(rows_key, 1))

                # top bar: show an Add button so it's visible without scrolling
                top_c1, top_c2 = st.columns([3, 1])
                with top_c2:
                    if st.button("+ Add another item", key=f"addrow_top_{sanitize_key(cat)}"):
                        st.session_state[rows_key] = st.session_state.get(rows_key, 1) + 1

                cols = st.columns([3, 1, 2])
                for i in range(count):
                    idx = i + 1
                    sel_key = f"select_{sanitize_key(cat)}_{idx}"
                    qty_key = f"qty_{sanitize_key(cat)}_{idx}"

                    with st.container():
                        c1, c2, c3 = st.columns([3, 1, 2])
                        # ensure any stored selection for this row is still valid for the current options
                        if sel_key in st.session_state and st.session_state.get(sel_key) not in options:
                            st.session_state[sel_key] = "-- select --"

                        with c1:
                            selection = st.selectbox(f"Type (row {idx})", options, key=sel_key)
                        with c2:
                            qty = st.number_input(f"Qty (row {idx})", min_value=0.0, value=float(st.session_state.get(qty_key, 1.0)), key=qty_key)
                        with c3:
                            # show Remove only when more than one row exists
                            if count > 1:
                                if st.button("Remove", key=f"remove_{sanitize_key(cat)}_{idx}"):
                                    # shift subsequent rows up to fill this gap
                                    for j in range(idx, count):
                                        src = j + 1
                                        dst = j
                                        sel_src = f"select_{sanitize_key(cat)}_{src}"
                                        sel_dst = f"select_{sanitize_key(cat)}_{dst}"
                                        qty_src = f"qty_{sanitize_key(cat)}_{src}"
                                        qty_dst = f"qty_{sanitize_key(cat)}_{dst}"
                                        # move selection and qty if present
                                        if sel_src in st.session_state:
                                            st.session_state[sel_dst] = st.session_state.get(sel_src)
                                        else:
                                            st.session_state.pop(sel_dst, None)
                                        if qty_src in st.session_state:
                                            st.session_state[qty_dst] = st.session_state.get(qty_src)
                                        else:
                                            st.session_state.pop(qty_dst, None)

                                        # move any other fields (othername/otherprice)
                                        other_src = f"othername_{sanitize_key(cat)}_{src}"
                                        other_dst = f"othername_{sanitize_key(cat)}_{dst}"
                                        otherp_src = f"otherprice_{sanitize_key(cat)}_{src}"
                                        otherp_dst = f"otherprice_{sanitize_key(cat)}_{dst}"
                                        if other_src in st.session_state:
                                            st.session_state[other_dst] = st.session_state.get(other_src)
                                        else:
                                            st.session_state.pop(other_dst, None)
                                        if otherp_src in st.session_state:
                                            st.session_state[otherp_dst] = st.session_state.get(otherp_src)
                                        else:
                                            st.session_state.pop(otherp_dst, None)

                                    # remove last row keys
                                    last = count
                                    for k in [f"select_{sanitize_key(cat)}_{last}", f"qty_{sanitize_key(cat)}_{last}", f"othername_{sanitize_key(cat)}_{last}", f"otherprice_{sanitize_key(cat)}_{last}"]:
                                        st.session_state.pop(k, None)

                                    st.session_state[rows_key] = count - 1

                        # If Other is selected, show inputs to add new material and a button to save it
                        if selection == "Other":
                            other_name_key = f"othername_{sanitize_key(cat)}_{idx}"
                            other_price_key = f"otherprice_{sanitize_key(cat)}_{idx}"
                            other_name = st.text_input("New material name", key=other_name_key)
                            other_price = st.number_input("Price (per unit)", min_value=0.0, value=0.0, key=other_price_key)
                            if st.button(f"Save new material (row {idx})", key=f"saveother_{sanitize_key(cat)}_{idx}"):
                                if other_name.strip() == "":
                                    st.warning("Enter a valid material name before saving.")
                                else:
                                    add_material(cat, other_name.strip(), float(other_price))
                                    st.success(f"Added {other_name} to {cat} with price Rs {other_price}")
                                    # set selection to the newly added pretty option and store qty
                                    new_opt = pretty_option(other_name.strip(), float(other_price))
                                    st.session_state[sel_key] = new_opt
                                    st.session_state[qty_key] = float(qty)

                st.markdown("---")
                if st.button(f"Add row to {cat}", key=f"addrow_{sanitize_key(cat)}"):
                    st.session_state[rows_key] = st.session_state.get(rows_key, 1) + 1

    # after UI, build items_selected from per-row selections
    inventory = load_inventory()
    for cat in CATEGORIES_ORDER:
        cat_items = inventory.get(cat, {})
        rows_key = f"rows_count_{sanitize_key(cat)}"
        count = int(st.session_state.get(rows_key, 0))
        for i in range(count):
            idx = i + 1
            sel_key = f"select_{sanitize_key(cat)}_{idx}"
            qty_key = f"qty_{sanitize_key(cat)}_{idx}"
            selection = st.session_state.get(sel_key, "-- select --")
            if not selection or selection == "-- select --":
                continue
            if selection == "Other":
                # should not normally happen because 'Save new material' replaces selection, but skip if still Other
                continue
            name = parse_option(selection)
            price = cat_items.get(name, {}).get("price", 0.0)
            qty = float(st.session_state.get(qty_key, 1.0))
            items_selected.append({"category": cat, "name": name, "price": float(price), "qty": qty})

    # compute totals
    total = sum(it["price"] * it["qty"] for it in items_selected)

    st.sidebar.header("Estimate Summary")
    st.sidebar.write(f"Project: **{project_name}**")
    st.sidebar.write(f"Client: {client}")
    st.sidebar.write(f"Items: {len(items_selected)}")
    st.sidebar.write(f"Subtotal: Rs {total:.2f}")

    st.header("Estimate Breakdown")
    if items_selected:
        rows = []
        for it in items_selected:
            rows.append({
                "Category": it["category"].title(),
                "Name": it["name"],
                "Unit Price (Rs)": f"{it['price']:.2f}",
                "Quantity": it["qty"],
                "Line Total (Rs)": f"{it['price'] * it['qty']:.2f}",
            })
        st.table(rows)
        st.subheader(f"Total Estimate: Rs {total:.2f}")

        # export
        import json

        export = {
            "project": project_name,
            "client": client,
            "notes": note,
            "items": items_selected,
            "total": total,
        }
        st.download_button("Download estimate (JSON)", data=json.dumps(export, indent=2, ensure_ascii=False), file_name=f"estimate_{project_name.replace(' ','_')}.json", mime="application/json")

        # Excel export (XLSX)
        def generate_excel(project: str, client_name: str, notes: str, items: list, total_amount: float) -> bytes:
            # Build DataFrame
            if items:
                df = pd.DataFrame(items)
                # ensure columns exist
                df = df.rename(columns={
                    "category": "Category",
                    "name": "Material",
                    "qty": "Qty",
                    "price": "Unit Price (Rs)",
                })
                if "Qty" not in df.columns:
                    df["Qty"] = 0
                if "Unit Price (Rs)" not in df.columns:
                    df["Unit Price (Rs)"] = 0.0
                df["Line Total (Rs)"] = df["Qty"] * df["Unit Price (Rs)"]
                # reorder
                df = df[["Category", "Material", "Qty", "Unit Price (Rs)", "Line Total (Rs)"]]
            else:
                df = pd.DataFrame(columns=["Category", "Material", "Qty", "Unit Price (Rs)", "Line Total (Rs)"])

            # append a final total row
            total_row = {"Category": "", "Material": "", "Qty": "", "Unit Price (Rs)": "Total:", "Line Total (Rs)": f"{total_amount:.2f}"}
            df_total = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
                df_total.to_excel(writer, sheet_name="Estimate", index=False)
                # autosize columns (simple approach)
                ws = writer.book.worksheets[0]
                for col in ws.columns:
                    max_length = 0
                    col_letter = col[0].column_letter
                    for cell in col:
                        try:
                            v = str(cell.value)
                        except Exception:
                            v = ""
                        if v:
                            max_length = max(max_length, len(v))
                    adjusted_width = (max_length + 2)
                    ws.column_dimensions[col_letter].width = adjusted_width

            excel_bytes = buffer.getvalue()
            buffer.close()
            return excel_bytes

        try:
            xlsx_bytes = generate_excel(project_name, client, note, items_selected, total)
            st.download_button("Download estimate (XLSX)", data=xlsx_bytes, file_name=f"estimate_{project_name.replace(' ','_')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        except Exception as e:
            st.error(f"Excel generation failed: {e}")
    else:
        st.info("No materials selected yet. Use the panels above to select or add materials.")


if __name__ == "__main__":
    main()
