import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

# --- PAGE CONFIG ---
st.set_page_config(page_title="Campaign Prioritizer", layout="wide")

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
st.title("🎯 Intelligent Campaign Prioritizer")
st.markdown("""
**The Challenge:** You have a large portfolio of policies, but limited resources for outreach.  
**The Solution:** Prioritize homes based on **Risk Exposure** (TIV × Fire Prob × Vulnerability) and **Likelihood to Engage**.
""")

# --- 1. DATA GENERATION ---
@st.cache_data
def generate_portfolio(n=1000):
    np.random.seed(42)
    
    # 1. TIV ($250k - $5M)
    tiv = np.random.lognormal(mean=13.5, sigma=0.6, size=n)
    tiv = np.clip(tiv, 250000, 5000000)
    
    # 2. Fire Probability (0.1% to 5%)
    prob_fire = np.random.beta(2, 50, size=n) 
    prob_fire = np.clip(prob_fire, 0.001, 0.05)
    
    # 3. Quick Assessment Score (0-100) -> Proxy for MDR
    # Higher Score = Lower Expected Damage
    qa_score = np.random.normal(60, 15, size=n)
    qa_score = np.clip(qa_score, 10, 95)
    
    # 4. Engagement Probability (5% to 60%)
    engage_prob = np.random.beta(2, 5, size=n)
    engage_prob = np.clip(engage_prob, 0.05, 0.60)
    
    df = pd.DataFrame({
        "Policy ID": [f"POL-{i:04d}" for i in range(n)],
        "TIV": tiv,
        "Fire_Prob": prob_fire,
        "Resilience_Score": qa_score,
        "Engagement_Prob": engage_prob, 
    })
    
    # --- METRIC: ESTIMATED MDR (Mean Damage Ratio) ---
    # User Request: Use QA Score as proxy for MDR.
    # Logic: Score 0 = 100% Damage (1.0). Score 100 = 0% Damage (0.0).
    # To be conservative, let's clamp min MDR to 0.10 (10%)
    df["MDR_Est"] = (100 - df["Resilience_Score"]) / 100
    df["MDR_Est"] = df["MDR_Est"].clip(lower=0.10)

    # --- METRIC: GROSS EXPECTED LOSS (ANNUAL) ---
    # The pure risk metric: TIV * P(Fire) * MDR
    df["Expected_Loss_Annual"] = df["TIV"] * df["Fire_Prob"] * df["MDR_Est"]
    
    return df

# --- SIDEBAR ---
st.sidebar.header("Campaign Settings")
budget_count = st.sidebar.slider("Campaign Target Size (Homes)", 50, 500, 200)

# Load Data
df = generate_portfolio()

# --- 2. SCORING STRATEGIES ---

# A. Risk Only (Actuarial) - Sort by highest Expected Loss
df["Score_RiskOnly"] = df["Expected_Loss_Annual"]

# B. Engagement Only (Marketing) - Sort by highest propensity
df["Score_Engagement"] = df["Engagement_Prob"]

# C. Faura Smart Score (Composite)
# Logic: We want to target the "At-Risk Dollars" that we can actually influence.
# Smart Score = Annual Expected Loss * Probability of Engagement
df["Score_Smart"] = df["Expected_Loss_Annual"] * df["Engagement_Prob"]

# --- 3. RUN CAMPAIGNS ---
def run_campaign(sort_col):
    campaign = df.sort_values(sort_col, ascending=False).head(budget_count)
    return campaign

camp_risk = run_campaign("Score_RiskOnly")
camp_engage = run_campaign("Score_Engagement")
camp_smart = run_campaign("Score_Smart")

# --- 4. METRICS COMPARISON ---
st.subheader("🏆 Strategy Comparison")

# Metrics to track:
# 1. Total Risk Exposure Targeted (The sum of Expected Loss in the target group)
# 2. "Risk at Play" (Risk Exposure * Engagement Prob) -> The risk we have a statistical chance of touching

col1, col2, col3 = st.columns(3)

