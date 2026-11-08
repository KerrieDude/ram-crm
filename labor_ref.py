"""Reference tables from RAM_CRM_2.0's settings sheet: crew/hours by home size,
portable-storage pricing, and truck size/mileage comparisons. Used on the
Labor & Expenses tab for quick lookups and fuel-cost estimates.
"""

# Home size -> est. hours by crew size (from settings sheet)
CREW_HOURS = [
    # (home_size, sqft, crew, hours)
    ("Studio", 600, 2, 2.5), ("1 Bed", 600, 2, 3), ("2 Bed", 800, 2, 4), ("3 Bed", 1300, 2, 5),
    ("Studio", 600, 3, 2), ("1 Bed", 600, 3, 2.5), ("2 Bed", 800, 3, 3), ("3 Bed", 1300, 3, 4),
    ("4 Bed", 1800, 3, 6), ("5 Bed", 2000, 3, 8),
    ("Studio", 600, 4, 1.5), ("1 Bed", 600, 4, 1.5), ("2 Bed", 800, 4, 2.5), ("3 Bed", 1300, 4, 3.5),
    ("4 Bed", 1800, 4, 6), ("5 Bed", 2000, 4, 7),
    ("Studio", 600, 5, 1), ("1 Bed", 600, 5, 1), ("2 Bed", 800, 5, 2), ("3 Bed", 1300, 5, 3),
    ("4 Bed", 1800, 5, 5.5), ("5 Bed", 2000, 5, 6.5),
]

HOME_SIZES = ["Studio", "1 Bed", "2 Bed", "3 Bed", "4 Bed", "5 Bed"]
CREW_SIZES = [2, 3, 4, 5]


def lookup_hours(home_size, crew):
    for hs, sqft, c, hrs in CREW_HOURS:
        if hs == home_size and c == crew:
            return hrs
    return None


# Portable storage pricing
RENT_A_CRATE = [
    # (home_size, boxes, dollies)
    ("Studio", None, None), ("1 Bed", 20, 5), ("2 Bed", 40, 10),
    ("3 Bed", 60, 15), ("4-5 Bed", 80, 20), ("Larger pack", None, None),
]
RENT_A_CRATE_UNIT = "24.25 x 15.15 x 12.75 in (2.73 cu. ft.) per crate"

REDI_BOX = [
    # (home_size, price_text, boxes)
    ("Studio", "$99, 2 wks, $15/extra wk", 20),
    ("1 Bed", "$149, 2 wks, $20/extra wk", 30),
    ("2 Bed", "$199, 2 wks, $25/extra wk", 45),
    ("3 Bed", "$199, 2 wks, $25/extra wk", 45),
    ("4-5 Bed", "$249, 2 wks, $30/extra wk", 60),
    ("Larger pack", "$299, 3 wks, $40/extra wk", 75),
]
REDI_BOX_UNIT = "27 x 17 x 12.4 in (3.32 cu. ft.) per box; free delivery/pickup/labels"

# Truck size comparison (for fuel-cost estimates)
TRUCKS = [
    {"name": "Pickup", "home_size": "Small Loads / Studio Apt", "tank_gal": 34, "mpg": 19, "range_mi": 646},
    {"name": "Cargo Van", "home_size": "Studio Apt / Deliveries", "tank_gal": 25, "mpg": 18, "range_mi": 450},
    {"name": "10' Truck", "home_size": "Studio / 1 Bedroom Apt", "tank_gal": 31, "mpg": 12, "range_mi": 372},
    {"name": "15' Truck", "home_size": "1 Bedroom Home / 2 Bedroom Apt", "tank_gal": 40, "mpg": 10, "range_mi": 400},
    {"name": "20' Truck", "home_size": "2 Bedroom Home / 3 Bedroom Apt", "tank_gal": 40, "mpg": 10, "range_mi": 400},
    {"name": "26' Truck", "home_size": "3-4 Bedroom Home", "tank_gal": 60, "mpg": 10, "range_mi": 600},
]
