import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Risk Prioritization Engine", layout="wide")

# --- LOGIN BLOCK ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True
    st.title("🔒 Faura Analytics Sandbox")
    with st.form("login_form"):
        st.write("Enter access code:")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log In"):
            if password == "Faura2026":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("Incorrect Password")
    return False

if not check_password():
    st.stop()

# --- MAIN CONTENT ---
st.title("🎯 Pure Risk Prioritization Engine")
st.markdown("""
**The Philosophy:** Behavioral proxies (like tenure or email opens) are unreliable. 
**The Solution:** Prioritize strictly by **Gross Expected Loss**. Target the properties where the carrier has the most to lose.
""")

# --- 1. DATA GENERATION ---
@st.cache_data
def generate_portfolio(n=1000):
    np.random.seed(42)
    
    # 1. TIV ($250k - $5M)
    tiv = np.random.lognormal(mean=13.5, sigma=0.6, size=n)
    tiv = np.clip(tiv, 250000, 5000000)
    
    # 2. Construction Year (1950 - 2024)
    # Weighted towards older homes (common in high risk CA areas)
    years = np.random.triangular(1950, 1980, 2024, size=n).astype(int)
    
    # 3. Fire Probability (0.1% to 5%)
    # Slightly correlated with older homes (built deeper in WUI)
    prob_fire = np.random.beta(2, 50, size=n) 
    prob_fire = np.clip(prob_fire, 0.001, 0.05)
    
    # 4. Resilience Score (The MDR Proxy)
    # Correlation: Older homes generally have lower scores (worse resilience)
    # But some old homes are retrofitted (noise)
    base_score = 60 + ((years - 1980) * 0.5) 
    qa_score = base_score + np.random.normal(0, 10, size=n)
    qa_score = np.clip(qa_score, 10, 95)
    
    df = pd.DataFrame({
        "Policy ID": [f"POL-{i:04d}" for i in range(n)],
        "Year_Built": years,
        "TIV": tiv,
        "Fire_Prob": prob_fire,
        "Resilience_Score": qa_score,
    })
    
    # --- METRIC: ESTIMATED MDR (Mean Damage Ratio) ---
    # Logic: Lower Score = Higher Damage. Clamped at 10% min damage.
    df["MDR_Est"] = ((100 - df["Resilience_Score"]) / 100).clip(lower=0.10)

    # --- METRIC: GROSS EXPECTED LOSS (ANNUAL) ---
    # The "Hard Variable" Truth: TIV * P(Fire) * MDR
    df["Expected_Loss_Annual"] = df["TIV"] * df["Fire_Prob"] * df["MDR_Est"]
    
    return df

# --- SIDEBAR ---
st.sidebar.header("Campaign Constraints")
budget_count = st.sidebar.slider("Campaign Target Size (Homes)", 50, 500, 200)

df = generate_portfolio()

# --- 2. STRATEGY LOGIC ---

# Strategy A: FAURA PRIORITIZED (Risk First)
df["Rank_Risk"] = df["Expected_Loss_Annual"]

# Strategy B: RANDOM (Status Quo / Alphabetical)
# Simulates what happens if they just call down the list without data
df["Rank_Random"] = np.random.rand(len(df))

# --- 3. RUN SIMULATION ---
def evaluate_campaign(rank_col, name):
    # Select top N
    campaign = df.sort_values(rank_col, ascending=False).head(budget_count)
    
    # Metrics
    total_tiv = campaign["TIV"].sum()
    total_risk = campaign["Expected_Loss_Annual"].sum()
    avg_score = campaign["Resilience_Score"].mean()
    avg_year = campaign["Year_Built"].mean()
    
    return {
        "Name": name,
        "Total Risk Targeted": total_risk,
        "Total TIV Touched": total_tiv,
        "Avg Resilience Score": avg_score,
        "Avg Year Built": avg_year,
        "Selection": campaign
    }

res_faura = evaluate_campaign("Rank_Risk", "Faura Risk Prioritized")
res_rand  = evaluate_campaign("Rank_Random", "Random Outreach (Control)")

# --- 4. DASHBOARD ---

# METRICS ROW
st.subheader("📊 Impact Analysis")
c1, c2, c3 = st.columns(3)

# Calculate Lift
risk_lift = (res_faura["Total Risk Targeted"] - res_rand["Total Risk Targeted"])
risk_lift_pct = (risk_lift / res_rand["Total Risk Targeted"]) * 100

c1.metric("Risk Exposure Targeted (Faura)", f"${res_faura['Total Risk Targeted']:,.0f}", delta=f"+{risk_lift_pct:.0f}% Lift")
c2.metric("Risk Exposure Targeted (Random)", f"${res_rand['Total Risk Targeted']:,.0f}", delta="Baseline", delta_color="off")
c3.metric("Avg Resilience of Target Group", f"{res_faura['Avg Resilience Score']:.0f}/100", help="Lower is better (means we are targeting the most vulnerable homes)")

# --- 5. LIFT CHART ---
st.markdown("---")
st.subheader("📈 The Value of Sorting")
st.markdown("**Question:** *'Why do we need data? Why not just call customers at random?'*")
st.markdown("**Answer:** Because risk is not evenly distributed. A small % of homes hold the majority of the risk.")

def get_lift_curve(rank_col, name):
    sorted_df = df.sort_values(rank_col, ascending=False).reset_index(drop=True)
    sorted_df["Cum_Risk"] = sorted_df["Expected_Loss_Annual"].cumsum()
    
    total_risk = df["Expected_Loss_Annual"].sum()
    sorted_df["% Total Risk"] = sorted_df["Cum_Risk"] / total_risk
    sorted_df["% Homes Targeted"] = (sorted_df.index + 1) / len(sorted_df)
    sorted_df["Strategy"] = name
    return sorted_df[["% Homes Targeted", "% Total Risk", "Strategy"]]

lift_data = pd.concat([
    get_lift_curve("Rank_Risk", "Faura Prioritized"),
    get_lift_curve("Rank_Random", "Random Outreach")
])

fig = px.line(lift_data, x="% Homes Targeted", y="% Total Risk", color="Strategy",
              color_discrete_map={
                  "Faura Prioritized": "#00CC96", # Green
                  "Random Outreach": "#EF553B",   # Red
              })
fig.add_vline(x=budget_count/len(df), line_dash="dash", line_color="grey", annotation_text="Budget Cutoff")
fig.update_layout(height=450, xaxis_tickformat=".0%", yaxis_tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)

# --- 6. TARGET LIST PREVIEW ---
st.markdown("---")
st.subheader(f"📋 Priority Target List ({budget_count} Homes)")
st.caption("Notice that we prioritize Older Homes and Low Scores, but **High TIV** often bumps a newer home up the list if the financial loss potential is high enough.")

target_list = res_faura['Selection'].copy()

st.dataframe(
    target_list[["Policy ID", "Year_Built", "TIV", "Resilience_Score", "MDR_Est", "Expected_Loss_Annual"]],
    column_config={
        "Year_Built": st.column_config.NumberColumn(format="%d"),
        "TIV": st.column_config.NumberColumn(format="$%d"),
        "Resilience_Score": st.column_config.NumberColumn("QA Score", format="%d"),
        "MDR_Est": st.column_config.ProgressColumn("Vuln. (MDR)", format="%.2f", min_value=0, max_value=1),
        "Expected_Loss_Annual": st.column_config.NumberColumn("Annual Risk Exp.", format="$%d", help="The primary sorting factor")
    },
    use_container_width=True
)

st.download_button("📥 Download Priority List", target_list.to_csv(index=False), "faura_priority_targets.csv")