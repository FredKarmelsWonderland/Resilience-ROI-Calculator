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

# --- SIDEBAR: DYNAMIC INPUTS ---
st.sidebar.header("Simulation Parameters")

st.sidebar.subheader("1. Portfolio Scope")
# Updated per user snippet (Min 100 to prevent crash)
total_homes_count = st.sidebar.slider("Total Portfolio Size (to Screen)", 100, 1000, 100, step=100)
budget_count = st.sidebar.slider("Pilot Target Size", 10, 1000, 100, step=10)

# --- FIXED COSTS ---
screening_cost_per = 3.0
outreach_cost_per = 30.0
psa_incentive = 50.0
mitigation_incentive = 300.0

# --- PHILOSOPHY & SCENARIO SECTION ---
st.markdown("### The Pilot Scenario")

c1, c2 = st.columns([2, 1])
with c1:
    # UPDATED TEXT SNIPPET
    st.info(f"""
    1.  Carrier provides a raw list of **{total_homes_count:,} homes** with address, premium, TIV.
    2.  **Step 1 (Screening):** We screen *all* {total_homes_count:,} homes at **${screening_cost_per}/address** to algorithmically generate our ranking/targeting funnel.
    3.  **Step 2 (Outreach):** We target the top **{budget_count} homes** with a pilot outreach budget of **${outreach_cost_per}/home**, generating personalized resilience reports with a follow on home-feature survey.
    
    **The "Pay-for-Performance" Funnel:**
    * **25% Engagement:** Homeowners who fill out the home feature survey get **${psa_incentive}**.
    * **15% Mitigation:** Homeowners who mitigate risk that was previously unmitigated get an additional **${mitigation_incentive}**.
    * *Result:* Your budget dollars primarily pay for performance, not just outreach.
    """)
with c2:
    st.markdown(r"""
    **The "Ignition" Algorithm:**
    $$
    \text{Risk} = \text{TIV} \times P(\text{Fire}) \times P(\text{Ignition})
    $$
    *Most carriers assume Ignition is 100%.*
    *Faura calculates specific Susceptibility via QA Score.*
    """)

# --- 1. DATA GENERATION ---
@st.cache_data
def generate_portfolio(n):
    np.random.seed(42)
    
    # 1. TIV ($250k - $5M)
    tiv = np.random.lognormal(mean=13.5, sigma=0.6, size=n)
    tiv = np.clip(tiv, 250000, 5000000)
    
    # 2. Fire Probability (0.1% to 2.5%)
    prob_fire = np.random.beta(2, 50, size=n) 
    prob_fire = np.clip(prob_fire, 0.001, 0.025)
    
    # 3. Resilience Score
    qa_score = np.random.normal(60, 15, size=n)
    qa_score = np.clip(qa_score, 10, 95)
    
    df = pd.DataFrame({
        "Policy ID": [f"POL-{i:04d}" for i in range(n)],
        "TIV": tiv,
        "Fire_Prob": prob_fire,
        "Resilience_Score": qa_score,
    })
    
    # --- METRICS ---
    rate = np.random.uniform(0.002, 0.008, size=n)
    df["Annual_Premium"] = df["TIV"] * rate
    
    # Susceptibility Factor (100 - Score)
    df["Susceptibility"] = ((100 - df["Resilience_Score"]) / 100).clip(lower=0.10)
    
    # Gross Expected Loss
    df["Expected_Loss_Annual"] = df["TIV"] * df["Fire_Prob"] * df["Susceptibility"]
    df["Underwriting_Gap"] = df["Expected_Loss_Annual"] - df["Annual_Premium"]

    return df

df = generate_portfolio(total_homes_count)

# --- 2. STRATEGY LOGIC ---
df["Rank_Risk"] = df["Expected_Loss_Annual"]
df["Rank_Random"] = np.random.rand(len(df))

