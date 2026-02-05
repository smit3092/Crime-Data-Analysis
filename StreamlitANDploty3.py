import pandas as pd
import streamlit as st
import plotly.express as px
from pathlib import Path

st.set_page_config(layout="wide")
st.title("Crime Data Explorer (with Map)")

DATA_PATH = "crime_safety_dataset.csv"
GEOCODES_PATH = "geocodes.csv"

@st.cache_data
def load_data(data_path: str) -> pd.DataFrame:
    df = pd.read_csv(data_path)

    # Build datetime
    df["datetime"] = pd.to_datetime(df["date"] + " " + df["time"], errors="coerce")

    # Build full_address EXACTLY the same way as your geocoding script did
    df["full_address"] = (
        df["location_description"].astype(str).str.strip()
        + ", " + df["city"].astype(str).str.strip()
        + ", " + df["state"].astype(str).str.strip()
    )

    return df

@st.cache_data
def load_geocodes(geocodes_path: str) -> pd.DataFrame:
    geo = pd.read_csv(geocodes_path)

    # Normalize merge key
    geo["full_address"] = geo["full_address"].astype(str).str.strip()

    # Ensure required columns exist
    required = {"full_address", "lat", "lon"}
    missing = required - set(geo.columns)
    if missing:
        raise ValueError(f"{geocodes_path} is missing columns: {sorted(missing)}")

    return geo[["full_address", "lat", "lon"]]

# ---- Load ----
df = load_data(DATA_PATH)

# ---- Merge geocodes.csv (this is the part you care about) ----
if not Path(GEOCODES_PATH).exists():
    st.error(f"Cannot find {GEOCODES_PATH} in the working directory. Put it next to this app file.")
    st.stop()

geo = load_geocodes(GEOCODES_PATH)
df = df.merge(geo, on="full_address", how="left")  # <-- references geocodes.csv

# ---- Filters ----
st.sidebar.header("Filters")

crime_types = ["All"] + sorted(df["crime_type"].dropna().unique().tolist())
crime_choice = st.sidebar.selectbox("Crime type", crime_types)

cities = ["All"] + sorted(df["city"].dropna().unique().tolist())
city_choice = st.sidebar.selectbox("City", cities)

# Apply filters
f = df.copy()
if crime_choice != "All":
    f = f[f["crime_type"] == crime_choice]
if city_choice != "All":
    f = f[f["city"] == city_choice]

# ---- Skip rows missing geocodes ----
mapped_df = f.dropna(subset=["lat", "lon"]).copy()
unmapped_df = f[f["lat"].isna() | f["lon"].isna()].copy()

# Show coverage so you can verify behavior
st.subheader("Geocode coverage")
c1, c2, c3 = st.columns(3)
c1.metric("Filtered rows", len(f))
c2.metric("Mapped (shown on map)", len(mapped_df))
c3.metric("Unmapped (hidden)", len(unmapped_df))

# ---- Map ----
st.subheader("Map (px.scatter_mapbox)")

if mapped_df.empty:
    st.info("No mapped rows to display under current filters (lat/lon missing).")
else:
    fig = px.scatter_mapbox(
        mapped_df,
        lat="lat",
        lon="lon",
        color="crime_type",
        hover_data={
            "datetime": True,
            "victim_age": True,
            "victim_gender": True,
            "victim_race": True,
            "city": True,
            "state": True,
            "location_description": True,
            "full_address": True,
            "lat": False,
            "lon": False,
        },
        zoom=10,
        height=650,
        title="Crime Incidents (mapped rows only)"
    )

    # No Mapbox token needed with open-street-map tiles
    fig.update_layout(mapbox_style="open-street-map", margin={"r": 0, "t": 40, "l": 0, "b": 0})
    st.plotly_chart(fig, use_container_width=True)

# ---- Tables ----
st.subheader("Data table")

show_unmapped = st.checkbox("Show unmapped rows in the table", value=False)

if show_unmapped:
    st.write("All filtered rows (including unmapped):")
    st.dataframe(f)
else:
    st.write("Mapped rows only (same rows shown on the map):")
    st.dataframe(mapped_df)
