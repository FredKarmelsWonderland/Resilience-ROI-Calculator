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
        if st.session_state["password"] == "Faura2026": 
            st.session_state["password_correct"] = True
            del st.session_state["password"]  
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔒 Please enter the Faura access code:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 Please enter the Faura access code:", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- 2. DATA LOADING (GOOGLE SHEETS) ---
@st.cache_data(ttl=60)
def load_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Read the 'Scored' tab specifically
        # PASTE YOUR FULL GOOGLE SHEET URL BELOW
        df = conn.read(
            spreadsheet="https://docs.google.com/spreadsheets/d/1Ank5NAk3qCuYKVK7F580aRU5I2DPDJ6lxLSa66PF33o/edit?gid=696390753#gid=696390753", 
            worksheet="Scored"
        )
        
        # Cleanup
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
pilot_size = st.sidebar.slider(
    "Target Pilot Size", 
    min_value=50, 
    max_value=len(df), 
    value=100, 
    step=25
)
st.sidebar.markdown("---")
st.sidebar.info("Analyzing the 'Screened' portfolio to identify profitability drags.")

# --- MAIN DASHBOARD ---
st.title("📊 Portfolio Screening & Pilot Selection")
st.markdown("### Identifying the 'Bleeding Edge' of the Portfolio")

# --- 3. GLOBAL METRICS ---
total_homes = len(df)
total_tiv = df["TIV"].sum()
total_gross_loss = df["gross_expected_loss"].sum()
total_net = df["carrier_net"].sum()
avg_score = df["scaled_QA_wildfire_score"].mean()

def fmt_currency(x):
    return f"${x/1_000_000:.1f}M" if abs(x) >= 1_000_000 else f"${x/1_000:.0f}K"

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Portfolio Value", fmt_currency(total_tiv), f"{total_homes} Homes")
col2.metric("Gross Expected Loss", fmt_currency(total_gross_loss))
col3.metric("Current Portfolio Net", fmt_currency(total_net), delta_color="normal")
col4.metric("Avg Resilience Score", f"{avg_score:.1f}/100", delta="Target: >75", delta_color="off")

st.markdown("---")

# --- 4. VISUAL ANALYTICS ---
t1, t2 = st.tabs(["📉 Profitability & Risk Profile", "🏠 Property Attributes"])

with t1:
    st.subheader("Financial Impact Analysis")
    c1, c2 = st.columns(2)
    with c1:
        # 1. Net Profit Histogram
        fig_net = px.histogram(df, x="carrier_net", nbins=50, title="Net Profit/Loss Distribution", color_discrete_sequence=["#636EFA"])
        fig_net.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="Breakeven")
        fig_net.update_layout(xaxis_title="Net Profit ($)", yaxis_title="Count")
        st.plotly_chart(fig_net, use_container_width=True)

    with c2:
        # 2. Gross Expected Loss Histogram
        fig_gross = px.histogram(df, x="gross_expected_loss", nbins=50, title="Gross Expected Loss Distribution", color_discrete_sequence=["#EF553B"])
        fig_gross.update_layout(xaxis_title="Gross Loss ($)", yaxis_title="Count")
        st.plotly_chart(fig_gross, use_container_width=True)

    st.markdown("---")
    st.subheader("Risk Metrics Distribution")

    c3, c4 = st.columns(2)
    with c3:
        # 3. Scaled Resilience Score
        fig_score = px.histogram(df, x="scaled_QA_wildfire_score", nbins=20, title="Scaled Resilience Score (0-100)", color_discrete_sequence=["#00CC96"])
        fig_score.add_vline(x=75, line_dash="dot", line_color="black", annotation_text="Target")
        fig_score.update_layout(xaxis_title="Score", yaxis_title="Count")
        st.plotly_chart(fig_score, use_container_width=True)

    with c4:
        # 4. Wildfire Grade (A-F)
        # We manually order these so they appear logically: A -> F
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

with t2:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.subheader("P(Ignition)")
        fig_ign = px.histogram(df, x="P_Ignition", title="Ignition Probability", nbins=20, color_discrete_sequence=["orange"])
        st.plotly_chart(fig_ign, use_container_width=True)
    with c2:
        st.subheader("Year Built")
        fig_year = px.histogram(df, x="Primary_Year_Built_PL", title="Construction Year", nbins=30, color_discrete_sequence=["teal"])
        st.plotly_chart(fig_year, use_container_width=True)
    with c3:
        st.subheader("Wildfire Probability")
        fig_prob = px.histogram(df, x="Wildfire_Annual_Probability_PL", title="Hazard Probability (PL)", nbins=30, color_discrete_sequence=["firebrick"])
        st.plotly_chart(fig_prob, use_container_width=True)

# --- 5. PILOT SELECTION ---
df_sorted = df.sort_values("carrier_net", ascending=True).reset_index(drop=True)
pilot_df = df_sorted.head(pilot_size)
pilot_loss = pilot_df["gross_expected_loss"].sum()
loss_ratio_captured = (pilot_loss / total_gross_loss) * 100

st.markdown("---")
st.header(f"🎯 The Target Pilot: Top {pilot_size} Riskiest Homes")
st.info(f"These {pilot_size} homes represent **{(pilot_size/total_homes)*100:.1f}%** of the portfolio but account for **{loss_ratio_captured:.1f}%** of expected losses.")

# --- 6. DATA TABLES ---
column_config = {
    "carrier_net": st.column_config.NumberColumn("Net Profit/Loss", format="$%d"),
    "gross_expected_loss": st.column_config.NumberColumn("Gross Loss", format="$%d"),
    "Annual_Premium": st.column_config.NumberColumn("Premium", format="$%d"),
    "scaled_QA_wildfire_score": st.column_config.ProgressColumn("QA Score", format="%.0f", min_value=0, max_value=100),
    "P_Ignition": st.column_config.NumberColumn("P(Ignition)", format="%.2f")
}

# Adjusted to match your exact columns
show_cols = [
    "Policy_ID", "address", "city", "carrier_net", "gross_expected_loss", 
    "Annual_Premium", "scaled_QA_wildfire_score", "P_Ignition", 
    "Wildfire_Annual_Probability_PL", "Construction Era"
]

st.subheader(f"📋 Pilot List ({pilot_size} Addresses)")
st.dataframe(pilot_df[show_cols], use_container_width=True, column_config=column_config, hide_index=True)

csv_pilot = pilot_df.to_csv(index=False).encode('utf-8')
st.download_button(label=f"📥 Download Pilot List", data=csv_pilot, file_name=f"Faura_Pilot_{pilot_size}.csv", mime="text/csv")

with st.expander("📂 View Full Portfolio"):
    st.dataframe(df_sorted[show_cols], use_container_width=True, column_config=column_config, hide_index=True)