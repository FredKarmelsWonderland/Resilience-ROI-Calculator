import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

# --- PAGE CONFIG ---
st.set_page_config(page_title="Campaign Prioritizer", layout="wide")

# --- 2. STANDARDIZED LOGIN BLOCK ---
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
**The Challenge:** You have 1,000 policies in a high-risk zone, but only budget to engage 200 of them.  
**The Solution:** Instead of random outreach, prioritize based on **Risk Reduction Potential** and **Propensity to Engage**.
""")

# --- 1. DATA GENERATION (Simulating the API Step) ---
@st.cache_data
def generate_portfolio(n=1000):
    np.random.seed(42)
    
    # 1. TIV (Log-normal distribution to create realistic outliers)
    tiv = np.random.lognormal(mean=13.5, sigma=0.6, size=n) # Median ~$700k
    tiv = np.clip(tiv, 250000, 5000000)
    
    # 2. Fire Probability (0.1% to 5%)
    # Correlated slightly with TIV (richer homes often in hills)
    prob_fire = np.random.beta(2, 50, size=n) 
    prob_fire = np.clip(prob_fire, 0.001, 0.05)
    
    # 3. Quick Assessment Score (0-100)
    # Higher Score = Better Resilience = LESS Potential to Improve
    qa_score = np.random.normal(60, 15, size=n)
    qa_score = np.clip(qa_score, 10, 95)
    
    # 4. Engagement Probability (0% to 60%)
    # Random propensity (simulating email open rates, demographics)
    engage_prob = np.random.beta(2, 5, size=n)
    engage_prob = np.clip(engage_prob, 0.05, 0.60)
    
    # DATAFRAME
    df = pd.DataFrame({
        "Policy ID": [f"POL-{i:04d}" for i in range(n)],
        "TIV": tiv,
        "Fire_Prob": prob_fire,
        "Resilience_Score": qa_score,   # 0=Bad, 100=Good
        "Engagement_Prob": engage_prob, # Likelihood to act
    })
    
    # --- CALCULATED METRICS ---
    
    # A. Gross Expected Loss (Status Quo)
    # Loss = TIV * Prob * Vulnerability (proxied by 100 - Score)
    # We divide by 100 to normalize score impact
    df["Expected_Loss_Annual"] = df["TIV"] * df["Fire_Prob"] * ((100 - df["Resilience_Score"]) / 100)
    
    # B. Potential Savings (If Mitigated)
    # Assume we can improve Resilience Score by +20 points on average
    # Savings = TIV * Prob * (Improvement_Delta)
    improvement_delta = 0.20 
    df["Potential_Savings"] = df["TIV"] * df["Fire_Prob"] * improvement_delta
    
    return df

# --- SIDEBAR CONTROLS ---
st.sidebar.header("Campaign Constraints")
budget_count = st.sidebar.slider("Campaign Budget (Homes to Target)", 50, 500, 200)

st.sidebar.markdown("### Algorithm Weights")
st.sidebar.info("Adjust how much Faura values Risk vs. Engagement in the 'Smart Score'.")
w_risk = st.sidebar.slider("Weight: Financial Risk", 0.0, 1.0, 0.7)
w_engage = st.sidebar.slider("Weight: Conversion Likelihood", 0.0, 1.0, 0.3)

# Load Data
df = generate_portfolio()

# --- 2. SCORING ALGORITHMS ---

# Strategy A: Risk Only (Actuarial View)
df["Score_RiskOnly"] = df["Potential_Savings"] 

# Strategy B: Conversion Only (Marketing View)
df["Score_ConversionOnly"] = df["Engagement_Prob"]

# Strategy C: Faura Smart Score (Composite)
# Normalize inputs first (0-1 scale) so weights work
norm_risk = (df["Potential_Savings"] - df["Potential_Savings"].min()) / (df["Potential_Savings"].max() - df["Potential_Savings"].min())
norm_engage = (df["Engagement_Prob"] - df["Engagement_Prob"].min()) / (df["Engagement_Prob"].max() - df["Engagement_Prob"].min())

# Formula: (Risk * w1) * (Engage * w2)
# Multiplicative is usually better than additive for "AND" logic (High Risk AND High Engage)
# But strictly for ranking, additive with weights is easier to visualize in sliders
# Let's use the 'Expected Realized Value' logic: Savings * Prob_Conversion
df["Score_FauraSmart"] = (df["Potential_Savings"] ** w_risk) * (df["Engagement_Prob"] ** w_engage)

# --- 3. RUNNING THE CAMPAIGNS ---

def run_campaign(strategy_col):
    # Sort descending by score
    campaign = df.sort_values(strategy_col, ascending=False).head(budget_count)
    
    # Metrics
    avg_tiv = campaign["TIV"].mean()
    avg_risk = campaign["Expected_Loss_Annual"].mean()
    
    # REALIZED VALUE = Potential Savings * Probability they actually convert
    # This is the "Honest" ROI metric
    realized_value = (campaign["Potential_Savings"] * campaign["Engagement_Prob"]).sum()
    
    return campaign, realized_value

camp_risk, val_risk = run_campaign("Score_RiskOnly")
camp_conv, val_conv = run_campaign("Score_ConversionOnly")
camp_smart, val_smart = run_campaign("Score_FauraSmart")

# --- 4. DASHBOARD ---

# Top Metrics (Comparison)
st.subheader("🏆 Strategy Comparison")
c1, c2, c3 = st.columns(3)

def metric_card(col, title, value, baseline, description):
    delta = value - baseline
    delta_pct = (delta / baseline) * 100 if baseline > 0 else 0
    col.metric(title, f"${value:,.0f}", f"{delta_pct:+.1f}% vs Risk-Only")
    col.caption(description)

metric_card(c1, "Risk-Only Strategy", val_risk, val_risk, "Sort by Highest Potential Loss")
metric_card(c2, "Engagement Strategy", val_conv, val_risk, "Sort by Highest Open Rate")
metric_card(c3, "Faura Smart Score", val_smart, val_risk, "Sort by Risk × Engagement")

# --- 5. LIFT CURVE VISUALIZATION ---
st.markdown("---")
st.subheader("📈 The 'Lift' Curve")
st.markdown("This chart shows why prioritization matters. It answers: **'If we only have budget for X homes, how much total risk value do we capture?'**")

# Prepare Lift Data
def get_lift_curve(sort_col, name):
    sorted_df = df.sort_values(sort_col, ascending=False).reset_index(drop=True)
    # Calculate "Realized Value" cumulatively
    sorted_df["Realized_Value"] = sorted_df["Potential_Savings"] * sorted_df["Engagement_Prob"]
    sorted_df["Cumulative_Value"] = sorted_df["Realized_Value"].cumsum()
    # Normalize to %
    total_market_value = (df["Potential_Savings"] * df["Engagement_Prob"]).sum()
    sorted_df["% Total Value"] = sorted_df["Cumulative_Value"] / total_market_value
    sorted_df["% Homes Targeted"] = (sorted_df.index + 1) / len(sorted_df)
    sorted_df["Strategy"] = name
    return sorted_df[["% Homes Targeted", "% Total Value", "Strategy"]]

lift_df = pd.concat([
    get_lift_curve("Score_RiskOnly", "Risk Only (Traditional)"),
    get_lift_curve("Score_ConversionOnly", "Engagement Only"),
    get_lift_curve("Score_FauraSmart", "Faura Smart Score")
])

# Create Plot
fig = px.line(lift_df, x="% Homes Targeted", y="% Total Value", color="Strategy",
              color_discrete_map={
                  "Risk Only (Traditional)": "#EF553B", # Red
                  "Engagement Only": "#FFA15A", # Orange
                  "Faura Smart Score": "#00CC96" # Green
              })

# Add the "Cutoff" line
cutoff_x = budget_count / len(df)
fig.add_vline(x=cutoff_x, line_dash="dash", line_color="grey", annotation_text="Budget Cutoff")

fig.update_layout(height=500, xaxis_tickformat=".0%", yaxis_tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)

# --- 6. TARGET LIST PREVIEW ---
st.markdown("---")
st.subheader(f"📋 Your Target List ({budget_count} Homes)")

# Show the 'Smart' list by default
target_display = camp_smart[["Policy ID", "TIV", "Resilience_Score", "Engagement_Prob", "Potential_Savings"]].copy()
target_display["Est. Realized Value"] = target_display["Potential_Savings"] * target_display["Engagement_Prob"]

st.dataframe(
    target_display.sort_values("Est. Realized Value", ascending=False),
    column_config={
        "TIV": st.column_config.NumberColumn(format="$%d"),
        "Potential_Savings": st.column_config.NumberColumn(format="$%d"),
        "Est. Realized Value": st.column_config.NumberColumn(format="$%d", help="Savings × Engagement Prob"),
        "Engagement_Prob": st.column_config.ProgressColumn(format="%.0f%%", min_value=0, max_value=1),
        "Resilience_Score": st.column_config.ProgressColumn(format="%d", min_value=0, max_value=100)
    },
    use_container_width=True
)

st.download_button(
    "📥 Download Campaign List (CSV)",
    data=camp_smart.to_csv(index=False),
    file_name="faura_smart_campaign_targets.csv",
    mime="text/csv"
)