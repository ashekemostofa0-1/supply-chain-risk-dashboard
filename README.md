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

<!-- SOURCES START -->
## Data sources

Raw files in `data/raw/` are saved exactly as downloaded by `python -m src.download_data`. Each file name links to its source URL.

| Indicator | Source | NAICS | Year | File | Downloaded | Status |
|---|---|---|---|---|---|---|
| shipments/energy/labor | Census ASM | 3241 | 2019 | [data/raw/census_asm/asm_3241_2019.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2019&NAICS2017=3241) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3241 | 2020 | [data/raw/census_asm/asm_3241_2020.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2020&NAICS2017=3241) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3241 | 2021 | [data/raw/census_asm/asm_3241_2021.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2021&NAICS2017=3241) | 2026-09-29 | ok |
| shipments/energy/labor | Census Economic Census 2022 | 3241 | 2022 | [data/raw/census_ec/ec_3241_2022.json](https://api.census.gov/data/2022/ecnbasic?get=NAICS2022_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&NAICS2022=3241) | 2026-09-29 | ok |
| shipments/labor | Census AIES basic | 3241 | 2023 | [data/raw/census_aies/aies_basic_3241_2023.json](https://api.census.gov/data/2023/aiesbasic?get=NAICS2017_LABEL,RCPT_TOT_VAL,PAY_ANN_VAL,EMP_MAR12_NUM&for=us:*&YEAR=2023&NAICS2017=3241) | 2026-09-29 | ok |
| energy | Census AIES expenses | 3241 | 2023 | [data/raw/census_aies/aies_exp_3241_2023.json](https://api.census.gov/data/2023/aiesexp02?get=NAICS2017_LABEL,EXPS_ELEC_VAL,EXPS_FUEL_VAL&for=us:*&YEAR=2023&NAICS2017=3241) | 2026-09-29 | ok |
| shipments/labor | Census AIES basic | 3241 | 2024 | [data/raw/census_aies/aies_basic_3241_2024.json](https://api.census.gov/data/2024/aiesbasic?get=NAICS2017_LABEL,RCPT_TOT_VAL,PAY_ANN_VAL,EMP_MAR12_NUM&for=us:*&YEAR=2024&NAICS2017=3241) | 2026-09-29 | ok |
| energy | Census AIES expenses | 3241 | 2024 | [data/raw/census_aies/aies_exp_3241_2024.json](https://api.census.gov/data/2024/aiesexp02?get=NAICS2017_LABEL,EXPS_ELEC_VAL,EXPS_FUEL_VAL&for=us:*&YEAR=2024&NAICS2017=3241) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3241 | 2019 | [data/raw/census_trade/imports_3241_2019.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2019-12&NAICS=3241) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3241 | 2019 | [data/raw/census_trade/exports_3241_2019.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2019-12&NAICS=3241) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3241 | 2020 | [data/raw/census_trade/imports_3241_2020.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2020-12&NAICS=3241) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3241 | 2020 | [data/raw/census_trade/exports_3241_2020.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2020-12&NAICS=3241) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3241 | 2021 | [data/raw/census_trade/imports_3241_2021.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2021-12&NAICS=3241) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3241 | 2021 | [data/raw/census_trade/exports_3241_2021.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2021-12&NAICS=3241) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3241 | 2022 | [data/raw/census_trade/imports_3241_2022.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2022-12&NAICS=3241) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3241 | 2022 | [data/raw/census_trade/exports_3241_2022.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2022-12&NAICS=3241) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3241 | 2023 | [data/raw/census_trade/imports_3241_2023.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2023-12&NAICS=3241) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3241 | 2023 | [data/raw/census_trade/exports_3241_2023.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2023-12&NAICS=3241) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3241 | 2024 | [data/raw/census_trade/imports_3241_2024.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2024-12&NAICS=3241) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3241 | 2024 | [data/raw/census_trade/exports_3241_2024.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2024-12&NAICS=3241) | 2026-09-29 | ok |
| price volatility | FRED PPI by industry | 3241 | all | [data/raw/fred_ppi/PCU32413241.csv](https://fred.stlouisfed.org/graph/fredgraph.csv?id=PCU32413241) | 2026-09-29 | ok |
| validation target | FRED Industrial Production | 3241 | all | [data/raw/fred_ip/IPG324S.csv](https://fred.stlouisfed.org/graph/fredgraph.csv?id=IPG324S) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3251 | 2019 | [data/raw/census_asm/asm_3251_2019.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2019&NAICS2017=3251) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3251 | 2020 | [data/raw/census_asm/asm_3251_2020.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2020&NAICS2017=3251) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3251 | 2021 | [data/raw/census_asm/asm_3251_2021.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2021&NAICS2017=3251) | 2026-09-29 | ok |
| shipments/energy/labor | Census Economic Census 2022 | 3251 | 2022 | [data/raw/census_ec/ec_3251_2022.json](https://api.census.gov/data/2022/ecnbasic?get=NAICS2022_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&NAICS2022=3251) | 2026-09-29 | ok |
| shipments/labor | Census AIES basic | 3251 | 2023 | [data/raw/census_aies/aies_basic_3251_2023.json](https://api.census.gov/data/2023/aiesbasic?get=NAICS2017_LABEL,RCPT_TOT_VAL,PAY_ANN_VAL,EMP_MAR12_NUM&for=us:*&YEAR=2023&NAICS2017=3251) | 2026-09-29 | ok |
| energy | Census AIES expenses | 3251 | 2023 | [data/raw/census_aies/aies_exp_3251_2023.json](https://api.census.gov/data/2023/aiesexp02?get=NAICS2017_LABEL,EXPS_ELEC_VAL,EXPS_FUEL_VAL&for=us:*&YEAR=2023&NAICS2017=3251) | 2026-09-29 | ok |
| shipments/labor | Census AIES basic | 3251 | 2024 | [data/raw/census_aies/aies_basic_3251_2024.json](https://api.census.gov/data/2024/aiesbasic?get=NAICS2017_LABEL,RCPT_TOT_VAL,PAY_ANN_VAL,EMP_MAR12_NUM&for=us:*&YEAR=2024&NAICS2017=3251) | 2026-09-29 | ok |
| energy | Census AIES expenses | 3251 | 2024 | [data/raw/census_aies/aies_exp_3251_2024.json](https://api.census.gov/data/2024/aiesexp02?get=NAICS2017_LABEL,EXPS_ELEC_VAL,EXPS_FUEL_VAL&for=us:*&YEAR=2024&NAICS2017=3251) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3251 | 2019 | [data/raw/census_trade/imports_3251_2019.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2019-12&NAICS=3251) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3251 | 2019 | [data/raw/census_trade/exports_3251_2019.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2019-12&NAICS=3251) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3251 | 2020 | [data/raw/census_trade/imports_3251_2020.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2020-12&NAICS=3251) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3251 | 2020 | [data/raw/census_trade/exports_3251_2020.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2020-12&NAICS=3251) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3251 | 2021 | [data/raw/census_trade/imports_3251_2021.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2021-12&NAICS=3251) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3251 | 2021 | [data/raw/census_trade/exports_3251_2021.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2021-12&NAICS=3251) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3251 | 2022 | [data/raw/census_trade/imports_3251_2022.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2022-12&NAICS=3251) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3251 | 2022 | [data/raw/census_trade/exports_3251_2022.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2022-12&NAICS=3251) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3251 | 2023 | [data/raw/census_trade/imports_3251_2023.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2023-12&NAICS=3251) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3251 | 2023 | [data/raw/census_trade/exports_3251_2023.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2023-12&NAICS=3251) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3251 | 2024 | [data/raw/census_trade/imports_3251_2024.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2024-12&NAICS=3251) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3251 | 2024 | [data/raw/census_trade/exports_3251_2024.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2024-12&NAICS=3251) | 2026-09-29 | ok |
| price volatility | FRED PPI by industry | 3251 | all | [data/raw/fred_ppi/PCU32513251.csv](https://fred.stlouisfed.org/graph/fredgraph.csv?id=PCU32513251) | 2026-09-29 | ok |
| validation target | FRED Industrial Production | 3251 | all | [data/raw/fred_ip/IPG3251S.csv](https://fred.stlouisfed.org/graph/fredgraph.csv?id=IPG3251S) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3252 | 2019 | [data/raw/census_asm/asm_3252_2019.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2019&NAICS2017=3252) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3252 | 2020 | [data/raw/census_asm/asm_3252_2020.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2020&NAICS2017=3252) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3252 | 2021 | [data/raw/census_asm/asm_3252_2021.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2021&NAICS2017=3252) | 2026-09-29 | ok |
| shipments/energy/labor | Census Economic Census 2022 | 3252 | 2022 | [data/raw/census_ec/ec_3252_2022.json](https://api.census.gov/data/2022/ecnbasic?get=NAICS2022_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&NAICS2022=3252) | 2026-09-29 | ok |
| shipments/labor | Census AIES basic | 3252 | 2023 | [data/raw/census_aies/aies_basic_3252_2023.json](https://api.census.gov/data/2023/aiesbasic?get=NAICS2017_LABEL,RCPT_TOT_VAL,PAY_ANN_VAL,EMP_MAR12_NUM&for=us:*&YEAR=2023&NAICS2017=3252) | 2026-09-29 | ok |
| energy | Census AIES expenses | 3252 | 2023 | [data/raw/census_aies/aies_exp_3252_2023.json](https://api.census.gov/data/2023/aiesexp02?get=NAICS2017_LABEL,EXPS_ELEC_VAL,EXPS_FUEL_VAL&for=us:*&YEAR=2023&NAICS2017=3252) | 2026-09-29 | ok |
| shipments/labor | Census AIES basic | 3252 | 2024 | [data/raw/census_aies/aies_basic_3252_2024.json](https://api.census.gov/data/2024/aiesbasic?get=NAICS2017_LABEL,RCPT_TOT_VAL,PAY_ANN_VAL,EMP_MAR12_NUM&for=us:*&YEAR=2024&NAICS2017=3252) | 2026-09-29 | ok |
| energy | Census AIES expenses | 3252 | 2024 | [data/raw/census_aies/aies_exp_3252_2024.json](https://api.census.gov/data/2024/aiesexp02?get=NAICS2017_LABEL,EXPS_ELEC_VAL,EXPS_FUEL_VAL&for=us:*&YEAR=2024&NAICS2017=3252) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3252 | 2019 | [data/raw/census_trade/imports_3252_2019.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2019-12&NAICS=3252) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3252 | 2019 | [data/raw/census_trade/exports_3252_2019.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2019-12&NAICS=3252) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3252 | 2020 | [data/raw/census_trade/imports_3252_2020.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2020-12&NAICS=3252) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3252 | 2020 | [data/raw/census_trade/exports_3252_2020.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2020-12&NAICS=3252) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3252 | 2021 | [data/raw/census_trade/imports_3252_2021.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2021-12&NAICS=3252) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3252 | 2021 | [data/raw/census_trade/exports_3252_2021.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2021-12&NAICS=3252) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3252 | 2022 | [data/raw/census_trade/imports_3252_2022.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2022-12&NAICS=3252) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3252 | 2022 | [data/raw/census_trade/exports_3252_2022.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2022-12&NAICS=3252) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3252 | 2023 | [data/raw/census_trade/imports_3252_2023.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2023-12&NAICS=3252) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3252 | 2023 | [data/raw/census_trade/exports_3252_2023.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2023-12&NAICS=3252) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3252 | 2024 | [data/raw/census_trade/imports_3252_2024.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2024-12&NAICS=3252) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3252 | 2024 | [data/raw/census_trade/exports_3252_2024.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2024-12&NAICS=3252) | 2026-09-29 | ok |
| price volatility | FRED PPI by industry | 3252 | all | [data/raw/fred_ppi/PCU32523252.csv](https://fred.stlouisfed.org/graph/fredgraph.csv?id=PCU32523252) | 2026-09-29 | ok |
| validation target | FRED Industrial Production | 3252 | all | [data/raw/fred_ip/IPG3252S.csv](https://fred.stlouisfed.org/graph/fredgraph.csv?id=IPG3252S) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3253 | 2019 | [data/raw/census_asm/asm_3253_2019.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2019&NAICS2017=3253) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3253 | 2020 | [data/raw/census_asm/asm_3253_2020.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2020&NAICS2017=3253) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3253 | 2021 | [data/raw/census_asm/asm_3253_2021.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2021&NAICS2017=3253) | 2026-09-29 | ok |
| shipments/energy/labor | Census Economic Census 2022 | 3253 | 2022 | [data/raw/census_ec/ec_3253_2022.json](https://api.census.gov/data/2022/ecnbasic?get=NAICS2022_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&NAICS2022=3253) | 2026-09-29 | ok |
| shipments/labor | Census AIES basic | 3253 | 2023 | [data/raw/census_aies/aies_basic_3253_2023.json](https://api.census.gov/data/2023/aiesbasic?get=NAICS2017_LABEL,RCPT_TOT_VAL,PAY_ANN_VAL,EMP_MAR12_NUM&for=us:*&YEAR=2023&NAICS2017=3253) | 2026-09-29 | ok |
| energy | Census AIES expenses | 3253 | 2023 | [data/raw/census_aies/aies_exp_3253_2023.json](https://api.census.gov/data/2023/aiesexp02?get=NAICS2017_LABEL,EXPS_ELEC_VAL,EXPS_FUEL_VAL&for=us:*&YEAR=2023&NAICS2017=3253) | 2026-09-29 | ok |
| shipments/labor | Census AIES basic | 3253 | 2024 | [data/raw/census_aies/aies_basic_3253_2024.json](https://api.census.gov/data/2024/aiesbasic?get=NAICS2017_LABEL,RCPT_TOT_VAL,PAY_ANN_VAL,EMP_MAR12_NUM&for=us:*&YEAR=2024&NAICS2017=3253) | 2026-09-29 | ok |
| energy | Census AIES expenses | 3253 | 2024 | [data/raw/census_aies/aies_exp_3253_2024.json](https://api.census.gov/data/2024/aiesexp02?get=NAICS2017_LABEL,EXPS_ELEC_VAL,EXPS_FUEL_VAL&for=us:*&YEAR=2024&NAICS2017=3253) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3253 | 2019 | [data/raw/census_trade/imports_3253_2019.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2019-12&NAICS=3253) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3253 | 2019 | [data/raw/census_trade/exports_3253_2019.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2019-12&NAICS=3253) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3253 | 2020 | [data/raw/census_trade/imports_3253_2020.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2020-12&NAICS=3253) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3253 | 2020 | [data/raw/census_trade/exports_3253_2020.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2020-12&NAICS=3253) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3253 | 2021 | [data/raw/census_trade/imports_3253_2021.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2021-12&NAICS=3253) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3253 | 2021 | [data/raw/census_trade/exports_3253_2021.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2021-12&NAICS=3253) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3253 | 2022 | [data/raw/census_trade/imports_3253_2022.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2022-12&NAICS=3253) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3253 | 2022 | [data/raw/census_trade/exports_3253_2022.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2022-12&NAICS=3253) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3253 | 2023 | [data/raw/census_trade/imports_3253_2023.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2023-12&NAICS=3253) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3253 | 2023 | [data/raw/census_trade/exports_3253_2023.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2023-12&NAICS=3253) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3253 | 2024 | [data/raw/census_trade/imports_3253_2024.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2024-12&NAICS=3253) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3253 | 2024 | [data/raw/census_trade/exports_3253_2024.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2024-12&NAICS=3253) | 2026-09-29 | ok |
| price volatility | FRED PPI by industry | 3253 | all | [data/raw/fred_ppi/PCU32533253.csv](https://fred.stlouisfed.org/graph/fredgraph.csv?id=PCU32533253) | 2026-09-29 | ok |
| validation target | FRED Industrial Production | 3253 | all | [data/raw/fred_ip/IPG3253S.csv](https://fred.stlouisfed.org/graph/fredgraph.csv?id=IPG3253S) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3259 | 2019 | [data/raw/census_asm/asm_3259_2019.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2019&NAICS2017=3259) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3259 | 2020 | [data/raw/census_asm/asm_3259_2020.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2020&NAICS2017=3259) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3259 | 2021 | [data/raw/census_asm/asm_3259_2021.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2021&NAICS2017=3259) | 2026-09-29 | ok |
| shipments/energy/labor | Census Economic Census 2022 | 3259 | 2022 | [data/raw/census_ec/ec_3259_2022.json](https://api.census.gov/data/2022/ecnbasic?get=NAICS2022_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&NAICS2022=3259) | 2026-09-29 | ok |
| shipments/labor | Census AIES basic | 3259 | 2023 | [data/raw/census_aies/aies_basic_3259_2023.json](https://api.census.gov/data/2023/aiesbasic?get=NAICS2017_LABEL,RCPT_TOT_VAL,PAY_ANN_VAL,EMP_MAR12_NUM&for=us:*&YEAR=2023&NAICS2017=3259) | 2026-09-29 | ok |
| energy | Census AIES expenses | 3259 | 2023 | [data/raw/census_aies/aies_exp_3259_2023.json](https://api.census.gov/data/2023/aiesexp02?get=NAICS2017_LABEL,EXPS_ELEC_VAL,EXPS_FUEL_VAL&for=us:*&YEAR=2023&NAICS2017=3259) | 2026-09-29 | ok |
| shipments/labor | Census AIES basic | 3259 | 2024 | [data/raw/census_aies/aies_basic_3259_2024.json](https://api.census.gov/data/2024/aiesbasic?get=NAICS2017_LABEL,RCPT_TOT_VAL,PAY_ANN_VAL,EMP_MAR12_NUM&for=us:*&YEAR=2024&NAICS2017=3259) | 2026-09-29 | ok |
| energy | Census AIES expenses | 3259 | 2024 | [data/raw/census_aies/aies_exp_3259_2024.json](https://api.census.gov/data/2024/aiesexp02?get=NAICS2017_LABEL,EXPS_ELEC_VAL,EXPS_FUEL_VAL&for=us:*&YEAR=2024&NAICS2017=3259) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3259 | 2019 | [data/raw/census_trade/imports_3259_2019.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2019-12&NAICS=3259) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3259 | 2019 | [data/raw/census_trade/exports_3259_2019.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2019-12&NAICS=3259) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3259 | 2020 | [data/raw/census_trade/imports_3259_2020.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2020-12&NAICS=3259) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3259 | 2020 | [data/raw/census_trade/exports_3259_2020.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2020-12&NAICS=3259) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3259 | 2021 | [data/raw/census_trade/imports_3259_2021.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2021-12&NAICS=3259) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3259 | 2021 | [data/raw/census_trade/exports_3259_2021.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2021-12&NAICS=3259) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3259 | 2022 | [data/raw/census_trade/imports_3259_2022.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2022-12&NAICS=3259) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3259 | 2022 | [data/raw/census_trade/exports_3259_2022.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2022-12&NAICS=3259) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3259 | 2023 | [data/raw/census_trade/imports_3259_2023.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2023-12&NAICS=3259) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3259 | 2023 | [data/raw/census_trade/exports_3259_2023.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2023-12&NAICS=3259) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3259 | 2024 | [data/raw/census_trade/imports_3259_2024.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2024-12&NAICS=3259) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3259 | 2024 | [data/raw/census_trade/exports_3259_2024.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2024-12&NAICS=3259) | 2026-09-29 | ok |
| price volatility | FRED PPI by industry | 3259 | all | [data/raw/fred_ppi/PCU32593259.csv](https://fred.stlouisfed.org/graph/fredgraph.csv?id=PCU32593259) | 2026-09-29 | ok |
| validation target | FRED Industrial Production | 3259 | all | [data/raw/fred_ip/IPG3255A9S.csv](https://fred.stlouisfed.org/graph/fredgraph.csv?id=IPG3255A9S) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3261 | 2019 | [data/raw/census_asm/asm_3261_2019.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2019&NAICS2017=3261) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3261 | 2020 | [data/raw/census_asm/asm_3261_2020.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2020&NAICS2017=3261) | 2026-09-29 | ok |
| shipments/energy/labor | Census ASM | 3261 | 2021 | [data/raw/census_asm/asm_3261_2021.json](https://api.census.gov/data/timeseries/asm/area2017?get=NAICS2017_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&YEAR=2021&NAICS2017=3261) | 2026-09-29 | ok |
| shipments/energy/labor | Census Economic Census 2022 | 3261 | 2022 | [data/raw/census_ec/ec_3261_2022.json](https://api.census.gov/data/2022/ecnbasic?get=NAICS2022_LABEL,RCPTOT,PAYANN,EMP,CSTELEC,CSTFU&for=us:*&NAICS2022=3261) | 2026-09-29 | ok |
| shipments/labor | Census AIES basic | 3261 | 2023 | [data/raw/census_aies/aies_basic_3261_2023.json](https://api.census.gov/data/2023/aiesbasic?get=NAICS2017_LABEL,RCPT_TOT_VAL,PAY_ANN_VAL,EMP_MAR12_NUM&for=us:*&YEAR=2023&NAICS2017=3261) | 2026-09-29 | ok |
| energy | Census AIES expenses | 3261 | 2023 | [data/raw/census_aies/aies_exp_3261_2023.json](https://api.census.gov/data/2023/aiesexp02?get=NAICS2017_LABEL,EXPS_ELEC_VAL,EXPS_FUEL_VAL&for=us:*&YEAR=2023&NAICS2017=3261) | 2026-09-29 | ok |
| shipments/labor | Census AIES basic | 3261 | 2024 | [data/raw/census_aies/aies_basic_3261_2024.json](https://api.census.gov/data/2024/aiesbasic?get=NAICS2017_LABEL,RCPT_TOT_VAL,PAY_ANN_VAL,EMP_MAR12_NUM&for=us:*&YEAR=2024&NAICS2017=3261) | 2026-09-29 | ok |
| energy | Census AIES expenses | 3261 | 2024 | [data/raw/census_aies/aies_exp_3261_2024.json](https://api.census.gov/data/2024/aiesexp02?get=NAICS2017_LABEL,EXPS_ELEC_VAL,EXPS_FUEL_VAL&for=us:*&YEAR=2024&NAICS2017=3261) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3261 | 2019 | [data/raw/census_trade/imports_3261_2019.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2019-12&NAICS=3261) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3261 | 2019 | [data/raw/census_trade/exports_3261_2019.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2019-12&NAICS=3261) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3261 | 2020 | [data/raw/census_trade/imports_3261_2020.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2020-12&NAICS=3261) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3261 | 2020 | [data/raw/census_trade/exports_3261_2020.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2020-12&NAICS=3261) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3261 | 2021 | [data/raw/census_trade/imports_3261_2021.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2021-12&NAICS=3261) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3261 | 2021 | [data/raw/census_trade/exports_3261_2021.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2021-12&NAICS=3261) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3261 | 2022 | [data/raw/census_trade/imports_3261_2022.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2022-12&NAICS=3261) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3261 | 2022 | [data/raw/census_trade/exports_3261_2022.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2022-12&NAICS=3261) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3261 | 2023 | [data/raw/census_trade/imports_3261_2023.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2023-12&NAICS=3261) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3261 | 2023 | [data/raw/census_trade/exports_3261_2023.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2023-12&NAICS=3261) | 2026-09-29 | ok |
| import dependence | Census trade: imports | 3261 | 2024 | [data/raw/census_trade/imports_3261_2024.json](https://api.census.gov/data/timeseries/intltrade/imports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,GEN_VAL_YR&time=2024-12&NAICS=3261) | 2026-09-29 | ok |
| import dependence | Census trade: exports | 3261 | 2024 | [data/raw/census_trade/exports_3261_2024.json](https://api.census.gov/data/timeseries/intltrade/exports/naics?get=NAICS_LDESC,CTY_CODE,CTY_NAME,ALL_VAL_YR&time=2024-12&NAICS=3261) | 2026-09-29 | ok |
| price volatility | FRED PPI by industry | 3261 | all | [data/raw/fred_ppi/PCU32613261.csv](https://fred.stlouisfed.org/graph/fredgraph.csv?id=PCU32613261) | 2026-09-29 | ok |
| validation target | FRED Industrial Production | 3261 | all | [data/raw/fred_ip/IPG3261S.csv](https://fred.stlouisfed.org/graph/fredgraph.csv?id=IPG3261S) | 2026-09-29 | ok |
<!-- SOURCES END -->
