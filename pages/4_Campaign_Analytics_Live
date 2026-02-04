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
        # REPLACE WITH YOUR GOOGLE SHEET URL
        df = conn.read(
            spreadsheet="https://docs.google.com/spreadsheets/d/1Ank5NAk3qCuYKVK7F580aRU5I2DPDJ6lxLSa66PF33o/edit?gid=1749003768#gid=1749003768",
            worksheet="Campaign" 
        )
        return df
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return pd.DataFrame()

df = load_campaign_data()

if df.empty:
    st.warning("⚠️ No campaign data found. Check your 'Campaign_Tracker' tab.")
    st.stop()

# --- 2. METRIC CALCULATIONS ---
total_sent = len(df)
opened = df[df["Opened Email"] == True].shape[0]
unsubscribed = df[df["Unsubscribed"] == True].shape[0]
lite_completed = df[df["Finished Lite PSA form"] == True].shape[0]
photos_submitted = df[df["Submitted any photos"] == True].shape[0]

# "Verified Mitigated" is tricky. Let's count anyone who has at least one "Verified" column in the mitigation section
# We grab columns that start with "Mitigated_"
mitigation_cols = [c for c in df.columns if c.startswith("Mitigated_")]
# Check if any of those columns equal "Verified" for each row
mitigated_count = df[mitigation_cols].apply(lambda x: x.isin(["Verified"]).any(), axis=1).sum()

# --- 3. HEADER METRICS ---
st.title("📢 Campaign Operations Center")
st.markdown("### Engagement & Conversion Tracking")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Emails Sent", total_sent)
c2.metric("Open Rate", f"{(opened/total_sent)*100:.1f}%", f"{opened} Opens")
c3.metric("Lite Form Rate", f"{(lite_completed/opened)*100:.1f}%", f"{lite_completed} Responses", help="% of Openers who finished form")
c4.metric("Photo Conversion", f"{(photos_submitted/lite_completed)*100:.1f}%", f"{photos_submitted} Verified", help="% of Forms that added photos")
c5.metric("Active Mitigations", mitigated_count, delta="Value Add", help="Homes that fixed a specific issue")

st.markdown("---")

# --- 4. THE FUNNEL CHART ---
col_funnel, col_details = st.columns([2, 1])

with col_funnel:
    st.subheader("📉 Campaign Conversion Funnel")
    
    # Data for Funnel
    stages = ["Emails Sent", "Opened Email", "Completed Lite Form", "Submitted Photos", "Verified Mitigation"]
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
    
    st.markdown("#### Top Mitigation Actions")
    # Count verified mitigations per category
    mitigation_counts = df[mitigation_cols].apply(lambda x: x.value_counts()).loc["Verified"].sort_values(ascending=True)
    
    # Clean up names for the chart (remove "Mitigated_")
    mitigation_counts.index = [x.replace("Mitigated_", "") for x in mitigation_counts.index]
    
    fig_bar = px.bar(mitigation_counts, orientation='h', title="Verified Fixes by Category")
    fig_bar.update_layout(showlegend=False, xaxis_title="Count of Homes", yaxis_title="Feature")
    st.plotly_chart(fig_bar, use_container_width=True)

# --- 5. DETAILED BREAKDOWNS (Tabs) ---
st.markdown("---")
st.subheader("🔍 Response Analysis")

t1, t2 = st.tabs(["📝 Lite Form Answers (Self-Reported)", "📸 Photo Verification Status"])

with t1:
    st.info("What homeowners are saying about their own properties (Self-Reported Data).")
    
    # Get "Lite_" columns
    lite_cols = [c for c in df.columns if c.startswith("Lite_")]
    
    # Reshape for plotting: We want a stacked bar chart of Yes/No/Unsure for each Question
    # This is a bit advanced pandas manipulation to make it plot-ready
    melted_lite = df[lite_cols].melt(var_name="Question", value_name="Response")
    # Filter out empty responses
    melted_lite = melted_lite[melted_lite["Response"] != ""]
    
    # Clean up Question names
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
    melted_photo = df[photo_cols].melt(var_name="Feature", value_name="Status")
    melted_photo = melted_photo[melted_photo["Status"] != ""]
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
with st.expander("📂 View Raw Campaign Data"):
    st.dataframe(df)