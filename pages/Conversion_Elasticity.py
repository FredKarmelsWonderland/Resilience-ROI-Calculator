import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- PASSWORD PROTECTION ---
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        if st.session_state["password"] == "Faura2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.text_input("Please enter the Sales Access Password", type="password", on_change=password_entered, key="password")
        return False
    else:
        return True

if not check_password():
    st.stop()

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="MDR Scenario Modeling", layout="wide")

st.title("📉 Resilience Scenarios: The 'Tale of Two Cities'")
st.markdown("""
**Historical Benchmarking:** Not all fires result in total loss. 
This tool models your portfolio's performance based on **real-world disaster scenarios**, demonstrating how community resilience (building codes, defensible space) acts as a cap on severity (MDR).
""")

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Portfolio Inputs")
n_homes = st.sidebar.number_input("Number of Homes", value=1000, step=100)
avg_premium = st.sidebar.number_input("Avg Premium ($)", value=10000, step=100)
avg_tiv = st.sidebar.number_input("Avg TIV ($)", value=1000000, step=100000)
expense_ratio = st.sidebar.number_input("Expense Ratio (%)", value=15.0, step=0.1, format="%.2f") / 100

st.sidebar.markdown("---")
st.sidebar.header("2. Faura Program")
faura_cost = st.sidebar.number_input("Faura Cost per Home ($)", value=30)
conversion_rate = st.sidebar.slider("Faura Conversion Rate (%)", 0, 50, 20) / 100
incentives = st.sidebar.number_input("Total Incentives ($)", value=600)

# --- SCENARIO DATABASE (The Narrative Engine) ---
# We define specific fires as "Archetypes" of resilience
scenarios = {
    "Camp Fire (Paradise)": {
        "MDR": 0.90,
        "Description": "Low Resilience: Older stock, unmitigated WUI.",
        "Faura_Score_Proxy": "20-30",
        "Color": "#8B0000" # Dark Red
    },
    "Tubbs Fire (Santa Rosa)": {
        "MDR": 0.65,
        "Description": "Mixed Resilience: Urban interface with varying mitigation.",
        "Faura_Score_Proxy": "40-50",
        "Color": "#FF4500" # Orange Red
    },
    "Marshall Fire (Boulder)": {
        "MDR": 0.45,
        "Description": "Suburban Density: High spread, but modern suppression access.",
        "Faura_Score_Proxy": "50-60",
        "Color": "#FFD700" # Gold
    },
    "Silverado Fire (Irvine)": {
        "MDR": 0.15,
        "Description": "High Resilience: Master-planned, hardened structures, fuel breaks.",
        "Faura_Score_Proxy": "80-90",
        "Color": "#228B22" # Forest Green
    }
}

st.sidebar.markdown("---")
st.sidebar.header("3. Select Historical Benchmark")
selected_scenario_name = st.sidebar.selectbox("Simulate Event Severity:", list(scenarios.keys()))
scenario_data = scenarios[selected_scenario_name]
current_mdr = scenario_data["MDR"]

# --- CALCULATION LOGIC ---
# We assume Faura shifts the converted homes "Down the Ladder" 
# For simplicity in this demo, we assume mitigated homes perform 50% better than the scenario baseline
# or hit a "Resilience Floor" of 10% MDR.
mitigated_mdr = max(0.10, current_mdr * 0.5) 

# Incident Probability is fixed for the event simulation (It happened)
incident_prob = 1.0 # The fire IS happening in this model

def calculate_impact():
    # FINANCIALS
    sq_losses = n_homes * avg_tiv * incident_prob * current_mdr
    
    # With Faura
    n_converted = n_homes * conversion_rate
    n_unconverted = n_homes * (1 - conversion_rate)
    
    # Unconverted homes suffer the full Scenario MDR
    loss_unconverted = n_unconverted * avg_tiv * incident_prob * current_mdr
    # Converted homes suffer the Improved MDR
    loss_converted = n_converted * avg_tiv * incident_prob * mitigated_mdr
    
    faura_losses = loss_unconverted + loss_converted
    program_cost = (n_homes * faura_cost) + (n_converted * incentives)
    
    saved_losses = sq_losses - faura_losses
    net_benefit = saved_losses - program_cost
    
    return sq_losses, faura_losses, saved_losses, net_benefit, program_cost

sq_loss, faura_loss, saved, net, cost = calculate_impact()

# --- DASHBOARD HEADER ---
st.info(f"""
**Benchmark: {selected_scenario_name}** 📝 *{scenario_data['Description']}* 🔹 **Implied Resilience Score:** {scenario_data['Faura_Score_Proxy']} | 🔹 **Base MDR:** {current_mdr*100:.0f}%
""")

# --- METRICS ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Status Quo Loss", f"${sq_loss:,.0f}")
with col2:
    st.metric("Loss Avoided (Claims Saved)", f"${saved:,.0f}", delta="Money Saved")
with col3:
    st.metric("Net ROI (after Program Costs)", f"${net:,.0f}")

# --- CHARTING ---
fig = go.Figure()

# 1. Comparison Bar Chart
fig.add_trace(go.Bar(
    x=["Status Quo Loss", "Loss with Faura"],
    y=[sq_loss, faura_loss],
    marker_color=[scenario_data['Color'], '#4B604D'],
    text=[f"${sq_loss:,.0f}", f"${faura_loss:,.0f}"],
    textposition='auto',
    textfont=dict(size=18, color="white")
))

fig.update_layout(
    title=f"Impact of Resilience on {selected_scenario_name} Scenario",
    yaxis_title="Total Aggregate Loss ($)",
    template="plotly_white",
    height=500
)

st.plotly_chart(fig, use_container_width=True)

# --- NARRATIVE SECTION ---
st.markdown("### 🧠 The Resilience Thesis")
st.markdown(f"""
This model answers the question: ***"What if we had {conversion_rate*100:.0f}% adoption during the {selected_scenario_name}?"***

1.  **The "Camp Fire" Standard (Status Quo):** Without verified mitigation, homes are assumed to be highly fragile, leading to the **{current_mdr*100:.0f}% MDR** seen in the status quo bar.
2.  **The "Silverado" Effect (Mitigation):** By validating defensible space and structural hardening (Faura's Core Product), we effectively shift the converted portion of your portfolio toward the resilience profile of Irvine, CA.
3.  **The Result:** Even in a catastrophic event scenario like **{selected_scenario_name}**, the {int(n_homes*conversion_rate)} converted homes resist total destruction, saving **${saved:,.0f}** in claims.
""")