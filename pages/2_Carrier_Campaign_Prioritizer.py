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
total_homes_count = st.sidebar.number_input("Total Portfolio Size (to Screen)", value=500, min_value=100, step=50)
budget_count = st.sidebar.number_input("Pilot Target Size", value=100, min_value=10, step=10)

# --- FIXED COSTS ---
screening_cost_per = 3.0
outreach_cost_per = 20.0
psa_incentive = 50.0
mitigation_incentive = 300.0

# --- PHILOSOPHY & SCENARIO SECTION ---
st.markdown("### The Pilot Scenario")

c1, c2 = st.columns([2, 1])
with c1:
    st.info(f"""
    1.  Carrier provides a raw list of **{total_homes_count:,} homes** with home address, premium, TIV, and email.
    2.  **(Screening):** We screen *all* {total_homes_count:,} homes at **${screening_cost_per}/address** and rank them by financial vulnerability.
    3.  **(Outreach):** We target the top **{budget_count} homes** with a pilot outreach budget of **${outreach_cost_per}/home**, generating personalized resilience reports with a follow on home-feature survey.
    
    **The "Pay-for-Performance" Funnel:**
    * **25% Engagement:** Homeowners who fill out the home feature survey get **${psa_incentive}**.
    * **15% Mitigation:** Homeowners who mitigate risk that was previously unmitigated get an additional **${mitigation_incentive}**.
    * *Result:* Your budget dollars primarily pay for performance, not just outreach.
    """)
with c2:
    # UPDATED: CREDIBLE RISK MODELING EXPLANATION
    st.markdown(r"""
    **The "Vulnerability" Gap:**
    $$
    \text{Risk} = \text{TIV} \times \underbrace{P(\text{Fire})}_\text{Hazard} \times \underbrace{P(\text{Ignition})}_\text{Vulnerability}
    $$
    * **Hazard (P_Fire):** Probability of Wildfire.
    * **Vulnerability (P_Ignition):** Probability of ignition if Fire occurs.
    """)

# --- 1. DATA GENERATION ---
@st.cache_data
def generate_portfolio(n):
    np.random.seed(42)
    
    # 1. TIV ($250k - $4M Cap)
    tiv = np.random.lognormal(mean=13.5, sigma=0.6, size=n)
    tiv = np.clip(tiv, 250000, 4000000)
    
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
    # Premium Rate (simulated ~0.5%)
    rate = np.random.uniform(0.002, 0.008, size=n)
    df["Annual_Premium"] = df["TIV"] * rate
    
    # P(Ignition)
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

# --- 4. CAMPAIGN ROI SECTION ---
st.markdown("---")
st.subheader(f"📋 Campaign Profitability Projection")
st.caption("Note: Values for TIV, Premium, and Probability below are **simulated** for this demonstration.")
st.markdown("""
**Scenario Assumptions:**
* **85%** Status Quo (Non-Responsive)
* **10%** Reduce P(Ignition) by 50% (Halved)
* **5%** Reduce P(Ignition) by 75% (Quartered)
""")

# A. Apply Simulation Logic
target_df = res_faura['Selection'].copy()
np.random.seed(99) 

outcomes = ["Status Quo", "P(Ignition) Halved", "P(Ignition) Quartered"]
multipliers = [1.0, 0.5, 0.25]
probs = [0.85, 0.10, 0.05] 

target_df["Outcome_Type"] = np.random.choice(outcomes, size=len(target_df), p=probs)
target_df["Loss_Multiplier"] = target_df["Outcome_Type"].replace(dict(zip(outcomes, multipliers)))

# B. Calculate NEW Loss
target_df["New_Expected_Loss"] = target_df["Expected_Loss_Annual"] * target_df["Loss_Multiplier"]
target_df["Annual_Savings"] = target_df["Expected_Loss_Annual"] - target_df["New_Expected_Loss"]

# C. Calculate ROW-LEVEL COST
def calculate_row_cost(outcome):
    base = screening_cost_per + outreach_cost_per 
    if outcome == "Status Quo":
        return base
    else:
        return base + psa_incentive + mitigation_incentive 

target_df["Row_Cost"] = target_df["Outcome_Type"].apply(calculate_row_cost)

