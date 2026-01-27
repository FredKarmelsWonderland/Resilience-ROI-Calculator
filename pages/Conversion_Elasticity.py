import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import numpy as np

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Conversion Elasticity", layout="wide")

st.title("📈 Conversion Elasticity Analysis")
st.markdown("""
**The "Partnership Curve":** This chart demonstrates why higher conversion rates drive exponential value for the carrier.
It answers: *"At what participation rate does the program pay for itself?"* and *"How much profit do we gain for every 10% increase in adoption?"*
""")

# --- SIDEBAR INPUTS ---
st.sidebar.header("1. Portfolio Inputs")
n_homes = st.sidebar.number_input("Number of Homes", value=1000, step=100)
avg_premium = st.sidebar.number_input("Avg Premium ($)", value=2500, step=100)
avg_tiv = st.sidebar.number_input("Avg TIV ($)", value=1000000, step=100000)

# Financial Inputs
expense_ratio = st.sidebar.slider("Expense Ratio (%)", 0, 40, 15) / 100

st.sidebar.markdown("---")
st.sidebar.header("2. Risk Inputs")
incident_prob = st.sidebar.slider("Annual Burn Probability (%)", 0.0, 5.0, 1.0, step=0.1) / 100
mdr_unmitigated = st.sidebar.slider("Unmitigated MDR (%)", 50, 100, 80) / 100
mdr_mitigated = st.sidebar.slider("Mitigated MDR (%)", 10, 80, 30) / 100

st.sidebar.markdown("---")
st.sidebar.header("3. Program Costs")
faura_cost = st.sidebar.number_input("Faura Fixed Fee ($/home)", value=30)
incentives = st.sidebar.number_input("Total Incentives ($/conversion)", value=150)

# --- CALCULATION LOGIC ---
def calculate_elasticity():
    # Create a range of conversion rates from 0% to 100%
    conversion_rates = np.linspace(0, 1, 101) # 0.00, 0.01, ... 1.00
    
    results = []
    
    # Constant Values (Status Quo doesn't change with conversion)
    sq_losses = n_homes * avg_tiv * incident_prob * mdr_unmitigated
    sq_expenses = n_homes * avg_premium * expense_ratio
    sq_profit = (n_homes * avg_premium) - sq_expenses - sq_losses
    
    for rate in conversion_rates:
        # Faura Logic
        n_converted = n_homes * rate
        n_unconverted = n_homes * (1 - rate)
        
        # Losses
        loss_unconverted = n_unconverted * avg_tiv * incident_prob * mdr_unmitigated
        loss_converted = n_converted * avg_tiv * incident_prob * mdr_mitigated
        total_losses = loss_unconverted + loss_converted
        
        # Program Costs
        program_fees = n_homes * faura_cost # Fixed fee applies to ALL homes
        incentive_costs = n_converted * incentives # Only paid if they convert
        
        # Net Profit
        faura_profit = (n_homes * avg_premium) - sq_expenses - total_losses - program_fees - incentive_costs
        
        results.append({
            "Conversion_Rate": rate * 100, # For display (0-100)
            "Faura_Profit": faura_profit,
            "Status_Quo_Profit": sq_profit,
            "Net_Benefit": faura_profit - sq_profit
        })
        
    return pd.DataFrame(results)

df = calculate_elasticity()

# --- FIND BREAKEVEN POINT ---
# Find the first row where Net Benefit > 0
try:
    breakeven_row = df[df['Net_Benefit'] > 0].iloc[0]
    breakeven_rate = breakeven_row['Conversion_Rate']
    breakeven_text = f"{breakeven_rate:.1f}%"
    breakeven_color = "green"
except IndexError:
    breakeven_text = "Never (Costs exceed Benefits)"
    breakeven_color = "red"

# --- METRICS ROW ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Breakeven Conversion Rate", breakeven_text)
with col2:
    current_benefit_20 = df[df['Conversion_Rate'] == 20.0]['Net_Benefit'].values[0]
    st.metric("Net Benefit at 20% Conversion", f"${current_benefit_20:,.0f}")
with col3:
    max_benefit = df['Net_Benefit'].max()
    st.metric("Max Potential Benefit (100% Conv)", f"${max_benefit:,.0f}")

# --- PLOTLY CHART ---
fig = go.Figure()

# 1. Status Quo Line (Flat Dashed)
fig.add_trace(go.Scatter(
    x=df['Conversion_Rate'],
    y=df['Status_Quo_Profit'],
    mode='lines',
    name='Status Quo Profit',
    line=dict(color='#EF553B', width=3, dash='dash')
))

# 2. Faura Profit Line (Curved Green)
fig.add_trace(go.Scatter(
    x=df['Conversion_Rate'],
    y=df['Faura_Profit'],
    mode='lines',
    name='Profit with Faura',
    line=dict(color='#4B604D', width=4)
))

# 3. Add Breakeven Marker
if breakeven_text != "Never (Costs exceed Benefits)":
    fig.add_annotation(
        x=breakeven_rate,
        y=breakeven_row['Faura_Profit'],
        text=f"Breakeven: {breakeven_text}",
        showarrow=True,
        arrowhead=1,
        ax=0,
        ay=-40,
        bgcolor="white",
        bordercolor="black"
    )

# Formatting
fig.update_layout(
    title="Profitability vs. Homeowner Conversion Rate",
    xaxis_title="Conversion Rate (%)",
    yaxis_title="Total Portfolio Profit ($)",
    hovermode="x unified",
    template="plotly_white",
    height=600,
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
)

# Add shading for "Profit Zone"
fig.add_trace(go.Scatter(
    x=df['Conversion_Rate'],
    y=df['Faura_Profit'],
    fill='tonexty', # Fills to the trace before it (Status Quo)
    fillcolor='rgba(75, 96, 77, 0.1)', # Light Green
    line=dict(width=0),
    showlegend=False,
    hoverinfo='skip'
))

st.plotly_chart(fig, use_container_width=True)

# --- EXPLANATION ---
st.info("""
**How to read this chart:**
* **The Red Dashed Line** is the Status Quo. It is flat because doing nothing changes nothing.
* **The Green Line** starts *below* the red line (because of the fixed program fees).
* As conversion increases, risk drops. The point where the Green line crosses the Red line is your **Breakeven Point**.
* **The Green Zone** represents "Net New Profit" created by the partnership.
""")