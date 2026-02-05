import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Getting Started", layout="wide")

# --- 1. SECURITY BLOCK ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False
    
    def password_entered():
        if st.session_state["password"] == "Faura2026": 
            st.session_state["password_correct"] = True
            del st.session_state["password"]  
        else:
            st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.text_input("🔒 Please enter the Faura access code:", type="password", on_change=password_entered, key="password")
        return False
    return True

if not check_password():
    st.stop()

# --- 2. SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.header("⚙️ Campaign Settings")
    # Widget for X homes
    num_homes_input = st.number_input("Total Portfolio Size (Homes)", min_value=100, value=1000, step=50)
    pilot_size = st.number_input("Pilot Target Size", min_value=10, value=100, step=10)
    
    st.markdown("---")
    st.info("Adjusting the portfolio size calculates the estimated screening cost.")

# --- 3. DATA LOADING ---
@st.cache_data(ttl=600)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # REPLACE WITH YOUR GOOGLE SHEET URL
        df = conn.read(
            spreadsheet="https://docs.google.com/spreadsheets/d/1Ank5NAk3qCuYKVK7F580aRU5I2DPDJ6lxLSa66PF33o/edit?gid=0#gid=0",
            worksheet="client screening list" 
        )
        
        # Standardize Columns (Cleanup)
        df.columns = df.columns.str.strip()
        
        # Ensure Numeric Data
        cols_to_numeric = ["TIV", "Annual_Premium", "Expected_Loss_Annual", "Faura_Score"]
        for col in cols_to_numeric:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[$,]', '', regex=True), errors='coerce')
        
        return df
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return pd.DataFrame()

df = load_data()

if df.empty:
    st.warning("⚠️ No data found. Please check your Google Sheet connection.")
    st.stop()

# --- 4. PAGE HEADER & SCREENING COST ---
st.title("🚀 Getting Started with a Campaign")

screening_cost = num_homes_input * 3
st.markdown(f"""
### Step 1: Portfolio Ingestion
**Carrier provides a list of {num_homes_input:,} homes that we screen at $3/address (Total: \${screening_cost:,.0f}), ranking them by underwriting risk.**
""")

# --- 5. CLIENT SCREENING LIST (COLLAPSIBLE) ---
with st.expander("📂 View Client Screening List (Raw Data)", expanded=False):
    st.markdown("This is the raw intake file before prioritization.")
    st.dataframe(df, use_container_width=True)

# --- 6. PORTFOLIO ANALYTICS ---
st.markdown("---")
st.subheader("📊 Portfolio Analytics")

# A. The Widgets
c1, c2, c3, c4, c5, c6 = st.columns(6)

total_tiv = df["TIV"].sum()
total_homes = len(df)
total_premium = df["Annual_Premium"].sum()
total_gel = df["Expected_Loss_Annual"].sum()
net_portfolio = total_premium - total_gel
avg_resilience = df["Faura_Score"].mean()

c1.metric("Total TIV", f"${total_tiv/1e6:,.1f}M")
c2.metric("Total Homes", f"{total_homes:,}")
c3.metric("Total Premium", f"${total_premium:,.0f}")
c4.metric("Gross Exp. Loss", f"${total_gel:,.0f}")
c5.metric("Current Net", f"${net_portfolio:,.0f}", help="Premium - Expected Loss")
c6.metric("Avg Resilience", f"{avg_resilience:.1f}/100")

# B. Full Portfolio Table (Collapsible)
with st.expander("📋 View Full Portfolio Metrics", expanded=False):
    st.dataframe(df.style.format({
        "TIV": "${:,.0f}", 
        "Annual_Premium": "${:,.0f}", 
        "Expected_Loss_Annual": "${:,.0f}",
        "Faura_Score": "{:.1f}"
    }), use_container_width=True)

# C. Histograms
col_hist1, col_hist2 = st.columns(2)

with col_hist1:
    fig_score = px.histogram(df, x="Faura_Score", nbins=20, title="Distribution of Resilience Scores",
                             color_discrete_sequence=["#636EFA"])
    fig_score.update_layout(bargap=0.1, height=300)
    st.plotly_chart(fig_score, use_container_width=True)

with col_hist2:
    # Filter out massive outliers for cleaner visualization if needed
    fig_loss = px.histogram(df, x="Expected_Loss_Annual", nbins=20, title="Distribution of Expected Loss",
                            color_discrete_sequence=["#EF553B"])
    fig_loss.update_layout(bargap=0.1, height=300, xaxis_tickprefix="$")
    st.plotly_chart(fig_loss, use_container_width=True)

# --- 7. THE TARGET PILOT (TOP 100) ---
st.markdown("---")
st.subheader(f"🎯 The Target Pilot: Top {pilot_size} Riskiest Homes")

