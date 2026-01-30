import streamlit as st
import pandas as pd
import pydeck as pdk

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="Portfolio Savings Map")
st.title("🏡 Wildfire Resilience Portfolio Map")

# --- 1. LOAD DATA ---
@st.cache_data
def load_data():
    try:
        # Load CSV (Ensure 'Discount_Commentary' is in your CSV from the R script)
        df = pd.read_csv("pages/savings_data.csv")
    except FileNotFoundError:
        return pd.DataFrame()

    # Rename columns to standard names if needed
    column_map = {
        'average_prem': 'average_prem',
        'total_discount': 'total_discount',
        'Discount_Commentary': 'Discount_Commentary', # Ensure this matches your CSV header
        'address': 'address'
    }
    df = df.rename(columns=column_map)
    
    # Cleaning: Convert currency strings to numbers
    cols_to_clean = ['average_prem', 'total_discount', 'lat', 'lon']
    for col in cols_to_clean:
        if col in df.columns and df[col].dtype == 'object':
             df[col] = df[col].astype(str).str.replace('$', '').str.replace(',', '')
             df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Create a short text label for the map (e.g. "$1,200" -> "$1.2k")
    df['label'] = df['total_discount'].apply(lambda x: f"${x/1000:.1f}k" if x >= 1000 else f"${x:.0f}")
             
    return df.dropna(subset=['lat', 'lon'])

df = load_data()

if df.empty:
    st.error("⚠️ Could not find data. Check `pages/savings_data.csv`.")
    st.stop()

# --- 2. SIDEBAR FILTERS ---
st.sidebar.header("Filter Map")
min_savings = st.sidebar.slider("Min. Potential Savings", 0, int(df['total_discount'].max()), 0, step=100)
filtered_df = df[df['total_discount'] >= min_savings]

# --- 3. MAP CONFIGURATION ---

# A. Scatterplot Layer (The Dots)
# Green dots for high savings, Blue for low
filtered_df['color'] = filtered_df['total_discount'].apply(
    lambda x: [60, 179, 113, 200] if x >= 1000 else [30, 144, 255, 180]
)
# Size based on savings
filtered_df['radius'] = filtered_df['total_discount'].apply(lambda x: 20 + (x / 10))

scatter_layer = pdk.Layer(
    "ScatterplotLayer",
    filtered_df,
    get_position=["lon", "lat"],
    get_color="color",
    get_radius="radius",
    pickable=True,
    stroked=True,
    filled=True,
    line_width_min_pixels=1,
    radius_min_pixels=6,   # Minimum size so they don't disappear
    radius_max_pixels=30,  # Max size so they don't cover the map
)

# B. Text Layer (The "Redfin" Labels)
# This puts the "$1.5k" text directly above the dot
text_layer = pdk.Layer(
    "TextLayer",
    filtered_df,
    get_position=["lon", "lat"],
    get_text="label",
    get_color=[0, 0, 0, 200], # Black text
    get_size=16,
    get_angle=0,
    get_text_anchor="middle",
    get_alignment_baseline="bottom",
    pixel_offset=[0, -10] # Shift text up slightly so it floats above dot
)

# C. Map View settings
view_state = pdk.ViewState(
    latitude=filtered_df['lat'].mean(),
    longitude=filtered_df['lon'].mean(),
    zoom=12,
    pitch=0,
)

# D. The Tooltip (Popup on Hover)
tooltip = {
    "html": """
        <div style="font-family: sans-serif; padding: 8px; color: white; background-color: #1E1E1E; border-radius: 4px;">
            <b>{address}</b><br>
            Est. Premium: ${average_prem}<br>
            Potential Savings: <span style="color: #4CAF50;"><b>${total_discount}</b></span>
        </div>
    """,
    "style": {"color": "white"}
}

# --- 4. RENDER MAP ---
# map_style="roadmap" gives the Google Maps / Redfin look (streets + gray background)
st.pydeck_chart(pdk.Deck(
    map_style="mapbox://styles/mapbox/light-v9", # Clean "Redfin-style" light map
    initial_view_state=view_state,
    layers=[scatter_layer, text_layer], # Render both dots and text
    tooltip=tooltip
))

# --- 5. DETAILED DATA TABLE ---
st.markdown("### 📋 Property Savings Details")

# Format columns for display
display_cols = ['address', 'Discount_Commentary', 'average_prem', 'total_discount']

# Check if Discount_Commentary exists (in case CSV is old)
if 'Discount_Commentary' not in filtered_df.columns:
    filtered_df['Discount_Commentary'] = "No commentary available"

st.dataframe(
    filtered_df[display_cols].sort_values('total_discount', ascending=False),
    column_config={
        "address": "Property Address",
        "Discount_Commentary": st.column_config.TextColumn("Resilience Assessment", width="large"),
        "average_prem": st.column_config.NumberColumn("Avg Premium", format="$%d"),
        "total_discount": st.column_config.NumberColumn("Potential Savings", format="$%d"),
    },
    use_container_width=True,
    hide_index=True
)