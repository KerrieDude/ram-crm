"""Furniture inventory catalog (item -> cubic feet), transcribed from the RAM_CRM_2.0
MoveEst sheet's own inventory list, grouped by room. Used to compute total cubic
footage / weight for a move instead of guessing hours by hand.
"""

WEIGHT_FACTOR_LBS_PER_CUFT = 7  # from the spreadsheet's Settings sheet

FURNITURE = {
    "Appliances": {
        "Dryer": 25, "Refrigerator - X-Small": 15, "Refrigerator - Regular": 45,
        "Refrigerator - Large": 65, "Washer/Dryer Stackable": 35, "Washing Machine": 25,
        "Dishwasher": 20, "Freezer 10cu or less": 30, "Freezer 11-15cu": 45,
        "Freezer 16cu+": 60, "Ironing Board": 2, "Microwave Oven": 5,
        "Microwave Stand": 10, "Range": 30, "Toaster Oven": 1, "Vacuum Cleaner": 3,
    },
    "Living Room": {
        "Sofa 3 Cushion": 50, "Sofa Hide-A-Bed 4 Cushion": 60, "Sofa Loveseat": 35,
        "Sofa Sectional (per section)": 30, "Table End": 5, "Table Coffee": 10,
        "Table Occasional": 15, "Table Small": 5, "Entertainment Center": 35,
        "Bench": 10, "Bookcase (Large)": 20, "Bookcase (Small)": 10,
        "Chair Occasional": 10, "Chair Overstuffed": 25, "Chair Rocker": 12,
        "Chair Straight": 5, "Chest": 20, "Futon": 25, "Ottoman": 10,
        "Piano Baby Grand/Upright": 75, "Piano Parlor Grand": 85, "Piano Spinet/Console": 65,
        "Cabinet Curio": 10, "Clock Grandfather": 25, "Fireplace Equipment": 5,
        "Footstool": 2, "Lamp Floor/Pole": 3, "Magazine Rack": 2, "Plant Stand": 3,
        "Rug Large": 10, "Rug Small": 3,
    },
    "Dining Room": {
        "Buffet (Base)": 30, "Buffet (Top)": 20, "Cabinet China": 40,
        "Cabinet Corner": 20, "Cabinet Curio/Utility": 10, "Table Dining": 30,
        "Chair Dining": 5, "Tea Cart": 10,
    },
    "Kitchen": {
        "Table Breakfast": 10, "Chair Breakfast": 5, "Bakers Rack": 15,
        "Cabinet": 20, "Cart": 10, "Chair High": 5, "Stool Bar": 3,
    },
    "Bedroom(s)": {
        "Bed King": 70, "Bed Queen": 65, "Bed Double/Full": 60, "Bed Single": 55,
        "Bed Bunk": 70, "Bed Youth/Trundle": 30, "Bench Vanity": 5, "Sofa 2 Cushion": 35,
        "Chair Boudoir": 20, "Chest Small": 10, "Chest": 20, "Chest of Drawers": 30,
        "Chest Armoire": 40, "Dresser": 30, "Dresser Double": 40, "Dresser Triple": 50,
        "Dresser Vanity": 20, "Small Table/Shelf": 5, "Bed Rollaway/Cot": 20,
        "Bed Waterbed Base": 35, "Chair Arm/Straight": 15, "Chair Lounge": 10,
        "Chest/Trunk": 15, "Clothes Hamper": 5, "Day Bed": 50, "Table Night": 5,
        "Armoire Small": 20, "Armoire Large": 40,
    },
    "Electronics": {
        "TV 9\"-19\"": 15, "TV 20\"-27\"": 20, "TV 28\"-39\"": 25, "TV 40\"+": 35,
        "Plasma TV": 10, "LCD TV": 10, "DVD/VCR/CD": 3, "Speaker (Floor)": 5,
        "TV Stand": 5, "Computer": 5, "Entertainment Center (Small)": 30,
        "Entertainment Center (Large)": 60,
    },
    "Office / Library": {
        "2-Drawer Lateral File": 15, "2-Drawer Vertical File": 10,
        "4-Drawer Lateral File": 25, "4-Drawer Vertical File": 20,
        "Bookcase - Large": 20, "Bookcase - Small": 10, "Chair Office": 5,
        "Credenza": 45, "Desk Computer": 20, "Desk Office": 30, "Desk Small": 10,
        "Hutch": 25, "PC/Printer/Fax": 5,
    },
    "Nursery / Kids Room": {
        "Bed Crib": 15, "Bed Child's": 30, "Chair Child's": 3, "Chair Rocker": 12,
        "Table Changing": 25, "Table Child's": 5, "Basket/Hamper": 5, "Bassinette": 5,
        "Playpen": 10, "Stroller": 4, "Toy": 2, "Toy Chest": 5,
    },
    "Outdoor / Porch": {
        "Chair Metal": 5, "Chair Plastic": 2, "Chairs Patio": 5, "Chaise Lounge": 25,
        "Firepit": 4, "Glider or Settee": 20, "Grill Large": 15, "Grill Small": 5,
        "Table Patio": 15, "Table Small (Patio)": 5, "Umbrella Patio": 5,
        "Wicker Chair/Piece": 5, "Bird Bath": 10, "Hammock": 15,
        "Outdoor Child Gym": 20, "Outdoor Swings": 30,
    },
    "Garage / Shop": {
        "Air Conditioner (Large)": 20, "Fan": 5, "Heater Gas/Electric": 5,
        "Humidifier/Dehumidifier": 10, "Ladder 6ft Step": 3, "Ladder 8ft Step": 5,
        "Ladder Extension": 8, "Power Tool": 3, "Power Tool Stand": 15,
        "Shelving Unit": 10, "ShopVac": 5, "Storage Cabinet": 20, "Tire": 5,
        "Tool Chest (Large)": 20, "Tool Box": 5, "Work Bench (Large)": 25,
        "Work Bench (Small)": 10,
    },
    "Lawn Equipment": {
        "Garden Hose/Tools": 3, "Lawn Mower (Riding)": 35, "Lawn Mower (Power)": 15,
        "Leaf Sweeper": 5, "Spreader (Lawn)": 2, "Trash Can (Outside)": 5,
        "Weed Eater": 2, "Wheelbarrow": 8,
    },
    "Exercise / Sporting Goods": {
        "Barbells (set)": 4, "Bicycle": 5, "Bicycle (Child's)": 2,
        "Exercise Bike": 20, "Golf Clubs": 5, "Skis/Poles": 8,
        "Treadmill/Exercise Machine": 20, "Trampoline": 15,
    },
    "Game Room": {
        "Pool Table (Slate)": 100, "Ping Pong Table": 40,
    },
    "Cartons": {
        "Kitchen Box": 10, "Small Carton (1.5cu)": 1.5, "Book Carton (6cu)": 6,
        "Medium Carton (3.0cu)": 3, "HD Large Carton (3.75cu)": 3.75,
        "Large Carton (4.5cu)": 4.5, "Tote": 2.5, "Mirror Carton": 3,
        "X-Large Carton (6.0cu)": 6, "Wardrobe Carton": 10,
    },
    "Attic / Misc": {
        "Suitcase": 5, "X-mas Tree": 15, "Rubbermaid Bins": 5, "PBO Boxes": 3,
        "Misc Attic/Garage/Crawl": 5, "Mirror": 1, "Card Table": 2, "Chair Folding": 1,
        "Sewing Machine (Portable)": 5, "Sewing Machine w/Cabinet": 10, "Trunk/Footlocker": 5,
    },
}
