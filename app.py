"""Supply Chain Risk Dashboard - starter page (Step 2 smoke test)."""
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Supply Chain Risk Dashboard", layout="wide")
st.title("Supply Chain Risk Dashboard")
st.caption("Setup check: if you can see the chart below, your tools work.")

rng = np.random.default_rng(42)
df = pd.DataFrame({
    "Supplier": [f"Supplier {c}" for c in "ABCDEFGH"],
    "Lead time (days)": rng.integers(10, 60, 8),
    "On-time delivery (%)": rng.integers(75, 99, 8),
})
st.plotly_chart(px.bar(df, x="Supplier", y="Lead time (days)"), use_container_width=True)
st.dataframe(df, use_container_width=True)
