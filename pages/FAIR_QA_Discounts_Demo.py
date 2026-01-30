import streamlit as st
import pandas as pd
import pydeck as pdk

# --- PAGE CONFIG ---
st.set_page_config(layout="wide", page_title="Portfolio Savings Map")
st.title("🏡 Wildfire Resilience Portfolio Map")

# --- 1. LOAD DATA ---
@st.cache_data
def load_data():
    # ADJUST FILE PATH IF NECESSARY
    try:
        df = pd.read_csv("pages/savings_data.csv")
    except FileNotFoundError:
        return pd.DataFrame() # Return empty if not found to handle gracefully

    # --- RENAME COLUMNS TO MATCH MAP LOGIC ---
    # We only care about premium and discounts now
    column_map = {
        'average_prem': 'average_prem',
        'total_discount': 'total_discount'
    }
    df = df.rename(columns=column_map)
    
    # Ensure numeric data is actually numeric (removes '$' or ',' if present)
    cols_to_clean = ['average_prem', 'total_discount', 'lat', 'lon']
    for col in cols_to_clean:
        if col in df.columns and df[col].dtype == 'object':
             df[col] = df[col].astype(str).str.replace('$', '').str.replace(',', '')
             df[col] = pd.to_numeric(df[col], errors='coerce')
             
    return df.dropna(subset=['lat', 'lon']) # Drop rows without geo-coordinates

df = load_data()

if df.empty:
    st.error("⚠️ Could not find `savings_data.csv` or it is empty. Please upload the CSV to the app folder.")
    st.stop()

# --- 2. SIDEBAR FILTERS ---
st.sidebar.header("Filter Map")
min_savings = st.sidebar.slider("Min. Potential Savings", 0, int(df['total_discount'].max()), 0, step=100)

# Apply Filters
filtered_df = df[df['total_discount'] >= min_savings]

# --- 3. COLOR & SIZE LOGIC (SAVINGS ONLY) ---
def get_color(savings):
    # Color by Savings Amount instead of Risk
    # High Savings ($2000+) -> Green
    # Med Savings ($1000+) -> Teal
    # Low Savings        -> Blue
    if savings >= 2000: return [60, 179, 113, 200]    # Green (High Priority)
    if savings >= 1000: return [32, 178, 170, 200]    # Light Sea Green
    return [30, 144, 255, 200]                        # Blue

# Apply color function
filtered_df['color'] = filtered_df['total_discount'].apply(get_color)

# Scale the dot size: Base size (10) + Scaled Discount
filtered_df['radius'] = filtered_df['total_discount'].apply(lambda x: 15 + (x / 20))

# --- 4. RENDER MAP ---
if not filtered_df.empty:
    # Tooltip Logic (HTML/CSS)
    # Removed Risk Rating from the popup since we don't have it
    tooltip = {
        "html": """
            <div style="font-family: sans-serif; padding: 10px; color: white; background-color: #0E1117; border: 1px solid #333; border-radius: 5px;">
                <b style="font-size: 14px;">{address}</b><br>
                <span style="color: #888; font-size: 12px;">{city}, {state}</span>
                <hr style="margin: 5px 0; border-color: #444;">
                Est. Premium: <b>${average_prem}</b><br>
                Potential Savings: <b style="color: #4CAF50;">${total_discount}</b>
            </div>
        """,
        "style": {"backgroundColor": "transparent", "color": "white"}
    }

    layer = pdk.Layer(
        "ScatterplotLayer",
        filtered_df,
        get_position=["lon", "lat"],
        get_color="color",
        get_radius="radius",
        pickable=True,
        opacity=0.8,
        stroked=True,
        filled=True,
        radius_scale=1,
        radius_min_pixels=5,
        radius_max_pixels=60,
    )

    # Auto-center map on the data
    view_state = pdk.ViewState(
        latitude=filtered_df['lat'].mean(),
        longitude=filtered_df['lon'].mean(),
        zoom=11,
        pitch=0,
    )

    st.pydeck_chart(pdk.Deck(
        layers=[layer],
        initial_view_state=view_state,
        tooltip=tooltip,
        map_style="mapbox://styles/mapbox/light-v10"
    ))

    # --- 5. SUMMARY METRICS ---
    col1, col2, col3 = st.columns(3)
    col1.metric("Homes Displayed", len(filtered_df))
    col2.metric("Total Opportunity", f"${filtered_df['total_discount'].sum():,.0f}")
    col3.metric("Avg Savings / Home", f"${filtered_df['total_discount'].mean():,.0f}")

    # Optional: Simple data table below
    st.markdown("### High Opportunity Targets")
    st.dataframe(
        filtered_df[['address', 'city', 'state', 'average_prem', 'total_discount']]
        .sort_values('total_discount', ascending=False)
        .head(10)
        .style.format({'average_prem': "${:,.0f}", 'total_discount': "${:,.0f}"}),
        use_container_width=True
    )

else:
    st.warning("No homes match the selected filters.")