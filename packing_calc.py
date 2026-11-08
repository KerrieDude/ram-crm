"""Loads the real packing-materials calculator table from RAM_CRM_2.0 (move_spec sheet)
and looks up recommended box/supply counts by home size + persons + packing tier.
"""
import json
import os

_PATH = os.path.join(os.path.dirname(__file__), "data", "move_spec.json")

COLS = [
    "tier", "persons", "bedrooms", "beds", "estimate",
    "medium_boxes", "large_boxes", "x_boxes", "picture_boxes",
    "kitchen_book_boxes", "wardrobe_boxes",
]

with open(_PATH) as f:
    _RAW = json.load(f)

ROWS = [dict(zip(COLS, r)) for r in _RAW]

BEDROOM_OPTIONS = sorted({r["bedrooms"] for r in ROWS}, key=lambda b: (b != "Studio", b))
PERSON_OPTIONS = sorted({r["persons"] for r in ROWS})
TIERS = ["Minimalist (Basic)", "Minimalist (Average)", "Minimalist (Professional)",
         "Modest (Basic)", "Modest (Average)", "Modest (Professional)",
         "Large (Basic)", "Large (Average)", "Large (Professional)"]


def lookup(bedrooms, persons, tier):
    for r in ROWS:
        if r["bedrooms"] == bedrooms and r["persons"] == persons and r["tier"] == tier:
            return r
    return None
