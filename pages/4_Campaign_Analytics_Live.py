import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Campaign Operations", layout="wide")

# --- 1. DATA LOADING ---
@st.cache_data(ttl=60)
def load_campaign_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # FIX 1: UPDATED WORKSHEET NAME TO "Campaign"
        # PASTE YOUR FULL GOOGLE SHEET URL BELOW
        df = conn.read(
            spreadsheet="https://docs.google.com/spreadsheets/d/1Ank5NAk3qCuYKVK7F580aRU5I2DPDJ6lxLSa66PF33o/edit?gid=1749003768#gid=1749003768",
            worksheet="Campaign" 
        )
        return df
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return pd.DataFrame()

raw_df = load_campaign_data()

if raw_df.empty:
    st.warning("⚠️ No data found. Check your Google Sheet connection.")
    st.stop()

# --- FILTERING LOGIC ---
# We do this OUTSIDE the cache function to debug easily
df = raw_df.copy()

# FIX 2: ROBUST STRING CLEANING
# We strip whitespace and upper-case everything to catch "True ", "true", "TRUE"
if "Campaign_Active" in df.columns:
    # 1. Convert to string
    # 2. Strip whitespace (common copy-paste error)
    # 3. Upper case
    # 4. Check if it equals "TRUE"
    df = df[df["Campaign_Active"].astype(str).str.strip().str.upper() == "TRUE"]
else:
    st.error("❌ Column 'Campaign_Active' not found in Google Sheet.")
    st.stop()

# --- DEBUG BLOCK (Use this to solve the "1000 rows" mystery) ---
# Un-comment the line below if you still see issues
# st.write(f"Raw Rows: {len(raw_df)} | Filtered Rows: {len(df)}")

if df.empty:
    st.warning("⚠️ Data loaded, but 0 rows matched 'Campaign_Active = TRUE'.")
    st.write("First 5 rows of raw data for inspection:")
    st.write(raw_df.head())
    st.stop()

# --- 2. METRIC CALCULATIONS ---
def count_true(column_name):
    if column_name not in df.columns: return 0
    # Robust check for "TRUE" strings
    return df[df[column_name].astype(str).str.strip().str.upper() == "TRUE"].shape[0]

# FIX 3: CRASH PROOF MATH
def safe_calc(numerator, denominator):
    if denominator == 0:
        return 0
    return (numerator / denominator) * 100

total_sent = len(df) # This should now be 100
opened = count_true("Opened Email")
unsubscribed = count_true("Unsubscribed")
lite_completed = count_true("Finished Lite PSA form")
photos_submitted = count_true("Submitted any photos")

mitigation_cols = [c for c in df.columns if c.startswith("Mitigated_")]
if mitigation_cols:
    mitigated_count = df[mitigation_cols].apply(lambda x: x.isin(["Verified"]).any(), axis=1).sum()
else:
    mitigated_count = 0

# --- 3. HEADER METRICS ---
st.title("📢 Campaign Operations Center")
st.markdown("### Engagement & Conversion Tracking")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Emails Sent", total_sent)
c2.metric("Open Rate", f"{safe_calc(opened, total_sent):.0f}%", f"{opened} Opens")
c3.metric("Lite Form Rate", f"{safe_calc(lite_completed, opened):.0f}%", f"{lite_completed} Responses", help="% of Openers")
c4.metric("Photo Conversion", f"{safe_calc(photos_submitted, lite_completed):.0f}%", f"{photos_submitted} Verified", help="% of Forms with Photos")
c5.metric("Value-Add Fixes", mitigated_count, delta="Verified", help="Homes that fixed a specific issue")

st.markdown("---")

# --- 4. THE FUNNEL CHART ---
col_funnel, col_details = st.columns([2, 1])

with col_funnel:
    st.subheader("📉 Campaign Conversion Funnel")
    
    stages = ["Emails Sent", "Opened Email", "Completed Lite Form", "Submitted Photos", "Verified Value-Add"]
    values = [total_sent, opened, lite_completed, photos_submitted, mitigated_count]
    
    fig_funnel = go.Figure(go.Funnel(
        y = stages,
        x = values,
        textinfo = "value+percent initial",
        marker = {"color": ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A"]}
    ))
    fig_funnel.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=400)
    st.plotly_chart(fig_funnel, use_container_width=True)

with col_details:
    st.subheader("❌ Negative Feedback")
    st.metric("Unsubscribes", unsubscribed, f"{safe_calc(unsubscribed, total_sent):.1f}% of total")
    
    st.markdown("#### Top Verified Fixes")
    # Count verified mitigations
    mitigation_counts = df[mitigation_cols].apply(pd.Series.value_counts).T
    if "Verified" in mitigation_counts.columns:
        mitigation_counts = mitigation_counts["Verified"].sort_values(ascending=True)
        mitigation_counts.index = [x.replace("Mitigated_", "") for x in mitigation_counts.index]
        
        fig_bar = px.bar(mitigation_counts, orientation='h', title="Verified Fixes")
        fig_bar.update_layout(showlegend=False, xaxis_title="Count", yaxis_title="Feature")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No verified mitigations yet.")

# --- 5. DETAILED BREAKDOWNS (Tabs) ---
st.markdown("---")
st.subheader("🔍 Response Analysis")

t1, t2 = st.tabs(["📝 Lite Form Answers", "📸 Photo Verification"])

with t1:
    lite_cols = [c for c in df.columns if c.startswith("Lite_")]
    if lite_cols:
        melted_lite = df[lite_cols].melt(var_name="Question", value_name="Response")
        # Filter blanks
        melted_lite = melted_lite[melted_lite["Response"].astype(str).str.strip() != ""]
        melted_lite["Question"] = melted_lite["Question"].str.replace("Lite_", "")
        
        if not melted_lite.empty:
            fig_lite = px.histogram(melted_lite, x="Question", color="Response", barmode="group",
                                    color_discrete_map={"Yes": "#00CC96", "No": "#EF553B", "Unsure": "#FFA15A"})
            st.plotly_chart(fig_lite, use_container_width=True)
        else:
            st.info("No Lite Form responses yet.")

with t2:
    photo_cols = [c for c in df.columns if c.startswith("Photo_")]
    if photo_cols:
        melted_photo = df[photo_cols].melt(var_name="Feature", value_name="Status")
        # Filter blanks
        melted_photo = melted_photo[melted_photo["Status"].astype(str).str.strip() != ""]
        melted_photo["Feature"] = melted_photo["Feature"].str.replace("Photo_", "")
        
        if not melted_photo.empty:
            fig_photo = px.histogram(melted_photo, y="Feature", color="Status", barmode="stack", orientation="h",
                color_discrete_map={"Verified Class A": "green", "Verified Mesh": "green", "Verified Metal": "green", 
                                    "Verified Enclosed": "green", "Verified Dual Pane": "green", "Verified Clearance": "green", 
                                    "Verified Clear": "green", "Verified Gate": "green", "Verified Trimmed": "green", 
                                    "Verified Distant": "green", "Non-Compliant": "red", "Unclear": "orange"})
            st.plotly_chart(fig_photo, use_container_width=True)
        else:
            st.info("No Photo submissions yet.")

# --- 6. RAW DATA ---
with st.expander("📂 View Active Campaign Data"):
    st.dataframe(df)