# D. Calculate NET Metrics
target_df["Net"] = target_df["Annual_Premium"] - target_df["Expected_Loss_Annual"]
target_df["New Net"] = target_df["Annual_Premium"] - target_df["New_Expected_Loss"] - target_df["Row_Cost"]

# E. Aggregates for Top Cards
total_savings = target_df["Annual_Savings"].sum()
total_program_cost = target_df["Row_Cost"].sum()
roi = (total_savings - total_program_cost) / total_program_cost if total_program_cost > 0 else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Projected Annual Savings", f"${total_savings:,.0f}")
m2.metric("Total Program Cost", f"${total_program_cost:,.0f}", help="Sum of screening, outreach, and incentives based on outcomes.")
m3.metric("Net Program ROI", f"{roi:.1f}x")
denom = len(target_df[target_df['Outcome_Type'] != 'Status Quo'])
m4.metric("Avg Savings per Success", f"${total_savings / denom:,.0f}" if denom > 0 else "$0")

# F. PREPARE DISPLAY TABLE (Styling)
display_cols = [
    "Policy ID", "TIV", "Annual_Premium", "Fire_Prob", "Susceptibility", 
    "Expected_Loss_Annual", "Net", "Outcome_Type", "New_Expected_Loss", "New Net"
]
style_df = target_df[display_cols].copy()

style_df.columns = [
    "Policy ID", "TIV", "Annual Premium", "P(Fire)", "P(Ignition)", 
    "Gross Expected Loss", "Net", "Outcome", "New Expected Loss", "New Net"
]

def fmt_currency(x):
    if abs(x) >= 1_000_000:
        return f"${x/1_000_000:.2f}M"
    elif abs(x) >= 1_000:
        return f"${x/1_000:.0f}K"
    else:
        return f"${x:,.0f}"

def color_net(val):
    color = '#ff4b4b' if val < 0 else '#09ab3b' # Red/Green
    return f'color: {color}'

st.dataframe(
    style_df.style
    .format({
        "TIV": fmt_currency,
        "Annual Premium": fmt_currency,
        "Gross Expected Loss": fmt_currency,
        "Net": fmt_currency,
        "New Expected Loss": fmt_currency,
        "New Net": fmt_currency,
        "P(Fire)": "{:.4f}",
        "P(Ignition)": "{:.2f}"
    })
    .map(color_net, subset=["Net", "New Net"]),
    use_container_width=True,
    height=500
)

# G. Download Logic
download_df = target_df.copy()
download_df["Fire_Prob"] = download_df["Fire_Prob"].round(4)
download_df["Susceptibility"] = download_df["Susceptibility"].round(2)
download_df = download_df.round(0)

cols_out = ["Policy ID", "TIV", "Fire_Prob", "Susceptibility", "Expected_Loss_Annual", "Annual_Premium", "Net", "Outcome_Type", "New_Expected_Loss", "Row_Cost", "New Net"]
st.download_button("📥 Download Simulation (CSV)", download_df[cols_out].to_csv(index=False), "faura_simulation.csv")

# --- 5. ANALYTICS SECTION ---
st.markdown("---")
st.subheader("📊 Deep Dive: The Value of Data Screening")

c1, c2, c3, c4 = st.columns(4)
risk_diff = res_faura["Total Risk Targeted"] - res_rand["Total Risk Targeted"]
risk_lift_pct = (risk_diff / res_rand["Total Risk Targeted"]) * 100 if res_rand["Total Risk Targeted"] > 0 else 0

c1.metric("Gross Risk Targeted (Faura)", f"${res_faura['Total Risk Targeted']:,.0f}", delta=f"+{risk_lift_pct:.0f}% vs Random")
c2.metric("Gross Risk Targeted (Random)", f"${res_rand['Total Risk Targeted']:,.0f}", delta="Baseline", delta_color="off")
c3.metric("Risk Intelligence Value", f"${risk_diff:,.0f}", help="The extra risk exposure captured purely by using Faura's sorting algorithm vs random selection.")
c4.metric("Avg Premium (Target Group)", f"${res_faura['Selection']['Annual_Premium'].mean():,.0f}")

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