# --- 3. RUN SIMULATION ---
def evaluate_campaign(rank_col, name):
    # Safe slicing in case budget > total
    safe_budget = min(budget_count, len(df))
    campaign = df.sort_values(rank_col, ascending=False).head(safe_budget)
    return {
        "Name": name,
        "Total Risk Targeted": campaign["Expected_Loss_Annual"].sum(),
        "Total Gap Targeted": campaign["Underwriting_Gap"].sum(),
        "Selection": campaign
    }

res_faura = evaluate_campaign("Rank_Risk", "Faura Risk Prioritized")
res_rand  = evaluate_campaign("Rank_Random", "Random Outreach (Control)")

# --- 4. CAMPAIGN ROI SECTION (MOVED UP) ---
st.markdown("---")
st.subheader(f"📋 Campaign ROI Projection")
st.markdown("""
**Scenario Assumptions:**
* **85%** Status Quo (Non-Responsive)
* **10%** Reduce Susceptibility by 50% (Halved Ignition Prob.)
* **5%** Reduce Susceptibility by 75% (Quartered Ignition Prob.)
""")

# A. Apply Simulation Logic
target_df = res_faura['Selection'].copy()
np.random.seed(99) 

outcomes = ["Status Quo", "Susceptibility Halved", "Susceptibility Quartered"]
multipliers = [1.0, 0.5, 0.25]
probs = [0.85, 0.10, 0.05] 

target_df["Outcome_Type"] = np.random.choice(outcomes, size=len(target_df), p=probs)
target_df["Loss_Multiplier"] = target_df["Outcome_Type"].replace(dict(zip(outcomes, multipliers)))
target_df["New_Expected_Loss"] = target_df["Expected_Loss_Annual"] * target_df["Loss_Multiplier"]
target_df["Annual_Savings"] = target_df["Expected_Loss_Annual"] - target_df["New_Expected_Loss"]

# B. Aggregate Savings & ROI (Fixed Cost Model)
total_savings = target_df["Annual_Savings"].sum()

# COST CALCULATION
# 1. Screening: All Homes
c_screen = len(df) * screening_cost_per
# 2. Outreach: Target Homes (Fixed Fee)
c_engage = len(target_df) * outreach_cost_per
# 3. Incentives
c_psa = (len(target_df) * 0.25) * psa_incentive
c_mitigation = (len(target_df) * 0.15) * mitigation_incentive

total_program_cost = c_screen + c_engage + c_psa + c_mitigation

roi = (total_savings - total_program_cost) / total_program_cost if total_program_cost > 0 else 0

# C. Summary Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Projected Annual Savings", f"${total_savings:,.0f}")
m2.metric("Total Program Cost", f"${total_program_cost:,.0f}", help=f"Screening + Outreach + Incentives")
m3.metric("Net Program ROI", f"{roi:.1f}x")
denom = len(target_df[target_df['Outcome_Type'] != 'Status Quo'])
m4.metric("Avg Savings per Success", f"${total_savings / denom:,.0f}" if denom > 0 else "$0")

# D. Formatting Helpers
def format_currency_csv(val):
    if val >= 1_000_000: return f"${val/1_000_000:.2f}M"
    elif val >= 1000: return f"${val/1000:.0f}K"
    else: return f"${val:.0f}"

def format_pct_csv(val):
    return f"{val*100:.2f}%"

# E. Display Table
target_df["Display_TIV"] = target_df["TIV"].apply(format_currency_csv)
target_df["Display_Loss_SQ"] = target_df["Expected_Loss_Annual"].apply(format_currency_csv)
target_df["Display_Loss_New"] = target_df["New_Expected_Loss"].apply(format_currency_csv)
target_df["Display_Prem"] = target_df["Annual_Premium"].apply(format_currency_csv)
target_df["Display_Gap"] = (target_df["Expected_Loss_Annual"] - target_df["Annual_Premium"]).apply(format_currency_csv)
target_df["Display_Prob"] = (target_df["Fire_Prob"] * 100).map("{:.2f}%".format)
target_df["Display_Ignition"] = target_df["Susceptibility"].map("{:.2f}".format)

