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

# --- PHILOSOPHY & SCENARIO SECTION ---
st.markdown("### The Pilot Scenario")

# Define costs for dynamic display
screening_cost_per = 3
outreach_cost_per = 30
psa_incentive = 50
mitigation_incentive = 300

c1, c2 = st.columns([2, 1])
with c1:
    st.info(f"""
    **The Constraints:**
    1.  Carrier provides a raw list of **1,000 homes**.
    2.  **Step 1 (Screening):** We screen *all* 1,000 homes at **${screening_cost_per}/address** to generate our ranking/targeting scores.
    3.  **Step 2 (Outreach):** We target the top **200 homes** with a pilot outreach budget of **${outreach_cost_per}/home**.
    
    **The "Pay-for-Performance" Funnel:**
    * **25% Engagement:** Homeowners who fill out the PSA get **${psa_incentive}**.
    * **15% Mitigation:** Homeowners who verify risk reduction get an additional **${mitigation_incentive}**.
    * *Result:* We don't waste budget on non-responders. We pay for results.
    """)
with c2:
    st.markdown("""
    **The Ranking/Targeting Algorithm:**
    $$
    \\text{Value} = P_{\\text{Wildfire}} \\times \\text{TIV} \\times \\text{MDR}
    $$
    *(Where MDR is proxied by 100 - QA Score)*
    """)

# --- 1. DATA GENERATION ---
@st.cache_data
def generate_portfolio(n=1000):
    np.random.seed(42)
    
    # 1. TIV ($250k - $5M)
    tiv = np.random.lognormal(mean=13.5, sigma=0.6, size=n)
    tiv = np.clip(tiv, 250000, 5000000)
    
    # 2. Fire Probability (0.1% to 2.5%)
    prob_fire = np.random.beta(2, 50, size=n) 
    prob_fire = np.clip(prob_fire, 0.001, 0.025)
    
    # 3. Resilience Score (The MDR Proxy)
    qa_score = np.random.normal(60, 15, size=n)
    qa_score = np.clip(qa_score, 10, 95)
    
    df = pd.DataFrame({
        "Policy ID": [f"POL-{i:04d}" for i in range(n)],
        "TIV": tiv,
        "Fire_Prob": prob_fire,
        "Resilience_Score": qa_score,
    })
    
    # --- METRIC: ANNUAL PREMIUM ---
    rate = np.random.uniform(0.002, 0.008, size=n)
    df["Annual_Premium"] = df["TIV"] * rate
    
    # --- METRIC: ESTIMATED MDR ---
    df["MDR_Est"] = ((100 - df["Resilience_Score"]) / 100).clip(lower=0.10)

    # --- METRIC: GROSS EXPECTED LOSS (ANNUAL) ---
    df["Expected_Loss_Annual"] = df["TIV"] * df["Fire_Prob"] * df["MDR_Est"]
    
    # --- METRIC: NET UNDERWRITING GAP ---
    df["Underwriting_Gap"] = df["Expected_Loss_Annual"] - df["Annual_Premium"]

    return df

# --- SIDEBAR ---
st.sidebar.header("Campaign Constraints")
budget_count = st.sidebar.slider("Campaign Target Size (Homes)", 50, 500, 200)

df = generate_portfolio()

# --- 2. STRATEGY LOGIC ---
df["Rank_Risk"] = df["Expected_Loss_Annual"]
df["Rank_Random"] = np.random.rand(len(df))

# --- 3. RUN SIMULATION ---
def evaluate_campaign(rank_col, name):
    campaign = df.sort_values(rank_col, ascending=False).head(budget_count)
    return {
        "Name": name,
        "Total Risk Targeted": campaign["Expected_Loss_Annual"].sum(),
        "Total Gap Targeted": campaign["Underwriting_Gap"].sum(),
        "Selection": campaign
    }

res_faura = evaluate_campaign("Rank_Risk", "Faura Risk Prioritized")
res_rand  = evaluate_campaign("Rank_Random", "Random Outreach (Control)")

