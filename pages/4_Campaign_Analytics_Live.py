import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Campaign Operations", layout="wide")

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

# --- 2. DATA LOADING ---
@st.cache_data(ttl=0) # Force fresh data
def load_campaign_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Load Data
        df = conn.read(
            spreadsheet="https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID_HERE/edit",
            worksheet="Campaign" 
        )
        
        # Cleanup Headers
        df.columns = df.columns.astype(str).str.strip()
        
        # Filter for Active Campaign
        target_col = "Campaign_Active"
        if target_col in df.columns:
            # Robust Filter: Convert to string, upper case, check for TRUE
            df = df[df[target_col].astype(str).str.strip().str.upper() == "TRUE"]
            
        return df
    except Exception as e:
        st.error(f"❌ Connection Error: {e}")
        return pd.DataFrame()

df = load_campaign_data()

if df.empty:
    st.warning("⚠️ No active campaign data found. Check 'Campaign_Active' column.")
    st.stop()

# --- 3. METRIC CALCULATIONS (The Fix) ---

def count_true(column_name):
    """
    Counts TRUE values robustly, handling mixed types (Booleans, Strings, Ints).
    """
    if column_name not in df.columns: 
        return 0
    
    # 1. Force convert everything to String
    # 2. Strip whitespace
    # 3. Uppercase
    # 4. Check against list of "Truth" values
    # This catches: True, "True", "TRUE", " true ", "1", 1
    clean_series = df[column_name].astype(str).str.strip().str.upper()
    return clean_series.isin(["TRUE", "1", "YES", "T"]).sum()

def safe_calc(numerator, denominator):
    if denominator == 0: return 0
    return (numerator / denominator) * 100

total_sent = len(df)
opened = count_true("Opened Email")
unsubscribed = count_true("Unsubscribed")
lite_completed = count_true("Finished Lite PSA form")
photos_submitted = count_true("Submitted any photos")

# Verified Mitigations
mitigation_cols = [c for c in df.columns if c.startswith("Mitigated_")]
if mitigation_cols:
    mitigated_count = df[mitigation_cols].apply(lambda x: x.isin(["Verified"]).any(), axis=1).sum()
else:
    mitigated_count = 0

# --- 4. DEBUG SECTION (Temporary) ---
# Un-comment this if it's STILL 0 to see exactly what the data looks like
# with st.expander("🛠 Debug: Inspect 'Opened Email' Column"):
#    st.write("Unique values found in 'Opened Email':")
#    st.write(df["Opened Email"].value_counts())

# --- 5. DASHBOARD LAYOUT ---
st.title("📢 Campaign Operations Center")
st.markdown("### Engagement & Conversion Tracking")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Emails Sent", total_sent)
c2.metric("Open Rate", f"{safe_calc(opened, total_sent):.0f}%", f"{opened} Opens")
c3.metric("Lite Form Rate", f"{safe_calc(lite_completed, opened):.0f}%", f"{lite_completed} Responses", help="% of Openers who finished form")
c4.metric("Photo Conversion", f"{safe_calc(photos_submitted, lite_completed):.0f}%", f"{photos_submitted} Verified", help="% of Forms that added photos")
c5.metric("Value-Add Fixes", mitigated_count, delta="Verified", help="Homes that fixed a specific issue")

st.markdown("---")

# --- 6. FUNNEL & DETAILS ---
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
        # Count 'Verified' specifically
        mitigation_counts = df[mitigation_cols].apply(pd.Series.value_counts).T
        if "Verified" in mitigation_counts.columns:
            counts = mitigation_counts["Verified"].sort_values(ascending=True)
            counts.index = [x.replace("Mitigated_", "") for x in counts.index]
            fig_bar = px.bar(counts, orientation='h', title="Verified Fixes")
            fig_bar.update_layout(showlegend=False, xaxis_title="Count", yaxis_title="Feature")
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No verified mitigations found.")

# --- 7. TABS ---
st.markdown("---")
st.subheader("🔍 Response Analysis")
t1, t2 = st.tabs(["📝 Lite Form Answers", "📸 Photo Verification"])

with t1:
    lite_cols = [c for c in df.columns if c.startswith("Lite_")]
    if lite_cols:
        melted = df[lite_cols].melt(var_name="Question", value_name="Response")
        melted = melted[melted["Response"].astype(str).str.strip() != ""]
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
        melted = melted[melted["Status"].astype(str).str.strip() != ""]
        if not melted.empty:
            melted["Feature"] = melted["Feature"].str.replace("Photo_", "")
            fig = px.histogram(melted, y="Feature", color="Status", barmode="stack", orientation="h",
                               color_discrete_map={"Verified Class A": "green", "Verified Mesh": "green", "Non-Compliant": "red", "Unclear": "orange"})
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No Photo data available yet.")