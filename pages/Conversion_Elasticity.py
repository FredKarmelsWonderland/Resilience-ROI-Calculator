import streamlit as st
import pandas as pd
import numpy as np
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
st.set_page_config(page_title="Conversion Elasticity", layout="wide")

st.title("📈 Faura Conversion Elasticity Analysis")
st.markdown("""
**The "Partnership Steps":** This chart compares the portfolio profitability at specific milestones of homeowner adoption.
It answers: *"How much new profit do we unlock if we get to 20%, 40%, or 60% participation?"*
""")

# --- HELPER FUNCTION ---
def currency_input(label, default_value, tooltip=None):
    user_input = st.sidebar.text_input(label, value=f"${default_value:,.0f}", help=tooltip)
    try:
        clean_val = float(user_input.replace('$', '').replace(',', '').strip())
    except ValueError:
        clean_val = default_value
        st.sidebar.error(f"Please enter a valid number for {label}")
    return clean_val

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Portfolio Inputs")
n_homes = st.sidebar.number_input("Number of Homes", value=1000, step=100)
avg_premium = currency_input("Avg Premium per Home", 2500)
avg_tiv = currency_input("Avg TIV per Home", 1000000)
expense_ratio = st.sidebar.number_input("Expense Ratio (%)", value=20.0, step=0.1, format="%.2f") / 100

st.sidebar.markdown("---")
st.sidebar.header("2. Risk Inputs")
incident_prob = st.sidebar.number_input("Annual Incident Prob (%)", value=1.0, step=0.01, format="%.2f") / 100
mdr_unmitigated = st.sidebar.number_input("MDR (Unmitigated) %", value=80.0, step=0.1) / 100
mdr_mitigated = st.sidebar.number_input("MDR (Mitigated) %", value=30.0, step=0.1) / 100

st.sidebar.markdown("---")
st.sidebar.header("3. Faura Program Inputs")
faura_cost = currency_input("Faura Cost per Home", 30)
st.sidebar.info("ℹ️ Conversion Rate is the variable we are testing (0% - 100%)")
gift_card = currency_input("Gift Card Incentive", 50)
premium_discount = currency_input("Premium Discount", 100)

# --- CALCULATION LOGIC ---
def calculate_scenario(rate):
    # Constant Status Quo
    sq_losses = n_homes * avg_tiv * incident_prob * mdr_unmitigated
    sq_expenses = n_homes * avg_premium * expense_ratio
    sq_profit = (n_homes * avg_premium) - sq_expenses - sq_losses
    
    # Faura Logic
    total_incentives_per_conversion = gift_card + premium_discount
    n_converted = n_homes * rate
    n_unconverted = n_homes * (1 - rate)
    
    loss_unconverted = n_unconverted * avg_tiv * incident_prob * mdr_unmitigated
    loss_converted = n_converted * avg_tiv * incident_prob * mdr_mitigated
    
    program_fees = n_homes * faura_cost
    incentive_costs = n_converted * total_incentives_per_conversion
    
    faura_profit = (n_homes * avg_premium) - sq_expenses - (loss_unconverted + loss_converted) - program_fees - incentive_costs
    
    return sq_profit, faura_profit

# --- 1. CALCULATE EXACT BREAKEVEN (Background Math) ---
# We still run the detailed math to find the exact "Breakeven %" for the metrics
x_range = np.linspace(0, 1, 1001)
breakeven_text = "Never"
for r in x_range:
    sq, faura = calculate_scenario(r)
    if faura > sq:
        breakeven_text = f"{r*100:.1f}%"
        break

# --- 2. CALCULATE BAR CHART DATA (Discrete Buckets) ---
buckets = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]
labels = ["0%", "20%", "40%", "60%", "80%", "100%"]
sq_data = []
faura_data = []
deltas = []

for b in buckets:
    sq, faura = calculate_scenario(b)
    sq_data.append(sq)
    faura_data.append(faura)
    deltas.append(faura - sq)

# --- METRICS ROW ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Breakeven Conversion Rate", breakeven_text)
with col2:
    idx_20 = 1 # Index of 20% in our buckets list
    st.metric("Net Benefit at 20% Conversion", f"${deltas[idx_20]:,.0f}")
with col3:
    st.metric("Max Potential Benefit (100%)", f"${deltas[-1]:,.0f}")

# --- BAR CHART ---
fig = go.Figure()

# Status Quo Bars
fig.add_trace(go.Bar(
    name='Status Quo',
    x=labels,
    y=sq_data,
    marker_color='#EF553B',
    opacity=0.6 # Make it slightly lighter so Faura pops
))

# Faura Bars
fig.add_trace(go.Bar(
    name='With Faura',
    x=labels,
    y=faura_data,
    marker_color='#4B604D',
    text=[f"${x:,.0f}" for x in faura_data],
    textposition='auto',
    textfont=dict(size=14, color="white")
))

# Annotations for Net Benefit (The Deltas)
for i, delta in enumerate(deltas):
    # Only show annotation if there is a visible difference
    if abs(delta) > 100: 
        max_height = max(sq_data[i], faura_data[i])
        color = "green" if delta > 0 else "red"
        sign = "+" if delta > 0 else ""
        
        fig.add_annotation(
            x=labels[i],
            y=max_height,
            text=f"<b>{sign}${delta:,.0f}</b>",
            showarrow=False,
            yshift=25,
            font=dict(size=16, color=color)
        )

fig.update_layout(
    title="Net Profit by Conversion Milestone",
    xaxis_title="Conversion Rate (%)",
    yaxis_title="Total Portfolio Profit ($)",
    barmode='group',
    template="plotly_white",
    height=600,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# --- EXPLANATION ---
st.info("""
**How to interpret this:**
* **0% Column:** This shows the upfront cost. Since we pay the fixed fee but get no risk reduction, the Green bar is lower than Red.
* **The Turnaround:** Look for the column where the Green bar overtakes the Red bar. That is your profit zone.
* **The Delta:** The number floating above each bar represents the **Net Profit Gain** compared to doing nothing.
""")