# Sort by Risk (Expected Loss)
df_sorted = df.sort_values("Expected_Loss_Annual", ascending=False).reset_index(drop=True)
top_n = df_sorted.head(pilot_size)

# Calculate Stats
pct_homes = (pilot_size / total_homes) * 100
top_n_loss = top_n["Expected_Loss_Annual"].sum()
pct_loss = (top_n_loss / total_gel) * 100

st.info(f"These **{pilot_size}** homes represent **{pct_homes:.1f}%** of the portfolio but account for **{pct_loss:.1f}%** of expected losses.")

st.dataframe(top_n.style.format({
    "TIV": "${:,.0f}", 
    "Annual_Premium": "${:,.0f}", 
    "Expected_Loss_Annual": "${:,.0f}",
    "Faura_Score": "{:.1f}"
}), use_container_width=True)

# --- 8. DEEP DIVE: VALUE OF SCREENING ---
st.markdown("---")
st.subheader("📊 Deep Dive: The Value of Data Screening")

# Simulation Logic
# 1. Faura Strategy: Already calculated as `top_n`
res_faura = {
    "Total Risk Targeted": top_n["Expected_Loss_Annual"].sum(),
    "Selection": top_n
}

# 2. Random Strategy: Shuffle and pick top N
np.random.seed(42) # Fixed seed for reproducibility
df_random = df.sample(frac=1).reset_index(drop=True) # Shuffle
random_n = df_random.head(pilot_size)

res_rand = {
    "Total Risk Targeted": random_n["Expected_Loss_Annual"].sum(),
    "Selection": random_n
}

# Metrics
c1, c2, c3, c4 = st.columns(4)
risk_diff = res_faura["Total Risk Targeted"] - res_rand["Total Risk Targeted"]
risk_lift_pct = (risk_diff / res_rand["Total Risk Targeted"]) * 100 if res_rand["Total Risk Targeted"] > 0 else 0

c1.metric("Gross Risk Targeted (Faura)", f"${res_faura['Total Risk Targeted']:,.0f}", delta=f"+{risk_lift_pct:.0f}% vs Random")
c2.metric("Gross Risk Targeted (Random)", f"${res_rand['Total Risk Targeted']:,.0f}", delta="Baseline", delta_color="off")
c3.metric("Risk Intelligence Value", f"${risk_diff:,.0f}", help="The extra risk exposure captured purely by using Faura's sorting algorithm vs random selection.")
c4.metric("Avg Premium (Target Group)", f"${res_faura['Selection']['Annual_Premium'].mean():,.0f}")

# Lift Curve Logic
# Create Ranks for the simulation
df_lift = df.copy()
df_lift["Rank_Risk"] = df_lift["Expected_Loss_Annual"] # Higher loss = Higher rank
df_lift["Rank_Random"] = np.random.rand(len(df_lift)) # Random rank

def get_lift_curve(rank_col, name):
    # Sort by the rank column
    sorted_df = df_lift.sort_values(rank_col, ascending=False).reset_index(drop=True)
    sorted_df["Cum_Risk"] = sorted_df["Expected_Loss_Annual"].cumsum()
    # Calculate % of homes targeted (x-axis)
    sorted_df["% Homes Targeted"] = (sorted_df.index + 1) / len(sorted_df)
    sorted_df["Strategy"] = name
    return sorted_df[["% Homes Targeted", "Cum_Risk", "Strategy"]]

lift_data = pd.concat([
    get_lift_curve("Rank_Risk", "Faura Prioritized"),
    get_lift_curve("Rank_Random", "Random Outreach")
])

fig_lift = px.line(lift_data, x="% Homes Targeted", y="Cum_Risk", color="Strategy",
              color_discrete_map={"Faura Prioritized": "#00CC96", "Random Outreach": "#EF553B"})

# Add Vertical Line for Budget (Pilot Size)
budget_pct = pilot_size / len(df)
fig_lift.add_vline(x=budget_pct, line_dash="dash", line_color="grey", annotation_text="Pilot Budget")

fig_lift.update_layout(
    height=450, 
    xaxis_tickformat=".0%", 
    yaxis_tickprefix="$", 
    yaxis_title="Cumulative Gross Expected Loss ($)",
    title="Cumulative Risk Capture: Faura vs Random"
)
st.plotly_chart(fig_lift, use_container_width=True)

# --- 9. FOOTER: EQUATION DISPLAY ---
st.markdown("---")
st.subheader("🧮 The Logic Behind the Score")
st.markdown(r"""
**The "Vulnerability" Gap:**
$$
\text{Risk} = \text{TIV} \times \underbrace{P(\text{Fire})}_\text{Hazard} \times \underbrace{P(\text{Ignition})}_\text{Vulnerability}
$$
* **Hazard (P_Fire):** Probability of Wildfire.
* **Vulnerability (P_Ignition):** Probability of Ignition if Fire occurs. [Faura uses its Proprietary Quick Assessment score for this].
""")