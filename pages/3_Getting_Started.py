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
    st.header("⚙️ Pilot Settings")
    pilot_size = st.number_input("Target Pilot Size (Homes)", min_value=50, value=100, step=10)
    st.markdown("---")
    st.info("Adjusting the pilot size highlights the top-risk homes in the charts below.")

# --- 3. DATA LOADING (DUAL TABS) ---
@st.cache_data(ttl=600)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # 1. Load RAW Input (Client List)
        df_raw = conn.read(
            spreadsheet="https://docs.google.com/spreadsheets/d/1Ank5NAk3qCuYKVK7F580aRU5I2DPDJ6lxLSa66PF33o/edit",
            worksheet="client screening list" 
        )
        
        # 2. Load SCORED Data (Analytics)
        df_scored = conn.read(
            spreadsheet="https://docs.google.com/spreadsheets/d/1Ank5NAk3qCuYKVK7F580aRU5I2DPDJ6lxLSa66PF33o/edit",
            worksheet="Scored" 
        )
        
        # --- CLEANUP SCORED DATA ---
        df_scored = df_scored.dropna(subset=["Policy_ID"])
        
        # Ensure numeric types for all columns used in analytics
        # Note: We exclude "Wildfire_Risk_Grade_PL" because it is categorical (A, B, C...)
        cols_to_clean = [
            "TIV", "Annual_Premium", "gross_expected_loss", "scaled_QA_wildfire_score", 
            "carrier_net", "P_Ignition", "Primary_Year_Built_PL", "Wildfire_Annual_Probability_PL"
        ]
        
        for col in cols_to_clean:
            if col in df_scored.columns:
                # Remove currency symbols ($ ,) and convert to numeric
                df_scored[col] = pd.to_numeric(
                    df_scored[col].astype(str).str.replace(r'[$,]', '', regex=True), 
                    errors='coerce'
                )
        
        return df_raw, df_scored
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

# Load Data
df_raw, df = load_data()

if df.empty:
    st.warning("⚠️ No Scored data found. Check your 'Scored' tab connection.")
    st.stop()

# --- 4. PAGE HEADER & SCREENING COST ---
st.title("🚀 Getting Started with a Campaign")

total_homes_intake = len(df_raw) 
screening_rate = 2 
total_screening_cost = total_homes_intake * screening_rate

st.markdown(f"""
### Step 1: Portfolio Ingestion
**Carrier provides a list of {total_homes_intake:,} homes that we screen at ${screening_rate}/address (Total: ${total_screening_cost:,.0f}), ranking them by underwriting risk.**
""")

# --- 5. CLIENT SCREENING LIST (RAW) ---
with st.expander("📂 View Client Screening List (Raw Intake)", expanded=False):
    st.markdown("This is the raw intake file before prioritization.")
    st.dataframe(df_raw, use_container_width=True)

# --- 6. PORTFOLIO ANALYTICS (SCORED) ---
st.markdown("---")
st.subheader("📊 Step 2. Portfolio Analytics")

# A. Metrics Widgets
c1, c2, c3, c4, c5, c6 = st.columns(6)

total_tiv = df["TIV"].sum()
total_homes = len(df)
total_premium = df["Annual_Premium"].sum()
total_gel = df["gross_expected_loss"].sum()
net_portfolio = df["carrier_net"].sum()
avg_resilience = df["scaled_QA_wildfire_score"].mean()

# Standard Metrics
c1.metric("Total Homes", f"{total_homes:,}")
c2.metric("Total TIV", f"${total_tiv/1e6:,.0f}M")
c3.metric("Total Premium", f"${total_premium/1e6:,.2f}M")
c4.metric("Gross Exp. Loss", f"${total_gel/1e6:,.2f}M")

# CUSTOM COLOR METRIC: EXPECTED NET
if net_portfolio > 0:
    net_color = "#00CC96" # Green
elif net_portfolio < 0:
    net_color = "#EF553B" # Red
else:
    net_color = "inherit"

c5.markdown(f"""
    <div data-testid="stMetricValue">
        <label style="font-size: 14px; color: rgba(49, 51, 63, 0.6);">Expected Net</label>
        <div style="font-size: 32px; font-weight: 600; color: {net_color};">
            ${net_portfolio/1e6:,.2f}M
        </div>
        <div style="font-size: 14px; color: rgba(49, 51, 63, 0.6);">
            Net Profit
        </div>
    </div>
""", unsafe_allow_html=True)

c6.metric("Avg Resilience Score", f"{avg_resilience:.0f}/100")

# B. Visual Analytics (New 3-Tab Layout)
st.markdown("---")
t1, t2, t3 = st.tabs(["📉 Loss Profile", "🏠 Home Profile", "🔥 Risk Profile"])

# TAB 1: LOSS PROFILE (Net Profit + Gross Loss)
with t1:
    c1, c2 = st.columns(2)
    with c1:
        if "carrier_net" in df.columns:
            fig_net = px.histogram(df, x="carrier_net", nbins=50, title="Net Profit/Loss Distribution", color_discrete_sequence=["#636EFA"])
            fig_net.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Breakeven")
            fig_net.update_layout(xaxis_title="Net Profit ($)", yaxis_title="Count")
            st.plotly_chart(fig_net, use_container_width=True)
    with c2:
        if "gross_expected_loss" in df.columns:
            fig_gross = px.histogram(df, x="gross_expected_loss", nbins=50, title="Gross Expected Loss Distribution", color_discrete_sequence=["#EF553B"])
            fig_gross.update_layout(xaxis_title="Gross Loss ($)", yaxis_title="Count")
            st.plotly_chart(fig_gross, use_container_width=True)

