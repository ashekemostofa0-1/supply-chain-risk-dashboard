"""
One-time check of the Freightos public estimate. Run:
    python debug_freightos.py
It tries a few request styles and prints what Freightos sends back.
"""
import requests

URL = "https://ship.freightos.com/api/shippingCalculator"
TRIES = [
    {"loadtype": "container40", "quantity": 1, "origin": "Shanghai, China", "destination": "Houston, TX, USA"},
    {"loadtype": "container40", "quantity": 1, "origin": "CNSHA", "destination": "USHOU"},
    {"loadtype": "container40", "quantity": 1, "origin": "Shanghai", "destination": "Houston"},
    {"loadtype": "container40", "quantity": 1, "origin": "CNSHA", "destination": "USHOU", "mode": "FCL"},
]
for i, p in enumerate(TRIES, 1):
    for fmt in ("json",):
        params = {**p, "estimate": "true", "format": fmt}
        try:
            r = requests.get(URL, params=params, headers={"User-Agent": "Mozilla/5.0"}, timeout=40)
            print(f"\n--- Try {i}: status {r.status_code}, url: {r.url}")
            print(r.text[:700])
        except Exception as e:
            print(f"\n--- Try {i}: ERROR {e!r}")
