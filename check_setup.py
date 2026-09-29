"""Step 2 check: confirms Python and every required library are installed."""
import sys
import importlib

REQUIRED = ["pandas", "numpy", "streamlit", "plotly", "scipy", "openpyxl", "pytest"]

print(f"Python {sys.version.split()[0]}")
ok = sys.version_info >= (3, 11)
print("  OK" if ok else "  NEEDS 3.11 OR NEWER")

for name in REQUIRED:
    try:
        mod = importlib.import_module(name)
        print(f"{name:<10} {getattr(mod, '__version__', 'installed')}")
    except ImportError:
        ok = False
        print(f"{name:<10} MISSING  -> pip install {name}")

print("\nAll set." if ok else "\nFix the items above, then run this again.")
