import json
import os
from typing import Dict, Any

INVENTORY_PATH = os.path.join(os.path.dirname(__file__), "inventory.json")


def load_inventory() -> Dict[str, Dict[str, Any]]:
    """Load inventory from inventory.json. If not present, create default empty file."""
    if not os.path.exists(INVENTORY_PATH):
        data = {}
        save_inventory(data)
        return data
    with open(INVENTORY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_inventory(data: Dict[str, Dict[str, Any]]) -> None:
    with open(INVENTORY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_material(category: str, name: str, price: float) -> None:
    """Add a material under a category. Creates category if missing."""
    inv = load_inventory()
    if category not in inv:
        inv[category] = {}
    inv[category][name] = {"price": float(price)}
    save_inventory(inv)


def get_categories() -> list:
    inv = load_inventory()
    return list(inv.keys())
