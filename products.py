"""
Products (HS codes) for the procurement view, linked to the NAICS industries in the dashboard.

For each product:
  freight   "container" = priced per 40ft container (Freightos estimate or your quote)
            "tanker"    = priced per barrel (your freight quote, tanker rates are paid data)
            "bulk"      = priced per metric ton (your freight quote)
  unit      what the quantity is measured in
  price     example material price per unit, ONLY a starting value: the user enters their own quote
            (crude oil uses the live Brent or WTI price instead)
  payload   metric tons per 40ft container (planning assumption, editable in the app)
  origins   supplier countries offered for this product (keys of lanes.ORIGINS)
"""

PRODUCTS = [
    {"hs": "2709", "name": "Crude Oil", "naics": "3241", "emoji": "🛢️", "benchmark": "brent",
     "desc": "Petroleum oils & oils obtained from bituminous minerals, crude",
     "freight": "tanker", "unit": "bbl", "price": None, "origins": ["Saudi Arabia", "Brazil", "Nigeria"]},
    {"hs": "2710", "name": "Refined Petroleum Products", "naics": "3241", "emoji": "⛽", "benchmark": "wti",
     "desc": "Gasoline, diesel, jet fuel and other refined oils",
     "freight": "tanker", "unit": "bbl", "price": 110.0, "origins": ["Netherlands", "South Korea", "India"]},
    {"hs": "2711", "name": "Natural Gas & LNG", "naics": "3251", "emoji": "🔥", "benchmark": "gas",
     "desc": "Petroleum gases, a key feedstock and fuel for chemical plants",
     "freight": "bulk", "unit": "t", "price": 450.0, "origins": ["Trinidad and Tobago", "Nigeria"]},
    {"hs": "29", "name": "Basic Organic Chemicals", "naics": "3251", "emoji": "⚗️", "benchmark": "gas",
     "desc": "Ethylene, propylene, methanol and other organic chemicals",
     "freight": "container", "unit": "t", "price": 900.0, "payload": 20.0,
     "origins": ["China", "South Korea", "Saudi Arabia", "Netherlands"]},
    {"hs": "3901", "name": "Polyethylene", "naics": "3252", "emoji": "🧪", "benchmark": "brent",
     "desc": "Polymers of ethylene in primary forms (HDPE, LDPE, LLDPE)",
     "freight": "container", "unit": "t", "price": 1100.0, "payload": 24.0,
     "origins": ["Saudi Arabia", "South Korea", "China", "Netherlands"]},
    {"hs": "3901–3914", "name": "Plastics Resins (all)", "naics": "3252", "emoji": "🧪", "benchmark": "gas",
     "desc": "Polyethylene, polypropylene, PVC and other resins in primary forms",
     "freight": "container", "unit": "t", "price": 1150.0, "payload": 24.0,
     "origins": ["China", "South Korea", "Saudi Arabia", "Netherlands"]},
    {"hs": "5503", "name": "Polyester Staple Fiber", "naics": "3252", "emoji": "🧵", "benchmark": "brent",
     "desc": "Synthetic staple fibers of polyester, not carded or combed",
     "freight": "container", "unit": "t", "price": 1000.0, "payload": 20.0,
     "origins": ["China", "Vietnam", "India", "South Korea"]},
    {"hs": "31", "name": "Fertilizers", "naics": "3253", "emoji": "🌾", "benchmark": "gas",
     "desc": "Nitrogen and mixed fertilizers (natural gas is the main input)",
     "freight": "bulk", "unit": "t", "price": 400.0, "origins": ["Trinidad and Tobago", "Saudi Arabia", "Netherlands"]},
    {"hs": "38", "name": "Other Chemical Products", "naics": "3259", "emoji": "🧴", "benchmark": "wti",
     "desc": "Miscellaneous chemical products and additives",
     "freight": "container", "unit": "t", "price": 1500.0, "payload": 20.0,
     "origins": ["China", "Netherlands", "India"]},
    {"hs": "3916–3926", "name": "Plastics Products", "naics": "3261", "emoji": "📦", "benchmark": "wti",
     "desc": "Plastic film, sheet, pipe and other plastic products",
     "freight": "container", "unit": "t", "price": 2500.0, "payload": 15.0,
     "origins": ["China", "Vietnam", "Mexico"]},
]

BENCHMARKS = {"brent": ("Global Benchmark Price (Brent)", "/ bbl"),
              "wti": ("U.S. Benchmark Price (WTI)", "/ bbl"),
              "gas": ("Feedstock Price (Henry Hub gas)", "/ MMBtu")}

REGIONS = ["All Regions", "US Gulf Coast", "Middle East", "Europe", "Northeast Asia", "South America"]
HORIZONS = {"Next 1–3 months": 3, "Next 1–6 months": 6}


def product_label(p):
    return f"{p['name']} (HS {p['hs']})"


def products_for(industries: dict):
    """Keep only products whose industry exists in the dataset."""
    return [p for p in PRODUCTS if p["naics"] in industries]
