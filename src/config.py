"""Project scope (Step 4): industries and years covered by the risk dashboard.

Every other script imports these values, so the scope is defined in one place.
"""

# 4-digit NAICS industries in scope (code -> short name)
INDUSTRIES = {
    "3241": "Petroleum and coal products",
    "3251": "Basic chemicals",
    "3252": "Resins and synthetic rubber",
    "3253": "Fertilizers and pesticides",
    "3259": "Other chemical products",
    "3261": "Plastics products",
}

# Study period (inclusive)
START_YEAR = 2019
END_YEAR = 2024
YEARS = list(range(START_YEAR, END_YEAR + 1))

# Folders
RAW_DIR = "data/raw"      # downloaded files, never edited by hand
CLEAN_DIR = "data/clean"  # merged dataset written by build_dataset.py
