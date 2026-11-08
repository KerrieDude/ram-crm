"""IKEA assembly time reference list (minutes -> hours, with crew size needed)
for use in Hunni-Do / assembly quotes.
"""

# (brand, product, minutes, crew)
_RAW = [
    ("MALM", "Bed frame", 45, 1),
    ("BRIMNES", "Bed frame", 45, 1),
    ("TRYSIL", "Bed frame", 45, 1),
    ("MALM", "Bed frame with 4 storage boxes", 95, 1),
    ("MALM", "2 drawer chest", 30, 1),
    ("BRIMNES", "2 drawer chest", 30, 1),
    ("MALM", "3 drawer chest", 40, 1),
    ("BRIMNES", "3 drawer chest", 40, 1),
    ("TRYSIL", "3 drawer chest", 40, 1),
    ("MALM", "4 drawer chest", 50, 1),
    ("BRIMNES", "4 drawer chest", 50, 1),
    ("MALM", "6 drawer chest", 70, 1),
    ("MALM", "6 drawer dresser", 90, 1),
    ("BRIMNES", "Bed frame with storage", 105, 1),
    ("BRIMNES", "Headboard", 60, 1),
    ("BRIMNES", "Wardrobe with 2 doors", 60, 1),
    ("BRIMNES", "Wardrobe with 3 doors", 70, 1),
    ("BRIMNES", "Nightstand", 20, 1),
    ("TRYSIL", "Nightstand", 20, 1),
    ("BRIMNES", "Daybed with 2 drawers", 135, 1),
    ("HEMNES", "Bed frame", 70, 1),
    ("BRUSALI", "Bed frame", 70, 1),
    ("BRUSALI", "Bed with 4 storage boxes", 120, 1),
    ("HEMNES", "2 drawer chest", 40, 1),
    ("HEMNES", "3 drawer chest", 70, 1),
    ("BRUSALI", "3 drawer chest", 70, 1),
    ("HEMNES", "6 drawer chest", 90, 1),
    ("HEMNES", "8 drawer dresser", 105, 1),
    ("HEMNES", "Nightstand", 20, 1),
    ("BRUSALI", "Nightstand", 20, 1),
    ("HEMNES", "Daybed with 3 drawers", 150, 1),
    ("KALLAX", "Shelving unit 5x5", 60, 1),
    ("KALLAX", "Shelving unit 4x4", 45, 1),
    ("KALLAX", "Shelving unit 2x4", 40, 1),
    ("KALLAX", "Shelving unit 1x4", 35, 1),
    ("KALLAX", "Shelving unit 2x2", 20, 1),
    ("KALLAX", "Insert with 2 drawers", 20, 1),
    ("KALLAX", "Insert with door", 15, 1),
    ("TRYSIL", "Wardrobe", 150, 2),
    ("FINGAL", "Swivel chair", 15, 1),
    ("BJURSTA", "Extendable table", 45, 1),
    ("MICKE", "Desk with 1 drawer", 30, 1),
    ("MICKE", "Desk with drawers, integrated storage", 40, 1),
    ("MICKE", "Add-on unit", 40, 1),
    ("LINNMON/ADILS", "Table (top + four legs)", 15, 1),
    ("BEKANT", "Desk with underframe", 40, 1),
    ("LACK", "Side table", 10, 1),
    ("LACK", "Coffee table", 15, 1),
    ("LACK", "TV unit", 20, 1),
    ("GALANT", "2 drawer unit", 75, 1),
    ("GALANT", "3 drawer unit", 95, 1),
    ("GALANT", "4 drawer unit", 110, 1),
    ("GALANT", "Cabinet with sliding doors", 150, 1),
    ("BILLY", "Bookcase, one frame", 40, 1),
    ("FRIHETEN", "Sofa bed with chaise", 50, 1),
    ("SODERHAMN", "Sofa, one-seat section with cover", 30, 1),
    ("PAX", "One frame, hinged doors, up to 3 addons", 90, 2),
    ("PAX", "Two frames, sliding doors, up to 5 addons", 240, 2),
    ("BESTA", "Single frame, shelves, floor standing", 30, 1),
    ("BESTA", "Single frame, door/drawer, floor standing", 45, 1),
    ("BESTA", "Single frame, wall mounting", 30, 2),
    ("MORVIK", "Wardrobe", 120, 1),
    ("MALM", "Lift bed", 130, 2),
]

IKEA_ITEMS = [
    {"brand": b, "product": p, "minutes": m, "hours": round(m / 60, 2), "crew": c}
    for b, p, m, c in _RAW
]

BRANDS = sorted({i["brand"] for i in IKEA_ITEMS})


def label(item):
    return f"{item['brand']} — {item['product']} ({item['minutes']} min, crew {item['crew']})"
