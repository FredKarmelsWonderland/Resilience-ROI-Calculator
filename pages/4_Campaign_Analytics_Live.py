import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Campaign Operations", layout="wide")

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

# --- 2. DATA LOADING ---
@st.cache_data(ttl=0) 
def load_campaign_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Load Data
        df = conn.read(
            spreadsheet="https://docs.google.com/spreadsheets/d/1Ank5NAk3qCuYKVK7F580aRU5I2DPDJ6lxLSa66PF33o/edit?gid=1749003768#gid=1749003768",
            worksheet="Campaign" 
        )
        
        # Cleanup Headers: Force string and strip
        df.columns = df.columns.astype(str).str.strip()
        
        return df
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return pd.DataFrame()

raw_df = load_campaign_data()

if raw_df.empty:
    st.warning("⚠️ No data found.")
    st.stop()

# --- 3. FILTERING ACTIVE CAMPAIGN ---
df = raw_df.copy()

# Robust Filter: Use .str.contains for safety
if "Campaign_Active" in df.columns:
    # This checks for "true" inside the cell, ignoring case (TRUE/True/true)
    # na=False means empty cells are treated as False
    df = df[df["Campaign_Active"].astype(str).str.contains("true", case=False, na=False)]
else:
    st.error("❌ Column 'Campaign_Active' not found.")
    st.stop()

if df.empty:
    st.warning("⚠️ Data loaded, but no rows matched 'Campaign_Active = TRUE'.")
    st.write("Debug: First 5 rows of raw data:")
    st.dataframe(raw_df.head())
    st.stop()

# --- 4. THE NUCLEAR COUNTING FUNCTION ---
def count_true(column_name):
    """
    Counts rows where the column contains 'true', '1', or 'yes' (Case Insensitive).
    This handles Booleans, Strings, and mixed formats.
    """
    if column_name not in df.columns: 
        return 0
    
    # Convert to string and use regex search for truthy values
    # Looks for "true" OR "1" OR "yes"
    return df[column_name].astype(str).str.contains("true|1|yes", case=False, na=False).sum()

def safe_calc(numerator, denominator):
    if denominator == 0: return 0
    return (numerator / denominator) * 100

# --- 5. CALCULATE METRICS ---
total_sent = len(df) # Should be ~100
opened = count_true("Opened Email")
unsubscribed = count_true("Unsubscribed")
lite_completed = count_true("Finished Lite PSA form")
photos_submitted = count_true("Submitted any photos")

# Verified Mitigations Logic
mitigation_cols = [c for c in df.columns if c.startswith("Mitigated_")]
if mitigation_cols:
    # Check if any column contains "verified" (case insensitive)
    mit_df = df[mitigation_cols].astype(str).apply(lambda x: x.str.contains("verified", case=False, na=False))
    mitigated_count = mit_df.any(axis=1).sum()
else:
    mitigated_count = 0

# --- 6. DEBUG EXPANDER ---
# Check this to prove the data is loaded correctly
with st.expander("🛠 Data Verification (Check this first)"):
    st.write(f"**Total Active Rows:** {len(df)}")
    st.write(f"**Calculated Opens:** {opened}")
    st.write("Preview of Active Data:")
    st.dataframe(df.head(5))

# --- 7. DASHBOARD UI ---
st.title("📢 Campaign Operations Center")
st.markdown("### Engagement & Conversion Tracking")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Emails Sent", total_sent)
c2.metric("Open Rate", f"{safe_calc(opened, total_sent):.0f}%", f"{opened} Opens")
c3.metric("Lite Form Rate", f"{safe_calc(lite_completed, opened):.0f}%", f"{lite_completed} Responses", help="% of Openers")
c4.metric("Photo Conversion", f"{safe_calc(photos_submitted, lite_completed):.0f}%", f"{photos_submitted} Verified", help="% of Forms with Photos")
c5.metric("Value-Add Fixes", mitigated_count, delta="Verified", help="Homes that fixed a specific issue")

st.markdown("---")

# --- 8. FUNNEL & DETAILS ---
col_funnel, col_details = st.columns([2, 1])

with col_funnel:
    st.subheader("📉 Campaign Conversion Funnel")
    stages = ["Emails Sent", "Opened Email", "Completed Lite Form", "Submitted Photos", "Verified Value-Add"]
    values = [total_sent, opened, lite_completed, photos_submitted, mitigated_count]
    
    fig_funnel = go.Figure(go.Funnel(
        y = stages, x = values, textinfo = "value+percent initial",
        marker = {"color": ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A"]}
    ))
    fig_funnel.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=400)
    st.plotly_chart(fig_funnel, use_container_width=True)

with col_details:
    st.subheader("❌ Negative Feedback")
    st.metric("Unsubscribes", unsubscribed, f"{safe_calc(unsubscribed, total_sent):.1f}% of total")
    
    st.markdown("#### Top Verified Fixes")
    if mitigation_cols:
        # Count Verified across all columns using the same loose logic
        mit_counts = df[mitigation_cols].astype(str).apply(lambda x: x.str.contains("verified", case=False, na=False).sum())
        mit_counts = mit_counts[mit_counts > 0].sort_values(ascending=True)
        
        if not mit_counts.empty:
            mit_counts.index = [x.replace("Mitigated_", "").replace("_", " ") for x in mit_counts.index]
            fig_bar = px.bar(x=mit_counts.values, y=mit_counts.index, orientation='h', title="Verified Fixes")
            fig_bar.update_layout(showlegend=False, xaxis_title="Count", yaxis_title="Feature")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No verified mitigations found.")

# --- 9. TABS ---
st.markdown("---")
st.subheader("🔍 Response Analysis")
t1, t2 = st.tabs(["📝 Lite Form Answers", "📸 Photo Verification"])

with t1:
    lite_cols = [c for c in df.columns if c.startswith("Lite_")]
    if lite_cols:
        melted = df[lite_cols].melt(var_name="Question", value_name="Response")
        # Filter Blanks: Check if string length > 0 after strip
        melted = melted[melted["Response"].astype(str).str.strip().str.len() > 0]
        # Filter out "nan" strings from empty cells
        melted = melted[~melted["Response"].astype(str).str.lower().isin(["nan", "none"])]
        
        if not melted.empty:
            melted["Question"] = melted["Question"].str.replace("Lite_", "")
            fig = px.histogram(melted, x="Question", color="Response", barmode="group",
                               color_discrete_map={"Yes": "#00CC96", "No": "#EF553B", "Unsure": "#FFA15A"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No Lite Form data available yet.")

with t2:
    photo_cols = [c for c in df.columns if c.startswith("Photo_")]
    if photo_cols:
        melted = df[photo_cols].melt(var_name="Feature", value_name="Status")
        melted = melted[melted["Status"].astype(str).str.strip().str.len() > 0]
        melted = melted[~melted["Status"].astype(str).str.lower().isin(["nan", "none"])]
        
        if not melted.empty:
            melted["Feature"] = melted["Feature"].str.replace("Photo_", "")
            fig = px.histogram(melted, y="Feature", color="Status", barmode="stack", orientation="h")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No Photo data available yet.")