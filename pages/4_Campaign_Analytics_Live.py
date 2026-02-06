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

# --- 3. FILTERING ACTIVE CAMPAIGN ---
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

# Calculations for Export
open_yield = safe_calc(opened, total_sent)
unsub_rate = safe_calc(unsubscribed, total_sent)
lite_yield = safe_calc(lite_completed, total_sent)
lite_conversion = safe_calc(lite_completed, opened)
photo_yield = safe_calc(photos_submitted, total_sent)
photo_conversion = safe_calc(photos_submitted, lite_completed)
fix_yield = safe_calc(mitigated_count, total_sent)
fix_conversion = safe_calc(mitigated_count, photos_submitted)

# --- 6. TOP DASHBOARD ---
st.title("Campaign Operations Center")
st.markdown("### Engagement & Conversion Tracking")

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Emails Sent", total_sent, help="Total Active Pilot Group")
c2.metric("Opened Email", opened, f"{open_yield:.0f}% of Total", help=f"{opened} opens out of {total_sent}")
c3.metric("Unsubscribes", unsubscribed, f"{unsub_rate:.1f}% of Total", delta_color="inverse", help="Opt-outs")
c4.metric("Lite Forms", lite_completed, f"{lite_yield:.0f}% of Total", help=f"Step Conversion: {lite_conversion:.1f}% of Openers")
c5.metric("Photos Submitted", photos_submitted, f"{photo_yield:.0f}% of Total", help=f"Step Conversion: {photo_conversion:.1f}% of Lite Forms")
c6.metric("Verified Fixes", mitigated_count, f"{fix_yield:.0f}% of Total", help=f"Step Conversion: {fix_conversion:.1f}% of Submissions")

st.markdown("---")

# --- 7. FUNNEL & DETAILS ---
col_funnel, col_details = st.columns([2, 1])

with col_funnel:
    st.subheader("📉 Campaign Conversion Funnel")
    stages = ["Emails Sent", "Opened Email", "Completed Lite Form", "Submitted Photos", "Verified Value-Add"]
    values = [total_sent, opened, lite_completed, photos_submitted, mitigated_count]
    
    fig_funnel = go.Figure(go.Funnel(
        y = stages, x = values, textinfo = "value+percent initial",
        marker = {"color": ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A"]},
        textfont = dict(size=14, color="white")
    ))
    fig_funnel.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=450, font=dict(size=14))
    st.plotly_chart(fig_funnel, use_container_width=True)

with col_details:
    st.subheader("🏆 Top Verified Fixes")
    if mitigation_cols:
        mit_counts = df[mitigation_cols].astype(str).apply(lambda x: x.str.contains("verified", case=False, na=False).sum())
        mit_counts = mit_counts[mit_counts > 0].sort_values(ascending=True)
        if not mit_counts.empty:
            mit_counts.index = [x.replace("Mitigated_", "").replace("_", " ") for x in mit_counts.index]
            fig_bar = px.bar(x=mit_counts.values, y=mit_counts.index, orientation='h')
            fig_bar.update_layout(showlegend=False, xaxis_title="Count", yaxis_title=None, height=400, font=dict(size=13))
            st.plotly_chart(fig_bar, use_container_width=True)
        else:
            st.info("No verified mitigations found.")

# --- 8. DETAILED RESPONSE GRIDS ---
st.markdown("---")
st.subheader("🔍 Response Breakdown")
t1, t2 = st.tabs(["📝 Lite Form Breakdown", "📸 Photo Verification Status"])

color_map_lite = {"Yes": "#00CC96", "No": "#EF553B", "Unsure": "#FFA15A", "No Gutters": "lightgray", "No Trees": "lightgray", "No Deck": "lightgray"}

with t1:
    lite_cols = [c for c in df.columns if c.startswith("Lite_")]
    if lite_cols:
        cols = st.columns(3)
        for i, col_name in enumerate(lite_cols):
            feature_name = col_name.replace("Lite_", "").replace("_", " ")
            clean_series = df[col_name].astype(str).str.strip()
            clean_series = clean_series[clean_series.str.len() > 0]
            clean_series = clean_series[~clean_series.str.lower().isin(["nan", "none"])]
            if not clean_series.empty:
                counts = clean_series.value_counts().reset_index()
                counts.columns = ["Answer", "Count"]
                fig = px.pie(counts, names="Answer", values="Count", title=f"<b>{feature_name}</b>",
                             color="Answer", color_discrete_map=color_map_lite, hole=0.4)
                fig.update_layout(showlegend=True, margin=dict(t=30, b=0, l=0, r=0), height=250)
                with cols[i % 3]:
                    st.plotly_chart(fig, use_container_width=True)

with t2:
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
                fig = px.pie(counts, names="Status", values="Count", title=f"<b>{feature_name}</b>", hole=0.4)
                fig.update_traces(marker=dict(colors=["#00CC96" if "verified" in x.lower() else "#EF553B" if "compliant" in x.lower() else "#FFA15A" for x in counts["Status"]]))
                fig.update_layout(showlegend=False, margin=dict(t=30, b=0, l=0, r=0), height=250)
                with cols[i % 3]:
                    st.plotly_chart(fig, use_container_width=True)

# --- 9. DATA EXPORT SECTION (UPDATED) ---
st.markdown("---")
st.subheader("📂 Data Export & Inspection")

# Create KPI Summary Dataframe
summary_data = {
    "Campaign Stage": ["Emails Sent", "Opened Email", "Unsubscribed", "Lite Forms", "Photos Submitted", "Verified Fixes"],
    "Count": [total_sent, opened, unsubscribed, lite_completed, photos_submitted, mitigated_count],
    "Yield (% of Total)": ["100%", f"{open_yield:.1f}%", f"{unsub_rate:.1f}%", f"{lite_yield:.1f}%", f"{photo_yield:.1f}%", f"{fix_yield:.1f}%"],
    "Step Conversion": ["N/A", "N/A", "N/A", f"{lite_conversion:.1f}% (of Opens)", f"{photo_conversion:.1f}% (of Forms)", f"{fix_conversion:.1f}% (of Photos)"]
}
df_summary = pd.DataFrame(summary_data)

c_actions, c_table = st.columns([1, 4])

with c_actions:
    st.markdown("#### Export Options")
    
    # 1. RAW DATA DOWNLOAD
    csv_raw = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download Raw Data",
        data=csv_raw,
        file_name="Faura_Campaign_Raw_Data.csv",
        mime="text/csv",
        type="primary"
    )
    
    # 2. KPI REPORT DOWNLOAD
    csv_kpi = df_summary.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📊 Download KPI Report",
        data=csv_kpi,
        file_name="Faura_Campaign_KPI_Summary.csv",
        mime="text/csv"
    )
    
    st.markdown("---")
    st.caption("ℹ️ To save the visual dashboard as a PDF, use your browser's **Print -> Save as PDF** feature (Cmd+P).")

with c_table:
    # Interactive Table
    st.markdown("#### Live Data Inspector")
    st.dataframe(df, use_container_width=True, hide_index=True, height=400)