# TAB 2: HOME PROFILE (Year Built + Resilience Score)
with t2:
    c1, c2 = st.columns(2)
    with c1:
        if "Primary_Year_Built_PL" in df.columns:
            fig_year = px.histogram(df, x="Primary_Year_Built_PL", title="Construction Year", nbins=30, color_discrete_sequence=["teal"])
            fig_year.update_layout(xaxis_title="Year Built", yaxis_title="Count")
            st.plotly_chart(fig_year, use_container_width=True)
    with c2:
         if "scaled_QA_wildfire_score" in df.columns:
            fig_score = px.histogram(df, x="scaled_QA_wildfire_score", nbins=20, title="Scaled Resilience Score (0-100)", color_discrete_sequence=["#00CC96"])
            fig_score.add_vline(x=75, line_dash="dot", line_color="black", annotation_text="Target")
            fig_score.update_layout(xaxis_title="Score", yaxis_title="Count")
            st.plotly_chart(fig_score, use_container_width=True)

# TAB 3: RISK PROFILE (Probability + Grade)
with t3:
    c1, c2 = st.columns(2)
    with c1:
        if "Wildfire_Annual_Probability_PL" in df.columns:
            fig_prob = px.histogram(df, x="Wildfire_Annual_Probability_PL", title="Annual Wildfire Probability", nbins=30, color_discrete_sequence=["firebrick"])
            fig_prob.update_layout(xaxis_title="Probability (0-1)", yaxis_title="Count")
            st.plotly_chart(fig_prob, use_container_width=True)
    with c2:
        if "Wildfire_Risk_Grade_PL" in df.columns:
            category_order = {"Wildfire_Risk_Grade_PL": ["A", "B", "C", "D", "F"]}
            fig_grade = px.histogram(
                df, 
                x="Wildfire_Risk_Grade_PL", 
                title="Wildfire Risk Grade", 
                color="Wildfire_Risk_Grade_PL",
                category_orders=category_order,
                color_discrete_map={
                    "A": "green", "B": "lightgreen", "C": "yellow", "D": "orange", "F": "red"
                }
            )
            fig_grade.update_layout(xaxis_title="Grade", yaxis_title="Count")
            st.plotly_chart(fig_grade, use_container_width=True)

# C. Full Portfolio Table
with st.expander("📋 View Full Portfolio Metrics", expanded=False):
    show_cols = ["Policy_ID", "address", "city", "TIV", "Annual_Premium", "gross_expected_loss", "scaled_QA_wildfire_score"]
    valid_cols = [c for c in show_cols if c in df.columns]
    
    st.dataframe(df[valid_cols].style.format({
        "TIV": "${:,.0f}", 
        "Annual_Premium": "${:,.0f}", 
        "gross_expected_loss": "${:,.0f}",
        "scaled_QA_wildfire_score": "{:.1f}"
    }), use_container_width=True)

# --- 7. THE TARGET PILOT (UPDATED) ---
st.markdown("---")
st.subheader(f"🎯 Step 3. The Targeted Pilot: Top {pilot_size} Riskiest Homes")

# Sort and Slice
if "gross_expected_loss" in df.columns:
    df_sorted = df.sort_values("gross_expected_loss", ascending=False).reset_index(drop=True)
    top_n = df_sorted.head(pilot_size)

    # Calculate Stats for Widgets
    pct_homes = (pilot_size / total_homes) * 100
    top_n_loss = top_n["gross_expected_loss"].sum()
    pct_loss = (top_n_loss / total_gel) * 100 if total_gel > 0 else 0
    
    # --- PILOT WIDGETS ---
    p1, p2, p3, p4, p5, p6 = st.columns(6)
    
    p_tiv = top_n["TIV"].sum()
    p_prem = top_n["Annual_Premium"].sum()
    p_gel = top_n["gross_expected_loss"].sum()
    p_net = top_n["carrier_net"].sum()
    p_score = top_n["scaled_QA_wildfire_score"].mean()

    p1.metric("Homes to Target", f"{pilot_size}", f"{pct_homes:.1f}% of Port")
    p2.metric("Campaign TIV", f"${p_tiv/1e6:,.0f}M")
    p3.metric("Campaign Premium", f"${p_prem/1e6:,.2f}M")
    p4.metric("Campaign Gross Exp. Loss", f"${p_gel/1e6:,.2f}M", f"{pct_loss:.1f}% of Loss", delta_color="inverse")
    
    # Custom Net Color for Pilot
    if p_net > 0: p_color = "#00CC96" 
    elif p_net < 0: p_color = "#EF553B" 
    else: p_color = "inherit"

    p5.markdown(f"""
    <div data-testid="stMetricValue">
        <label style="font-size: 14px; color: rgba(49, 51, 63, 0.6);">Target Net</label>
        <div style="font-size: 26px; font-weight: 600; color: {p_color};">
            ${p_net/1e6:,.2f}M
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    p6.metric("Avg Resilience Score", f"{p_score:.0f}/100")

    st.markdown("---")
    
    # --- COLLAPSIBLE PILOT TABLE ---
    with st.expander(f"📋 View Target Pilot List ({pilot_size} Homes)", expanded=True):
        valid_cols = [c for c in show_cols if c in top_n.columns]
        st.dataframe(top_n[valid_cols].style.format({
            "TIV": "${:,.0f}", 
            "Annual_Premium": "${:,.0f}", 
            "gross_expected_loss": "${:,.0f}",
            "scaled_QA_wildfire_score": "{:.1f}"
        }), use_container_width=True)

# --- 9. FOOTER ---
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