def show_card(col, title, campaign_df, baseline_val):
    # Metric: Total Expected Loss in this group
    total_risk_exposure = campaign_df["Expected_Loss_Annual"].sum()
    
    # Metric: Weighted Risk (Risk * Engage Prob)
    # This represents the "Risk Dollars we are statistically likely to engage"
    weighted_risk = (campaign_df["Expected_Loss_Annual"] * campaign_df["Engagement_Prob"]).sum()
    
    col.markdown(f"**{title}**")
    col.metric("Risk Exposure Targeted", f"${total_risk_exposure:,.0f}")
    
    delta = weighted_risk - baseline_val
    col.metric("Actionable Risk (Weighted)", f"${weighted_risk:,.0f}", 
               delta=f"{delta/baseline_val*100:+.1f}% vs Risk-Only" if baseline_val>0 else None)

# Baseline is Risk Only strategy's weighted risk
baseline_weighted = (camp_risk["Expected_Loss_Annual"] * camp_risk["Engagement_Prob"]).sum()

show_card(col1, "Strategy A: Highest Risk", camp_risk, baseline_weighted)
show_card(col2, "Strategy B: Highest Engagement", camp_engage, baseline_weighted)
show_card(col3, "Strategy C: Faura Smart Score", camp_smart, baseline_weighted)

# --- 5. LIFT CURVE ---
st.markdown("---")
st.subheader("📈 Risk Capture Curve")
st.markdown(f"If we only target **{budget_count} homes** (the dotted line), how much of the portfolio's total risk exposure are we addressing?")

def get_lift_data(sort_col, name):
    sorted_df = df.sort_values(sort_col, ascending=False).reset_index(drop=True)
    
    # Cumulative Risk Exposure
    sorted_df["Cum_Risk"] = sorted_df["Expected_Loss_Annual"].cumsum()
    
    # Normalize
    total_risk = df["Expected_Loss_Annual"].sum()
    sorted_df["% Total Risk"] = sorted_df["Cum_Risk"] / total_risk
    sorted_df["% Homes Targeted"] = (sorted_df.index + 1) / len(sorted_df)
    sorted_df["Strategy"] = name
    return sorted_df[["% Homes Targeted", "% Total Risk", "Strategy"]]

lift_df = pd.concat([
    get_lift_data("Score_RiskOnly", "Risk Only (Highest Loss)"),
    get_lift_data("Score_Engagement", "Engagement Only"),
    get_lift_data("Score_Smart", "Faura Smart Score")
])

fig = px.line(lift_df, x="% Homes Targeted", y="% Total Risk", color="Strategy",
              color_discrete_map={
                  "Risk Only (Highest Loss)": "#EF553B", 
                  "Engagement Only": "#FFA15A", 
                  "Faura Smart Score": "#00CC96"
              })

fig.add_vline(x=budget_count/len(df), line_dash="dash", line_color="grey", annotation_text="Budget Limit")
fig.update_layout(height=450, xaxis_tickformat=".0%", yaxis_tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)

# --- 6. TARGET LIST ---
st.markdown("---")
st.subheader(f"📋 Priority Target List ({budget_count} Homes)")

# Format for display (0-100 scale for progress bars)
display_df = camp_smart.copy()
display_df["Engagement_Pct"] = display_df["Engagement_Prob"] * 100 

st.dataframe(
    display_df[["Policy ID", "TIV", "Resilience_Score", "MDR_Est", "Engagement_Pct", "Expected_Loss_Annual"]],
    column_config={
        "TIV": st.column_config.NumberColumn(format="$%d"),
        "MDR_Est": st.column_config.ProgressColumn("Est. MDR", format="%.2f", min_value=0, max_value=1, help="Derived from Resilience Score (Lower Score = Higher Damage Ratio)"),
        "Resilience_Score": st.column_config.NumberColumn("QA Score", format="%d"),
        "Engagement_Pct": st.column_config.ProgressColumn("Engagement Prob", format="%.0f%%", min_value=0, max_value=100),
        "Expected_Loss_Annual": st.column_config.NumberColumn("Annual Risk Exp.", format="$%d", help="TIV × FireProb × MDR")
    },
    use_container_width=True
)

# Download Button
st.download_button("📥 Download Smart List", display_df.to_csv(index=False), "smart_targets.csv")