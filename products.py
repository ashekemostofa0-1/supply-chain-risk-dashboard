"""
Products shown in the filter bar, linked to the six NAICS industries in the dashboard.

HS chapters/headings are the standard Harmonized System groups for each product family.
The benchmark tells the dashboard which live price to show for the product.
"""

PRODUCTS = [
    {"hs": "2709", "name": "Crude Oil", "naics": "3241", "emoji": "🛢️", "benchmark": "brent",
     "desc": "Petroleum oils & oils obtained from bituminous minerals, crude"},
    {"hs": "2710", "name": "Refined Petroleum Products", "naics": "3241", "emoji": "⛽", "benchmark": "wti",
     "desc": "Gasoline, diesel, jet fuel and other refined oils"},
    {"hs": "2711", "name": "Natural Gas & LNG", "naics": "3251", "emoji": "🔥", "benchmark": "gas",
     "desc": "Petroleum gases, a key feedstock and fuel for chemical plants"},
    {"hs": "29", "name": "Basic Organic Chemicals", "naics": "3251", "emoji": "⚗️", "benchmark": "gas",
     "desc": "Ethylene, propylene, methanol and other organic chemicals"},
    {"hs": "3901–3914", "name": "Plastics Resins", "naics": "3252", "emoji": "🧪", "benchmark": "gas",
     "desc": "Polyethylene, polypropylene, PVC and other resins in primary forms"},
    {"hs": "31", "name": "Fertilizers", "naics": "3253", "emoji": "🌾", "benchmark": "gas",
     "desc": "Nitrogen and mixed fertilizers (natural gas is the main input)"},
    {"hs": "38", "name": "Other Chemical Products", "naics": "3259", "emoji": "🧴", "benchmark": "wti",
     "desc": "Miscellaneous chemical products and additives"},
    {"hs": "3916–3926", "name": "Plastics Products", "naics": "3261", "emoji": "📦", "benchmark": "wti",
     "desc": "Plastic film, sheet, pipe and other plastic products"},
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