# --- 4. DASHBOARD METRICS ---
st.subheader("📊 The Value of Data Screening")
c1, c2, c3, c4 = st.columns(4)

# Calculate Lifts
risk_diff = res_faura["Total Risk Targeted"] - res_rand["Total Risk Targeted"]
risk_lift_pct = (risk_diff / res_rand["Total Risk Targeted"]) * 100

c1.metric("Gross Risk Targeted (Faura)", f"${res_faura['Total Risk Targeted']:,.0f}", delta=f"+{risk_lift_pct:.0f}% vs Random")
c2.metric("Gross Risk Targeted (Random)", f"${res_rand['Total Risk Targeted']:,.0f}", delta="Baseline", delta_color="off")
# The explicit dollar differential
c3.metric("Risk Intelligence Value", f"${risk_diff:,.0f}", help="The extra risk exposure captured purely by using Faura's sorting algorithm vs random selection.")
c4.metric("Avg Premium (Target Group)", f"${res_faura['Selection']['Annual_Premium'].mean():,.0f}")

# --- 5. LIFT CHART (GROSS RISK ON Y-AXIS) ---
st.markdown("---")
st.subheader("📈 Risk Capture Curve ($ Exposure)")
st.markdown("This chart shows the **Gross Risk ($)** captured as we target more homes. Notice the massive gap in value between the green line (Faura) and the red line (Random).")

def get_lift_curve(rank_col, name):
    sorted_df = df.sort_values(rank_col, ascending=False).reset_index(drop=True)
    sorted_df["Cum_Risk"] = sorted_df["Expected_Loss_Annual"].cumsum()
    
    # X-Axis calculation
    sorted_df["% Homes Targeted"] = (sorted_df.index + 1) / len(sorted_df)
    sorted_df["Strategy"] = name
    return sorted_df[["% Homes Targeted", "Cum_Risk", "Strategy"]]

lift_data = pd.concat([
    get_lift_curve("Rank_Risk", "Faura Prioritized"),
    get_lift_curve("Rank_Random", "Random Outreach")
])

fig = px.line(lift_data, x="% Homes Targeted", y="Cum_Risk", color="Strategy",
              color_discrete_map={"Faura Prioritized": "#00CC96", "Random Outreach": "#EF553B"})

# Add Budget Cutoff Line
fig.add_vline(x=budget_count/len(df), line_dash="dash", line_color="grey", annotation_text="Pilot Budget")

# Update Y-Axis to show Dollar Format
fig.update_layout(
    height=450, 
    xaxis_tickformat=".0%", 
    yaxis_tickprefix="$", 
    yaxis_title="Cumulative Gross Expected Loss ($)"
)
st.plotly_chart(fig, use_container_width=True)

# --- 6. CAMPAIGN SIMULATION ---
st.markdown("---")
st.subheader(f"📋 Campaign ROI Projection")
st.markdown("""
**Scenario Assumptions:**
* **25%** Engage (PSA Only) $\\to$ Cost: \$30 Outreach + \$50 Incentive
* **15%** Mitigate (PSA + Action) $\\to$ Cost: \$30 Outreach + \$50 PSA + \$300 Incentive
* **60%** No Response $\\to$ Cost: \$30 Outreach Only
""")

# A. Apply Simulation Logic
target_df = res_faura['Selection'].copy()
np.random.seed(99) 

outcomes = ["Status Quo", "MDR Halved", "MDR Quartered"]
multipliers = [1.0, 0.5, 0.25]
# Logic: 15% Mitigate (split 10/5), 85% Status Quo (includes the PSA-only people for risk purposes)
probs = [0.85, 0.10, 0.05] 

target_df["Outcome_Type"] = np.random.choice(outcomes, size=len(target_df), p=probs)
target_df["Loss_Multiplier"] = target_df["Outcome_Type"].replace(dict(zip(outcomes, multipliers)))

# Calculate New Loss
target_df["New_Expected_Loss"] = target_df["Expected_Loss_Annual"] * target_df["Loss_Multiplier"]
target_df["Annual_Savings"] = target_df["Expected_Loss_Annual"] - target_df["New_Expected_Loss"]

