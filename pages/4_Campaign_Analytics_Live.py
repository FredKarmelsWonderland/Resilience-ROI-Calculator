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
@st.cache_data(ttl=0) # Force fresh data
def load_campaign_data():
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Load Data
        df = conn.read(
            spreadsheet="https://docs.google.com/spreadsheets/d/1Ank5NAk3qCuYKVK7F580aRU5I2DPDJ6lxLSa66PF33o/edit?gid=1749003768#gid=1749003768",
            worksheet="Campaign" 
        )
        
        # Cleanup Headers: Convert to string and strip whitespace
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
# Create a copy to work with
df = raw_df.copy()

# Robust Filter for "Campaign_Active"
if "Campaign_Active" in df.columns:
    # Normalize: String -> Lowercase -> Strip -> Check "true"
    # This handles "TRUE", "True", "true", "TRUE "
    df = df[df["Campaign_Active"].astype(str).str.lower().str.strip() == "true"]
else:
    st.error("❌ Column 'Campaign_Active' not found.")
    st.stop()

if df.empty:
    st.warning("⚠️ Data loaded, but no rows matched 'Campaign_Active = TRUE'.")
    st.stop()

# --- 4. ROBUST COUNTING LOGIC (The Fix) ---
def count_true(column_name):
    """
    Aggressively normalizes data to count TRUE values.
    """
    if column_name not in df.columns: 
        return 0
    
    # 1. Force convert entire column to String
    # 2. Lowercase everything ("TRUE" -> "true")
    # 3. Strip whitespace (" true " -> "true")
    clean_col = df[column_name].astype(str).str.lower().str.strip()
    
    # 4. Count exact matches
    return clean_col.isin(["true", "1", "yes", "t"]).sum()

def safe_calc(numerator, denominator):
    if denominator == 0: return 0
    return (numerator / denominator) * 100

# --- 5. CALCULATE METRICS ---
total_sent = len(df)
opened = count_true("Opened Email")
unsubscribed = count_true("Unsubscribed")
lite_completed = count_true("Finished Lite PSA form")
photos_submitted = count_true("Submitted any photos")

# Verified Mitigations Logic
mitigation_cols = [c for c in df.columns if c.startswith("Mitigated_")]
if mitigation_cols:
    # Convert all mitigation columns to string, lower, strip
    mit_df = df[mitigation_cols].astype(str).apply(lambda x: x.str.lower().str.strip())
    # Check if "verified" exists in the row
    mitigated_count = mit_df.apply(lambda x: x.str.contains("verified", na=False).any(), axis=1).sum()
else:
    mitigated_count = 0

# --- 6. DEBUG EXPANDER (Use this if it's still 0) ---
# with st.expander("🛠 Debug Data Inspector"):
#    st.write("First 5 rows of 'Opened Email' (cleaned):")
#    st.write(df["Opened Email"].astype(str).str.lower().str.strip().head())
#    st.write(f"Count calculated: {opened}")

# --- 7. DASHBOARD UI ---
st.title("📢 Campaign Operations Center")
st.markdown("### Engagement & Conversion Tracking")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Emails Sent", total_sent)
c2.metric("Open Rate", f"{safe_calc(opened, total_sent):.0f}%", f"{opened} Opens")
c3.metric("Lite Form Rate", f"{safe_calc(lite_completed, opened):.0f}%", f"{lite_completed} Responses", help="% of Openers who finished form")
c4.metric("Photo Conversion", f"{safe_calc(photos_submitted, lite_completed):.0f}%", f"{photos_submitted} Verified", help="% of Forms that added photos")
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
        # Re-calc for the chart using the clean logic
        mit_counts = df[mitigation_cols].astype(str).apply(lambda x: x.str.lower().str.strip())
        # We want to count how many rows have "verified" (partial match)
        # But for bar chart, we just need value counts of "verified"
        # We need to be careful: the R script might output "Verified" or "Verified Class A"
        # Let's count any cell containing "verified"
        
        # Create a series of just the "Verified" counts
        verified_counts = {}
        for col in mitigation_cols:
            # Count rows where this specific column contains "verified"
            count = mit_counts[col].str.contains("verified", na=False).sum()
            if count > 0:
                name = col.replace("Mitigated_", "").replace("_", " ")
                verified_counts[name] = count
        
        if verified_counts:
            s_counts = pd.Series(verified_counts).sort_values()
            fig_bar = px.bar(x=s_counts.values, y=s_counts.index, orientation='h', title="Verified Fixes")
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
        # Filter blanks (aggressive strip)
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
            # Clean status for coloring map
            melted["Status_Clean"] = melted["Status"].astype(str).str.lower().str.strip()
            
            # Map raw statuses to simple groups for color
            # Just relying on Plotly defaults if map fails, but trying to catch key phrases
            fig = px.histogram(melted, y="Feature", color="Status", barmode="stack", orientation="h")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No Photo data available yet.")