import streamlit as st
import pandas as pd
import pydeck as pdk

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="Portfolio Savings Map")
st.title("🏡 Wildfire Resilience Portfolio Map")


# --- 1. PASSWORD PROTECTION ---
def check_password():
    """Returns `True` if the user had the correct password."""
    if st.session_state.get("password_correct", False):
        return True

    st.sidebar.header("🔒 Login")
    password = st.sidebar.text_input("Enter Password", type="password")
    
    if st.button("Log In"):
        if password == "Faura2026":  
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("😕 Password incorrect")
    return False

if not check_password():
    st.stop() 

# --- 2. LOAD DATA ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("pages/savings_data.csv")
    except FileNotFoundError:
        return pd.DataFrame()

    # Rename columns to standard names
    column_map = {
        'average_prem': 'average_prem',
        'total_discount': 'total_discount',
        'Discount_Commentary': 'Discount_Commentary',
        'address': 'address',
        'url': 'url'
    }
    df = df.rename(columns=column_map)
    
    # Cleaning: Convert currency strings to numbers
    cols_to_clean = ['average_prem', 'total_discount', 'lat', 'lon']
    for col in cols_to_clean:
        if col in df.columns and df[col].dtype == 'object':
             df[col] = df[col].astype(str).str.replace('$', '').str.replace(',', '')
             df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Create short text label ($1.2k)
    df['label'] = df['total_discount'].apply(lambda x: f"${x/1000:.1f}k" if x >= 1000 else f"${x:.0f}")
             
    return df.dropna(subset=['lat', 'lon'])

df = load_data()

if df.empty:
    st.error("⚠️ Could not find data. Check `pages/savings_data.csv`.")
    st.stop()

# --- 3. SIDEBAR FILTERS ---
st.sidebar.header("Filter Map")
min_savings = st.sidebar.slider("Min. Potential Savings", 0, int(df['total_discount'].max()), 0, step=100)
filtered_df = df[df['total_discount'] >= min_savings]

# --- 4. MAP CONFIGURATION ---

# A. Scatterplot Layer (The Dots)
filtered_df['color'] = filtered_df['total_discount'].apply(
    lambda x: [60, 179, 113, 200] if x >= 1000 else [30, 144, 255, 180]
)
# Dynamic size: bigger savings = bigger dots
filtered_df['radius'] = filtered_df['total_discount'].apply(lambda x: 25 + (x / 20))

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
    radius_min_pixels=6,
    radius_max_pixels=40,
)

# B. Text Layer (The Labels)
text_layer = pdk.Layer(
    "TextLayer",
    filtered_df,
    get_position=["lon", "lat"],
    get_text="label",
    get_color=[0, 0, 0, 200],
    get_size=16,
    get_angle=0,
    get_text_anchor="middle",
    get_alignment_baseline="bottom",
    pixel_offset=[0, -12] 
)

# C. AUTO-CENTERING LOGIC (The Fix) ------------------------
if not filtered_df.empty:
    # Use Median to find the center (avoids outliers throwing off the map)
    mid_lat = filtered_df['lat'].median()
    mid_lon = filtered_df['lon'].median()
    
    # Simple Auto-Zoom: Check the spread of data
    lat_spread = filtered_df['lat'].max() - filtered_df['lat'].min()
    lon_spread = filtered_df['lon'].max() - filtered_df['lon'].min()
    max_spread = max(lat_spread, lon_spread)

    # If spread is small (< 0.05 degrees), zoom in close (13). 
    # If spread is large (> 0.2 degrees), zoom out (10).
    if max_spread < 0.05:
        zoom_level = 13
    elif max_spread < 0.2:
        zoom_level = 11
    else:
        zoom_level = 9
else:
    # Default fallback (Sunnyvale-ish)
    mid_lat, mid_lon, zoom_level = 37.3688, -122.0363, 11

view_state = pdk.ViewState(
    latitude=mid_lat,
    longitude=mid_lon,
    zoom=zoom_level,
    pitch=0,
)
# ----------------------------------------------------------

# D. The Tooltip
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

# --- 5. RENDER MAP ---
# Using CARTO_LIGHT for the clean "Redfin" look without API keys
st.pydeck_chart(pdk.Deck(
    map_style=pdk.map_styles.CARTO_LIGHT,
    initial_view_state=view_state,
    layers=[scatter_layer, text_layer],
    tooltip=tooltip
))

# --- 6. DETAILED DATA TABLE ---
st.markdown("### 📋 Property Savings Details")

display_cols = ['address', 'url', 'Discount_Commentary', 'average_prem', 'total_discount']

# Ensure columns exist
for col in ['url', 'Discount_Commentary']:
    if col not in filtered_df.columns:
        filtered_df[col] = "N/A"

st.dataframe(
    filtered_df[display_cols].sort_values('total_discount', ascending=False),
    column_config={
        "address": "Property Address",
        "url": st.column_config.LinkColumn("Redfin Link", display_text="View on Redfin"),
        "Discount_Commentary": st.column_config.TextColumn("Resilience Assessment", width="large"),
        "average_prem": st.column_config.NumberColumn("Avg Premium", format="$%d"),
        "total_discount": st.column_config.NumberColumn("Potential Savings", format="$%d"),
    },
    use_container_width=True,
    hide_index=True
)