# B. Aggregate Savings & ROI (WITH TIERED COSTS)
total_savings = target_df["Annual_Savings"].sum()

# COST BUILD UP
# 1. Screening: All 1000 homes
c_screen = len(df) * screening_cost_per

# 2. Outreach: All Pilot Homes (e.g. 200)
c_outreach = budget_count * outreach_cost_per

# 3. PSA Incentive: 25% of Pilot Homes
c_psa = (budget_count * 0.25) * psa_incentive

# 4. Mitigation Incentive: 15% of Pilot Homes (The 10% + 5% group)
c_mitigation = (budget_count * 0.15) * mitigation_incentive

total_program_cost = c_screen + c_outreach + c_psa + c_mitigation
roi = (total_savings - total_program_cost) / total_program_cost if total_program_cost > 0 else 0

# C. Summary Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Projected Annual Savings", f"${total_savings:,.0f}", help="Reduction in Gross Expected Loss.")
m2.metric("Total Program Cost", f"${total_program_cost:,.0f}", help=f"Screening + Outreach + Performance Incentives")
m3.metric("Net Program ROI", f"{roi:.1f}x", help="Savings / Total Cost")
denom = len(target_df[target_df['Outcome_Type'] != 'Status Quo'])
m4.metric("Avg Savings per Success", f"${total_savings / denom:,.0f}" if denom > 0 else "$0")

# D. Format Table
def format_currency(val):
    if val >= 1_000_000: return f"${val/1_000_000:.2f}M"
    else: return f"${val/1_000:.0f}K"

target_df["Display_TIV"] = target_df["TIV"].apply(format_currency)
target_df["Display_Loss_SQ"] = target_df["Expected_Loss_Annual"].apply(format_currency)
target_df["Display_Loss_New"] = target_df["New_Expected_Loss"].apply(format_currency)
target_df["Display_Prem"] = target_df["Annual_Premium"].apply(format_currency)
target_df["Display_Gap"] = (target_df["Expected_Loss_Annual"] - target_df["Annual_Premium"]).apply(format_currency)
target_df["Display_Prob"] = target_df["Fire_Prob"] * 100

st.dataframe(
    target_df.sort_values("Annual_Savings", ascending=False)[
        ["Policy ID", "Display_TIV", "Display_Prob", "Display_Prem", "Display_Loss_SQ", "Display_Gap", "Outcome_Type", "Display_Loss_New"]
    ],
    column_config={
        "Display_TIV": "TIV",
        "Display_Prob": st.column_config.NumberColumn("Fire Prob", format="%.2f%%"),
        "Display_Prem": "Ann. Premium",
        "Display_Loss_SQ": st.column_config.TextColumn("Gross Expected Loss"),
        "Display_Gap": st.column_config.TextColumn("⚠️ Net Loss Gap", help="Expected Loss - Premium. Positive = Unprofitable."),
        "Outcome_Type": "Simulated Outcome",
        "Display_Loss_New": "New Expected Loss",
    },
    use_container_width=True
)

# E. Download
download_df = target_df.copy()
download_df["Resilience_Score"] = download_df["Resilience_Score"].round(0).astype(int)
download_df["MDR_Est"] = download_df["MDR_Est"].round(2)
download_df["Expected_Loss_Annual"] = download_df["Expected_Loss_Annual"].round(0).astype(int)
download_df["Annual_Premium"] = download_df["Annual_Premium"].round(0).astype(int)
download_df["Underwriting_Gap"] = download_df["Expected_Loss_Annual"] - download_df["Annual_Premium"]

cols_out = ["Policy ID", "TIV", "Fire_Prob", "Resilience_Score", "Expected_Loss_Annual", "Annual_Premium", "Underwriting_Gap", "Outcome_Type", "New_Expected_Loss"]
st.download_button("📥 Download Simulation (CSV)", download_df[cols_out].to_csv(index=False), "faura_simulation.csv")