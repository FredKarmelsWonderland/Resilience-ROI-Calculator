import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Faura Portfolio Analytics", layout="wide")

# --- 1. SECURITY BLOCK ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "Faura2026": # <--- SET YOUR PASSWORD HERE
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input
        st.text_input(
            "🔒 Please enter the Faura access code:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    elif not st.session_state["password_correct"]:
        # Password incorrect, show input again + error
        st.text_input(
            "🔒 Please enter the Faura access code:", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
        return True

if not check_password():
    st.stop()  # Stop execution if password not correct

# --- 2. DATA LOADING (GOOGLE SHEETS) ---
@st.cache_data(ttl=60) # Refreshes cache every 60 seconds
def load_data():
    try:
        # Create the connection object
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Read the specific Worksheet
        df = conn.read(
            spreadsheet="Fake Campaign Demo 2-3-26",
            usecols=list(range(30)) # Safely grab the first ~30 columns to avoid empty trailing cols
        )
        
        # Basic cleanup: Drop rows where Policy_ID is missing (empty rows)
        df = df.dropna(subset=["Policy_ID"])
        return df
        
    except Exception as e:
        st.error(f"❌ Could not connect to Google Sheet. Error: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("⚠️ No data found. Please check your Google Sheet connection.")
    st.stop()

# --- SIDEBAR: PILOT CONTROLS ---
st.sidebar.header("🎯 Pilot Configuration")

# The crucial slider: How many homes does the carrier want to pay for?
pilot_size = st.sidebar.slider(
    "Target Pilot Size (Number of Homes)", 
    min_value=50, 
    max_value=len(df), 
    value=100, 
    step=25,
    help="Select the top X riskiest properties to include in the pilot."
)

st.sidebar.markdown("---")
st.sidebar.info("This dashboard analyzes the 'Screened' portfolio to identify the specific properties dragging down profitability.")

# --- MAIN DASHBOARD ---
st.title("📊 Portfolio Screening & Pilot Selection")
st.markdown("### Identifying the 'Bleeding Edge' of the Portfolio")

# --- 3. GLOBAL METRICS (The "Before" Picture) ---
total_homes = len(df)
total_tiv = df["TIV"].sum()
total_gross_loss = df["gross_expected_loss"].sum()
total_net = df["carrier_net"].sum()
avg_score = df["scaled_QA_wildfire_score"].mean()

# Formatting helper
def fmt_currency(x):
    return f"${x/1_000_000:.1f}M" if abs(x) >= 1_000_000 else f"${x/1_000:.0f}K"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Portfolio Value (TIV)", fmt_currency(total_tiv), f"{total_homes} Homes")
col2.metric("Gross Expected Loss", fmt_currency(total_gross_loss), help="Total projected wildfire losses this year.")
col3.metric("Current Portfolio Net", fmt_currency(total_net), delta_color="normal", help="Premium - Gross Expected Loss")
col4.metric("Avg Resilience Score", f"{avg_score:.1f}/100", delta="Target: >75", delta_color="off")

st.markdown("---")

# --- 4. VISUAL ANALYTICS ---
t1, t2 = st.tabs(["📉 Profitability Distribution", "🔥 Risk Factors Analysis"])

with t1:
    c1, c2 = st.columns([2, 1])
    with c1:
        # Histogram of Carrier Net (The "Bleeding Edge")
        fig_hist = px.histogram(
            df, 
            x="carrier_net", 
            nbins=50,
            title="Distribution of Net Profit/Loss per Home",
            color_discrete_sequence=["#636EFA"]
        )
        # Add a line for Breakeven
        fig_hist.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Breakeven")
        fig_hist.update_layout(xaxis_title="Net Profit ($)", yaxis_title="Count of Homes")
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with c2:
        # Scatter: QA Score vs Net Profit
        fig_scat = px.scatter(
            df,
            x="scaled_QA_wildfire_score",
            y="carrier_net",
            color="Wildfire_Risk_Rating_PL",
            title="Resilience Score vs. Profitability",
            hover_data=["Policy_ID", "city"],
            color_discrete_map={"Low": "green", "Moderate": "yellow", "High": "orange", "Very High": "red"}
        )
        st.plotly_chart(fig_scat, use_container_width=True)

with t2:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("P(Ignition)")
        fig_ign = px.histogram(df, x="P_Ignition", title="Ignition Probability Distribution", nbins=20, color_discrete_sequence=["orange"])
        st.plotly_chart(fig_ign, use_container_width=True)
    with c2:
        st.subheader("Year Built")
        # Ensure column matches your CSV exactly
        fig_year = px.histogram(df, x="characteristics_building_year_built", title="Construction Year", nbins=30, color_discrete_sequence=["teal"])
        st.plotly_chart(fig_year, use_container_width=True)
    with c3:
        st.subheader("Wildfire Probability")
        fig_prob = px.histogram(df, x="Wildfire_Annual_Probability_PL", title="Hazard Probability (PL)", nbins=30, color_discrete_sequence=["firebrick"])
        st.plotly_chart(fig_prob, use_container_width=True)

# --- 5. PILOT SELECTION LOGIC ---
# Sort by Carrier Net (Ascending) -> The biggest losers are at the top
df_sorted = df.sort_values("carrier_net", ascending=True).reset_index(drop=True)

# Slice the Pilot
pilot_df = df_sorted.head(pilot_size)

# Calculate Pilot Impact
pilot_loss = pilot_df["gross_expected_loss"].sum()
pilot_net = pilot_df["carrier_net"].sum()
loss_ratio_captured = (pilot_loss / total_gross_loss) * 100

st.markdown("---")
st.header(f"🎯 The Target Pilot: Top {pilot_size} Riskiest Homes")

st.info(f"""
**Why these {pilot_size} homes?**
Although they represent only **{(pilot_size/total_homes)*100:.1f}%** of the addresses, they account for **{loss_ratio_captured:.1f}%** of your total expected losses.
Targeting this group yields the highest ROI.
""")

# --- 6. DATA TABLES ---

# Configuration for color coding columns
column_config = {
    "carrier_net": st.column_config.NumberColumn(
        "Net Profit/Loss",
        format="$%d",
        help="Annual Premium - Gross Expected Loss"
    ),
    "gross_expected_loss": st.column_config.NumberColumn(
        "Gross Loss",
        format="$%d"
    ),
    "Annual_Premium": st.column_config.NumberColumn(
        "Premium",
        format="$%d"
    ),
    "scaled_QA_wildfire_score": st.column_config.ProgressColumn(
        "QA Score",
        format="%.0f",
        min_value=0,
        max_value=100,
    ),
    "P_Ignition": st.column_config.NumberColumn(
        "P(Ignition)",
        format="%.2f"
    )
}

# Display Columns (Adjust these names to match your CSV headers exactly if they differ)
show_cols = [
    "Policy_ID", "address", "city", "carrier_net", "gross_expected_loss", 
    "Annual_Premium", "scaled_QA_wildfire_score", "P_Ignition", 
    "Wildfire_Annual_Probability_PL", "Construction Era"
]

st.subheader(f"📋 Pilot List ({pilot_size} Addresses)")
st.dataframe(
    pilot_df[show_cols],
    use_container_width=True,
    column_config=column_config,
    height=400,
    hide_index=True
)

# Download Button
csv_pilot = pilot_df.to_csv(index=False).encode('utf-8')
st.download_button(
    label=f"📥 Download Pilot List ({pilot_size} rows)",
    data=csv_pilot,
    file_name=f"Faura_Pilot_Target_List_{pilot_size}.csv",
    mime="text/csv"
)

# Expandable Full Table
with st.expander("📂 View Full Portfolio (All 1000 Homes)"):
    st.dataframe(
        df_sorted[show_cols],
        use_container_width=True,
        column_config=column_config,
        hide_index=True
    )