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
        df = conn.read(
            spreadsheet="https://docs.google.com/spreadsheets/d/1Ank5NAk3qCuYKVK7F580aRU5I2DPDJ6lxLSa66PF33o/edit?gid=1749003768#gid=1749003768",
            worksheet="Campaign" 
        )
        df.columns = df.columns.astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return pd.DataFrame()

raw_df = load_campaign_data()

if raw_df.empty:
    st.warning("⚠️ No data found.")
    st.stop()

# --- 3. FILTERING ---
df = raw_df.copy()
if "Campaign_Active" in df.columns:
    df = df[df["Campaign_Active"].astype(str).str.contains("true", case=False, na=False)]
else:
    st.error("❌ Column 'Campaign_Active' not found.")
    st.stop()

if df.empty:
    st.warning("⚠️ Data loaded, but no active campaign rows found.")
    st.stop()

# --- 4. HELPER FUNCTIONS ---
def count_true(column_name):
    if column_name not in df.columns: return 0
    return df[column_name].astype(str).str.contains("true|1|yes", case=False, na=False).sum()

def safe_calc(numerator, denominator):
    if denominator == 0: return 0
    return (numerator / denominator) * 100

# --- 5. METRICS ---
total_sent = len(df)
opened = count_true("Opened Email")
unsubscribed = count_true("Unsubscribed")
lite_completed = count_true("Finished Lite PSA form")
photos_submitted = count_true("Submitted any photos")

# Mitigation Counts
mitigation_cols = [c for c in df.columns if c.startswith("Mitigated_")]
if mitigation_cols:
    mit_df = df[mitigation_cols].astype(str).apply(lambda x: x.str.contains("verified", case=False, na=False))
    mitigated_count = mit_df.any(axis=1).sum()
else:
    mitigated_count = 0

# --- 6. TOP DASHBOARD ---
st.title("📢 Campaign Operations Center")
st.markdown("### Engagement & Conversion Tracking")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Emails Sent", total_sent)
c2.metric("Open Rate", f"{safe_calc(opened, total_sent):.0f}%", f"{opened} Opens")
c3.metric("Lite Form Rate", f"{safe_calc(lite_completed, opened):.0f}%", f"{lite_completed} Responses", help="% of Openers")
c4.metric("Photo Conversion", f"{safe_calc(photos_submitted, lite_completed):.0f}%", f"{photos_submitted} Verified", help="% of Forms with Photos")
c5.metric("Value-Add Fixes", mitigated_count, delta="Verified", help="Homes that fixed a specific issue")

st.markdown("---")

# --- 7. FUNNEL & DETAILS ---
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
        mit_counts = df[mitigation_cols].astype(str).apply(lambda x: x.str.contains("verified", case=False, na=False).sum())
        mit_counts = mit_counts[mit_counts > 0].sort_values(ascending=True)
        if not mit_counts.empty:
            mit_counts.index = [x.replace("Mitigated_", "").replace("_", " ") for x in mit_counts.index]
            fig_bar = px.bar(x=mit_counts.values, y=mit_counts.index, orientation='h', title="Verified Fixes")
            fig_bar.update_layout(showlegend=False, xaxis_title="Count", yaxis_title="Feature")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No verified mitigations found.")

# --- 8. DETAILED RESPONSE GRIDS (The New Part) ---
st.markdown("---")
st.subheader("🔍 Response Breakdown")

t1, t2 = st.tabs(["📝 Lite Form Breakdown", "📸 Photo Verification Status"])

# COLOR MAPPING FOR CONSISTENCY
color_map_lite = {"Yes": "#00CC96", "No": "#EF553B", "Unsure": "#FFA15A", "No Gutters": "lightgray", "No Trees": "lightgray", "No Deck": "lightgray"}

with t1:
    st.info("Self-reported answers from the Lite PSA Form.")
    
    # Get all Lite columns
    lite_cols = [c for c in df.columns if c.startswith("Lite_")]
    
    if lite_cols:
        # Create a grid of columns (3 per row)
        cols = st.columns(3)
        
        for i, col_name in enumerate(lite_cols):
            # Clean up the name for the title
            feature_name = col_name.replace("Lite_", "").replace("_", " ")
            
            # Prepare data: filter out blanks/nans
            clean_series = df[col_name].astype(str).str.strip()
            clean_series = clean_series[clean_series.str.len() > 0]
            clean_series = clean_series[~clean_series.str.lower().isin(["nan", "none"])]
            
            if not clean_series.empty:
                counts = clean_series.value_counts().reset_index()
                counts.columns = ["Answer", "Count"]
                
                # Create a Donut Chart for each feature
                fig = px.pie(
                    counts, 
                    names="Answer", 
                    values="Count", 
                    title=f"<b>{feature_name}</b>",
                    color="Answer",
                    color_discrete_map=color_map_lite,
                    hole=0.4
                )
                fig.update_layout(showlegend=True, margin=dict(t=30, b=0, l=0, r=0), height=250)
                
                # Place in the grid (modulo 3 arithmetic)
                with cols[i % 3]:
                    st.plotly_chart(fig, use_container_width=True)
            else:
                pass # Skip empty columns
    else:
        st.info("No Lite Form columns found.")

with t2:
    st.info("Verification results based on submitted photos.")
    
    photo_cols = [c for c in df.columns if c.startswith("Photo_")]
    
    if photo_cols:
        cols = st.columns(3)
        for i, col_name in enumerate(photo_cols):
            feature_name = col_name.replace("Photo_", "").replace("_", " ")
            
            clean_series = df[col_name].astype(str).str.strip()
            clean_series = clean_series[clean_series.str.len() > 0]
            clean_series = clean_series[~clean_series.str.lower().isin(["nan", "none"])]
            
            if not clean_series.empty:
                counts = clean_series.value_counts().reset_index()
                counts.columns = ["Status", "Count"]
                
                # Dynamic coloring for Photo status
                fig = px.pie(
                    counts, 
                    names="Status", 
                    values="Count", 
                    title=f"<b>{feature_name}</b>",
                    hole=0.4
                )
                # We let Plotly pick colors here since statuses are complex strings
                # but we prefer Green/Red/Orange generally
                fig.update_traces(marker=dict(colors=["#00CC96" if "verified" in x.lower() else "#EF553B" if "compliant" in x.lower() else "#FFA15A" for x in counts["Status"]]))
                
                fig.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0), height=250)
                
                with cols[i % 3]:
                    st.plotly_chart(fig, use_container_width=True)