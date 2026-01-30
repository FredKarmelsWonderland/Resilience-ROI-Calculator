import streamlit as st
import pandas as pd
import pydeck as pdk

# --- 1. PAGE CONFIG (MUST BE FIRST) ---
st.set_page_config(layout="wide", page_title="Portfolio Savings Map")

# --- 2. STANDARDIZED LOGIN BLOCK ---
def check_password():
    """Returns `True` if the user had the correct password."""
    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Faura Portfolio Map")
    
    with st.form("login_form"):
        st.write("Please enter the access code to view the map.")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In")
        
        if submitted:
            if password == "Faura2026":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Password incorrect")
    return False

if not check_password():
    st.stop()

# --- 3. MAIN APP CONTENT ---
st.title("🏡 Wildfire Resilience Portfolio Map")

# --- 4. LOAD DATA ---
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
    
    # Cleaning
    cols_to_clean = ['average_prem', 'total_discount', 'lat', 'lon']
    for col in cols_to_clean:
        if col in df.columns and df[col].dtype == 'object':
             df[col] = df[col].astype(str).str.replace('$', '').str.replace(',', '')
             df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Label for map
    df['label'] = df['total_discount'].apply(lambda x: f"${x/1000:.1f}k" if x >= 1000 else f"${x:.0f}")
             
    return df.dropna(subset=['lat', 'lon'])

df = load_data()

if df.empty:
    st.error("⚠️ Could not find data. Check `pages/savings_data.csv`.")
    st.stop()

# --- 5. TOP-LEVEL METRICS WIDGETS ---
# Calculate the KPIs
total_homes = len(df)
homes_with_savings = len(df[df['total_discount'] > 0])
avg_premium = df['average_prem'].mean()
avg_savings = df['total_discount'].mean()
total_savings = df['total_discount'].sum()

# Display KPIs in 5 columns
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

kpi1.metric("Total Homes", f"{total_homes}")
kpi2.metric("Homes w/ Savings", f"{homes_with_savings}")
kpi3.metric("Avg Premium", f"${avg_premium:,.0f}")
kpi4.metric("Avg Savings / Home", f"${avg_savings:,.0f}")
kpi5.metric("Total Portfolio Savings", f"${total_savings:,.0f}")

st.markdown("---") # Divider line

# --- 6. SIDEBAR FILTERS ---
st.sidebar.header("Filter Map")
min_savings = st.sidebar.slider("Min. Potential Savings", 0, int(df['total_discount'].max()), 0, step=100)
filtered_df = df[df['total_discount'] >= min_savings]

# --- 7. MAP CONFIGURATION ---

# A. Color Coding Logic
def get_color(savings):
    if savings >= 2500:
        return [0, 100, 0, 200]      # Dark Green (High Value)
    elif savings >= 1500:
        return [60, 179, 113, 200]   # Medium Green
    elif savings > 0:
        return [32, 178, 170, 200]   # Light Teal
    else:
        return [128, 128, 128, 150]  # Grey (No Savings)

filtered_df['color'] = filtered_df['total_discount'].apply(get_color)

# B. Radius Logic
filtered_df['radius'] = filtered_df['total_discount'].apply(lambda x: 25 + (x / 15))

# C. Layers
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
    radius_max_pixels=50,
)

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

# D. Auto-Centering
if not filtered_df.empty:
    mid_lat = filtered_df['lat'].median()
    mid_lon = filtered_df['lon'].median()
    
    lat_spread = filtered_df['lat'].max() - filtered_df['lat'].min()
    lon_spread = filtered_df['lon'].max() - filtered_df['lon'].min()
    max_spread = max(lat_spread, lon_spread)

    if max_spread < 0.05: zoom_level = 13
    elif max_spread < 0.2: zoom_level = 11
    else: zoom_level = 9
else:
    mid_lat, mid_lon, zoom_level = 37.3688, -122.0363, 11

view_state = pdk.ViewState(
    latitude=mid_lat,
    longitude=mid_lon,
    zoom=zoom_level,
    pitch=0,
)

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

# --- 8. RENDER MAP ---
st.pydeck_chart(pdk.Deck(
    map_style=pdk.map_styles.CARTO_LIGHT,
    initial_view_state=view_state,
    layers=[scatter_layer, text_layer],
    tooltip=tooltip
))

# --- 9. DISCLAIMER (Methodology) ---
st.info(
    "ℹ️ **Methodology Note:** Average premiums are estimates derived from FAIR Plan filings for these zip codes. "
    "Savings potential is based on 'Quick Assessment' hydration of Construction Era and Roof Type "
    "(sourced via Vexcel + Redfin). PropertyLens data was not used for this specific demo."
)

# --- 10. DETAILED DATA TABLE ---
st.markdown("### 📋 Property Savings Details")

display_cols = ['address', 'url', 'Discount_Commentary', 'average_prem', 'total_discount']

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