st.dataframe(
    target_df.sort_values("Annual_Savings", ascending=False)[
        ["Policy ID", "Display_TIV", "Display_Prob", "Display_Ignition", "Display_Loss_SQ", "Display_Prem", "Display_Gap", "Outcome_Type", "Display_Loss_New"]
    ],
    column_config={
        "Display_TIV": "TIV",
        "Display_Prob": "P(Fire)",
        "Display_Ignition": "P(Ignition)",
        "Display_Loss_SQ": "Gross Expected Loss",
        "Display_Prem": "Annual Premium",
        "Display_Gap": "Net Loss Gap",
        "Display_Loss_New": "New Expected Loss",
    },
    use_container_width=True
)

# E. Download Logic
download_df = target_df.copy()
download_df["TIV"] = download_df["TIV"].apply(format_currency_csv)
download_df["Expected_Loss_Annual"] = download_df["Expected_Loss_Annual"].apply(format_currency_csv)
download_df["Annual_Premium"] = download_df["Annual_Premium"].apply(format_currency_csv)
download_df["New_Expected_Loss"] = download_df["New_Expected_Loss"].apply(format_currency_csv)
download_df["Annual_Savings"] = download_df["Annual_Savings"].apply(format_currency_csv)
download_df["Fire_Prob"] = download_df["Fire_Prob"].apply(format_pct_csv)
download_df["Susceptibility"] = download_df["Susceptibility"].round(2)

cols_out = ["Policy ID", "TIV", "Fire_Prob", "Susceptibility", "Expected_Loss_Annual", "Annual_Premium", "Outcome_Type", "New_Expected_Loss", "Annual_Savings"]
st.download_button("📥 Download Simulation (CSV)", download_df[cols_out].to_csv(index=False), "faura_simulation.csv")

# --- 5. "WHY THIS WORKS" SECTION (MOVED DOWN) ---
st.markdown("---")
st.subheader("📊 Deep Dive: The Value of Data Screening")
st.markdown("*Why not just randomly select homes? Because risk is not evenly distributed.*")

c1, c2, c3, c4 = st.columns(4)

risk_diff = res_faura["Total Risk Targeted"] - res_rand["Total Risk Targeted"]
risk_lift_pct = (risk_diff / res_rand["Total Risk Targeted"]) * 100 if res_rand["Total Risk Targeted"] > 0 else 0

c1.metric("Gross Risk Targeted (Faura)", f"${res_faura['Total Risk Targeted']:,.0f}", delta=f"+{risk_lift_pct:.0f}% vs Random")
c2.metric("Gross Risk Targeted (Random)", f"${res_rand['Total Risk Targeted']:,.0f}", delta="Baseline", delta_color="off")
c3.metric("Risk Intelligence Value", f"${risk_diff:,.0f}", help="The extra risk exposure captured purely by using Faura's sorting algorithm vs random selection.")
c4.metric("Avg Premium (Target Group)", f"${res_faura['Selection']['Annual_Premium'].mean():,.0f}")

# Lift Chart
def get_lift_curve(rank_col, name):
    sorted_df = df.sort_values(rank_col, ascending=False).reset_index(drop=True)
    sorted_df["Cum_Risk"] = sorted_df["Expected_Loss_Annual"].cumsum()
    sorted_df["% Homes Targeted"] = (sorted_df.index + 1) / len(sorted_df)
    sorted_df["Strategy"] = name
    return sorted_df[["% Homes Targeted", "Cum_Risk", "Strategy"]]

lift_data = pd.concat([
    get_lift_curve("Rank_Risk", "Faura Prioritized"),
    get_lift_curve("Rank_Random", "Random Outreach")
])

fig = px.line(lift_data, x="% Homes Targeted", y="Cum_Risk", color="Strategy",
              color_discrete_map={"Faura Prioritized": "#00CC96", "Random Outreach": "#EF553B"})

fig.add_vline(x=budget_count/len(df), line_dash="dash", line_color="grey", annotation_text="Pilot Budget")
fig.update_layout(height=450, xaxis_tickformat=".0%", yaxis_tickprefix="$", yaxis_title="Cumulative Gross Expected Loss ($)")
st.plotly_chart(fig, use_container_width=True)