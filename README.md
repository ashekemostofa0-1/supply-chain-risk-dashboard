# Supply Chain Risk Dashboard

Course project 1 (Lamar University, M.S. Engineering Management).
Interactive dashboard that scores and compares supply-chain risk across U.S.
manufacturing industries, built with Python and Streamlit.

## Scope

Six industries at the 4-digit NAICS level, 2019–2024:

| NAICS | Industry |
|-------|----------|
| 3241 | Petroleum and coal products |
| 3251 | Basic chemicals |
| 3252 | Resins and synthetic rubber |
| 3253 | Fertilizers and pesticides |
| 3259 | Other chemical products |
| 3261 | Plastics products |

Census manufacturing surveys changed during this period, so some
industry-year values may be missing. Gaps are documented, not guessed.
The scope is defined in `src/config.py`.

## Project structure

```
data/raw/            downloaded files, untouched
data/clean/          merged dataset
src/config.py        scope: industries and years
src/build_dataset.py cleaning + merging
src/risk_index.py    the 3 weighting methods
src/validate.py      testing the methods
tests/               pytest tests
app.py               Streamlit dashboard
```

## Setup

```
python -m venv .venv
.venv\Scripts\activate          # Windows (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python check_setup.py
pytest
streamlit run app.py
```
