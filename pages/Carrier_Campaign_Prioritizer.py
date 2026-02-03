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

# --- PHILOSOPHY & ALGORITHM SECTION ---
st.markdown("### The Pilot Scenario")
c1, c2 = st.columns([2, 1])
with c1:
    st.info("""
    **The Constraints:**
    1.  Carrier provides a raw list of **1,000 homes**.
    2.  Budget allows for a pilot on only **200 homes** (at ~$150/home).
    
    **The Faura Strategy:**
    3.  We target homes with the **Highest Gross Risk** (Expected Loss) first.
    4.  **Result:** We avoid wasting pilot budget on "Profitable" homes (where Premium > Loss) or low-probability events, maximizing the ROI of the $30k pilot spend.
    """)
with c2:
    st.markdown("""
    **The Algorithm:**
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
    
    # --- METRIC: ANNUAL PREMIUM (The "Revenue") ---
    # Logic: Premiums in CA are often "suppressed" relative to risk.
    # We simulate a rate of ~0.2% to 0.8% of TIV (often lower than the actual risk).
    rate = np.random.uniform(0.002, 0.008, size=n)
    df["Annual_Premium"] = df["TIV"] * rate
    
    # --- METRIC: ESTIMATED MDR (Mean Damage Ratio) ---
    df["MDR_Est"] = ((100 - df["Resilience_Score"]) / 100).clip(lower=0.10)

    # --- METRIC: GROSS EXPECTED LOSS (ANNUAL) ---
    df["Expected_Loss_Annual"] = df["TIV"] * df["Fire_Prob"] * df["MDR_Est"]
    
    # --- METRIC: NET UNDERWRITING GAP ---
    # Gap = Loss - Premium. 
    # Positive = Unprofitable (Bleeding Money). Negative = Profitable.
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
st.subheader("📊 Prioritization Impact")
c1, c2, c3, c4 = st.columns(4)

risk_lift = (res_faura["Total Risk Targeted"] - res_rand["Total Risk Targeted"])
risk_lift_pct = (risk_lift / res_rand["Total Risk Targeted"]) * 100

c1.metric("Gross Risk Targeted", f"${res_faura['Total Risk Targeted']:,.0f}", delta=f"+{risk_lift_pct:.0f}% Lift")
c2.metric("Net Underwriting Gap", f"${res_faura['Total Gap Targeted']:,.0f}", help="The total 'Profitability Bleed' (Loss - Premium) in this target group.")
c3.metric("Avg Premium per Home", f"${res_faura['Selection']['Annual_Premium'].mean():,.0f}")
c4.metric("Campaign Size", f"{budget_count} Homes")

# --- 5. LIFT CHART ---
st.markdown("---")
st.subheader("📈 Risk Capture Curve")

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
              color_discrete_map={"Faura Prioritized": "#00CC96", "Random Outreach": "#EF553B"})
fig.add_vline(x=budget_count/len(df), line_dash="dash", line_color="grey", annotation_text="Budget Cutoff")
fig.update_layout(height=400, xaxis_tickformat=".0%", yaxis_tickformat=".0%")
st.plotly_chart(fig, use_container_width=True)

# --- 6. CAMPAIGN SIMULATION ---
st.markdown("---")
st.subheader(f"📋 Campaign Projection (Simulated Results)")
st.markdown("""
**Scenario Assumptions:**
* **85%** Non-Responsive (Status Quo)
* **10%** Reduce MDR by 50% (Halved)
* **5%** Reduce MDR by 75% (Quartered)
""")

# A. Apply Simulation Logic
target_df = res_faura['Selection'].copy()
np.random.seed(99) 

outcomes = ["Status Quo", "MDR Halved", "MDR Quartered"]
multipliers = [1.0, 0.5, 0.25]
probs = [0.85, 0.10, 0.05]

target_df["Outcome_Type"] = np.random.choice(outcomes, size=len(target_df), p=probs)
target_df["Loss_Multiplier"] = target_df["Outcome_Type"].replace(dict(zip(outcomes, multipliers)))

# Calculate New Loss
target_df["New_Expected_Loss"] = target_df["Expected_Loss_Annual"] * target_df["Loss_Multiplier"]
target_df["Annual_Savings"] = target_df["Expected_Loss_Annual"] - target_df["New_Expected_Loss"]

# B. Aggregate Savings
total_savings = target_df["Annual_Savings"].sum()
program_cost = budget_count * 150 
roi = (total_savings - program_cost) / program_cost if program_cost > 0 else 0

# C. Summary Metrics
m1, m2, m3, m4 = st.columns(4)
m1.metric("Projected Annual Savings", f"${total_savings:,.0f}", help="Reduction in Gross Expected Loss.")
m2.metric("Program ROI", f"{roi:.1f}x", help="Based on $150 engagement cost.")
m3.metric("Homes Improved", f"{len(target_df[target_df['Outcome_Type'] != 'Status Quo'])}")
denom = len(target_df[target_df['Outcome_Type'] != 'Status Quo'])
m4.metric("Avg Savings per Success", f"${total_savings / denom:,.0f}" if denom > 0 else "$0")

# D. Format Table (Sort First, Then Format)
def format_currency(val):
    if val >= 1_000_000: return f"${val/1_000_000:.2f}M"
    else: return f"${val/1_000:.0f}K"

target_df["Display_TIV"] = target_df["TIV"].apply(format_currency)
target_df["Display_Loss_SQ"] = target_df["Expected_Loss_Annual"].apply(format_currency)
target_df["Display_Loss_New"] = target_df["New_Expected_Loss"].apply(format_currency)
target_df["Display_Prem"] = target_df["Annual_Premium"].apply(format_currency)
target_df["Display_Prob"] = target_df["Fire_Prob"] * 100

# NEW: Calculate Net Loss Gap (Loss - Premium) for display
target_df["Display_Gap"] = (target_df["Expected_Loss_Annual"] - target_df["Annual_Premium"]).apply(format_currency)

st.dataframe(
    target_df.sort_values("Annual_Savings", ascending=False)[
        ["Policy ID", "Display_TIV", "Display_Prob", "Display_Prem", "Display_Loss_SQ", "Display_Gap", "Outcome_Type", "Display_Loss_New"]
    ],
    column_config={
        "Display_TIV": "TIV",
        "Display_Prob": st.column_config.NumberColumn("Fire Prob", format="%.2f%%"),
        "Display_Prem": "Ann. Premium",
        "Display_Loss_SQ": st.column_config.TextColumn("Gross Expected Loss"),
        "Display_Gap": st.column_config.TextColumn("⚠️ Net Loss Gap", help="Expected Loss - Premium. Positive numbers mean the policy is losing money."),
        "Outcome_Type": "Simulated Outcome",
        "Display_Loss_New": "New Expected Loss",
    },
    use_container_width=True
)

# E. Download
download_df = target_df.copy()
# Rounding for clean CSV
download_df["Resilience_Score"] = download_df["Resilience_Score"].round(0).astype(int)
download_df["MDR_Est"] = download_df["MDR_Est"].round(2)
download_df["Expected_Loss_Annual"] = download_df["Expected_Loss_Annual"].round(0).astype(int)
download_df["Annual_Premium"] = download_df["Annual_Premium"].round(0).astype(int)
download_df["Underwriting_Gap"] = download_df["Expected_Loss_Annual"] - download_df["Annual_Premium"]

cols_out = ["Policy ID", "TIV", "Fire_Prob", "Resilience_Score", "Expected_Loss_Annual", "Annual_Premium", "Underwriting_Gap", "Outcome_Type", "New_Expected_Loss"]
st.download_button("📥 Download Simulation (CSV)", download_df[cols_out].to_csv(index=False), "faura_simulation.csv")