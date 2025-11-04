import os
from typing import Dict, Any

import streamlit as st

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


def safe_rerun():
    """Rerun the Streamlit script. Use experimental_rerun when available, otherwise
    mutate the query params (a supported way to force a rerun).
    """
    try:
        # preferred method (may not exist in some Streamlit versions)
        if hasattr(st, "experimental_rerun"):
            st.experimental_rerun()
            return
    except Exception:
        # fallthrough to query param approach
        pass

    # fallback: tweak query params to trigger a rerun
    try:
        import time

        params = st.experimental_get_query_params() or {}
        params["_rerun_ts"] = str(time.time())
        st.experimental_set_query_params(**params)
    except Exception:
        # last resort: set a session flag and stop; user action will refresh page
        st.session_state["_need_rerun"] = not st.session_state.get("_need_rerun", False)
        st.stop()


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

                cols = st.columns([3, 1, 2])
                for i in range(count):
                    idx = i + 1
                    sel_key = f"select_{sanitize_key(cat)}_{idx}"
                    qty_key = f"qty_{sanitize_key(cat)}_{idx}"

                    with st.container():
                        c1, c2, c3 = st.columns([3, 1, 2])
                        with c1:
                            selection = st.selectbox(f"Type (row {idx})", options, key=sel_key)
                        with c2:
                            qty = st.number_input(f"Qty (row {idx})", min_value=0.0, value=float(st.session_state.get(qty_key, 1.0)), key=qty_key)
                        with c3:
                            if st.button("Remove", key=f"remove_{sanitize_key(cat)}_{idx}"):
                                # decrease rows count and shift values
                                new_count = max(0, st.session_state.get(rows_key, 1) - 1)
                                st.session_state[rows_key] = new_count
                                safe_rerun()

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
                                    safe_rerun()

                st.markdown("---")
                if st.button(f"Add row to {cat}", key=f"addrow_{sanitize_key(cat)}"):
                    st.session_state[rows_key] = st.session_state.get(rows_key, 1) + 1
                    safe_rerun()

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
    else:
        st.info("No materials selected yet. Use the panels above to select or add materials.")


if __name__ == "__main__":
    main()
