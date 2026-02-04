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
        
        # Load the Campaign Tab
        # PASTE YOUR FULL GOOGLE SHEET URL BELOW
        df = conn.read(
            spreadsheet="https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit",
            worksheet="Campaign_Tracker" 
        )
        
        # --- ROBUST FILTERING ---
        # 1. Filter to keep only the Active Pilot rows
        if "Campaign_Active" in df.columns:
            # Convert to string and uppercase to handle "TRUE", "True", True, or 1 safely
            df = df[df["Campaign_Active"].astype(str).str.upper() == "TRUE"]
        else:
            # Fallback: drop if "Opened Email" is empty
            df = df[df["Opened Email"].astype(str) != ""]
            
        return df
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return pd.DataFrame()

df = load_campaign_data()

if df.empty:
    st.warning("⚠️ No active campaign data found. Check your 'Campaign_Active' column in Sheets.")
    st.stop()

# --- 2. METRIC CALCULATIONS ---
# Helper to safely count "TRUE" values even if they load as strings
def count_true(column_name):
    if column_name not in df.columns: return 0
    return df[df[column_name].astype(str).str.upper() == "TRUE"].shape[0]

total_sent = len(df) # Since we already filtered for Campaign_Active, this is correct (100)
opened = count_true("Opened Email")
unsubscribed = count_true("Unsubscribed")
lite_completed = count_true("Finished Lite PSA form")
photos_submitted = count_true("Submitted any photos")

# "Verified Mitigated" Logic:
# Count row if AT LEAST ONE "Mitigated_" column == "Verified"
mitigation_cols = [c for c in df.columns if c.startswith("Mitigated_")]
mitigated_count = df[mitigation_cols].apply(lambda x: x.isin(["Verified"]).any(), axis=1).sum()

# --- 3. HEADER METRICS ---
st.title("📢 Campaign Operations Center")
st.markdown("### Engagement & Conversion Tracking")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Emails Sent", total_sent)
c2.metric("Open Rate", f"{(opened/total_sent)*100:.0f}%", f"{opened} Opens")
c3.metric("Lite Form Rate", f"{(lite_completed/opened)*100:.0f}%", f"{lite_completed} Responses", help="% of Openers who finished form")
c4.metric("Photo Conversion", f"{(photos_submitted/lite_completed)*100:.0f}%", f"{photos_submitted} Verified", help="% of Forms that added photos")
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
    st.metric("Unsubscribes", unsubscribed, f"{(unsubscribed/total_sent)*100:.1f}% of total")
    
    st.markdown("#### Top Verified Fixes")
    # Count verified mitigations per category
    # We explicitly exclude empty strings to only count "Verified"
    mitigation_counts = df[mitigation_cols].apply(pd.Series.value_counts).T
    if "Verified" in mitigation_counts.columns:
        mitigation_counts = mitigation_counts["Verified"].sort_values(ascending=True)
        # Clean up names
        mitigation_counts.index = [x.replace("Mitigated_", "") for x in mitigation_counts.index]
        
        fig_bar = px.bar(mitigation_counts, orientation='h', title="Verified Fixes by Category")
        fig_bar.update_layout(showlegend=False, xaxis_title="Count of Homes", yaxis_title="Feature")
        st.plotly_chart(fig_bar, use_container_width=True)
    else:
        st.info("No verified mitigations yet.")

# --- 5. DETAILED BREAKDOWNS (Tabs) ---
st.markdown("---")
st.subheader("🔍 Response Analysis")

t1, t2 = st.tabs(["📝 Lite Form Answers (Self-Reported)", "📸 Photo Verification Status"])

with t1:
    st.info("What homeowners are saying about their own properties (Self-Reported Data).")
    
    lite_cols = [c for c in df.columns if c.startswith("Lite_")]
    if lite_cols:
        melted_lite = df[lite_cols].melt(var_name="Question", value_name="Response")
        # Filter out empty responses and blanks
        melted_lite = melted_lite[melted_lite["Response"].astype(str) != ""]
        melted_lite["Question"] = melted_lite["Question"].str.replace("Lite_", "")
        
        fig_lite = px.histogram(
            melted_lite, 
            x="Question", 
            color="Response", 
            barmode="group",
            title="Distribution of Self-Reported Answers",
            color_discrete_map={"Yes": "#00CC96", "No": "#EF553B", "Unsure": "#FFA15A", "No Gutters": "gray", "No Trees": "gray"}
        )
        st.plotly_chart(fig_lite, use_container_width=True)

with t2:
    st.info("Results from the Human/AI Review of submitted photos.")
    
    photo_cols = [c for c in df.columns if c.startswith("Photo_")]
    if photo_cols:
        melted_photo = df[photo_cols].melt(var_name="Feature", value_name="Status")
        # Filter out empty strings
        melted_photo = melted_photo[melted_photo["Status"].astype(str) != ""]
        melted_photo["Feature"] = melted_photo["Feature"].str.replace("Photo_", "")
        
        fig_photo = px.histogram(
            melted_photo, 
            y="Feature", 
            color="Status", 
            barmode="stack",
            orientation="h",
            title="Verification Outcomes",
            color_discrete_map={
                "Verified Class A": "green", "Verified Mesh": "green", "Verified Metal": "green", "Verified Enclosed": "green", 
                "Verified Dual Pane": "green", "Verified Clearance": "green", "Verified Clear": "green", "Verified Gate": "green", "Verified Trimmed": "green", "Verified Distant": "green",
                "Non-Compliant": "red", "Combustible Found": "red", "Debris Found": "red", "Wood to Wall": "red", "Overhang": "red", "Too Close": "red", "Exposed Rafters": "red", "Single Pane": "red",
                "Unclear": "orange"
            }
        )
        st.plotly_chart(fig_photo, use_container_width=True)

# --- 6. RAW DATA VIEW ---
with st.expander("📂 View Raw Campaign Data (Active Only)"):
    st.dataframe(df)