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

st.title("📈 Conversion Elasticity: Cost vs. Benefit Analysis")
st.markdown("""
**The ROI Equation:** This view isolates the **Expected Claims Savings** against the **Program Costs**.
It answers: *"If we spend money on incentives and fees, does the drop in claims cover the bill?"*
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
n_homes = st.sidebar.number_input("Number of Homes", value=100, step=10)
avg_tiv = currency_input("Avg TIV per Home", 1000000)

# Note: We don't need Premium for a "Losses" view, but we keep the Expense Ratio box
# just in case you want to pivot back later, or we can hide it. Leaving it out for clarity here.

st.sidebar.markdown("---")
st.sidebar.header("2. Risk Inputs")
incident_prob = st.sidebar.number_input("Annual Incident Prob (%)", value=1.0, step=0.01, format="%.2f") / 100
mdr_unmitigated = st.sidebar.number_input("MDR (Unmitigated) %", value=80.0, step=0.1) / 100
mdr_mitigated = st.sidebar.number_input("MDR (Mitigated) %", value=30.0, step=0.1) / 100

st.sidebar.markdown("---")
st.sidebar.header("3. Faura Program Inputs")
faura_cost = currency_input("Faura Cost per Home", 30)
st.sidebar.info("ℹ️ Analyzing Conversion from 0% to 20%")
gift_card = currency_input("Gift Card Incentive", 300)
premium_discount = currency_input("Premium Discount", 300)

# --- CALCULATION LOGIC ---
def calculate_scenario(rate):
    # Unmitigated Baseline (Status Quo)
    sq_losses = n_homes * avg_tiv * incident_prob * mdr_unmitigated
    
    # With Faura Conversion
    n_converted = n_homes * rate
    n_unconverted = n_homes * (1 - rate)
    
    loss_unconverted = n_unconverted * avg_tiv * incident_prob * mdr_unmitigated
    loss_converted = n_converted * avg_tiv * incident_prob * mdr_mitigated
    
    faura_losses = loss_unconverted + loss_converted
    
    # Calculate Costs
    # Note: We include Premium Discount here as a "Cost" because it is lost revenue, 
    # essentially a cost to the carrier's bottom line.
    program_fixed_cost = n_homes * faura_cost
    incentive_variable_cost = n_converted * (gift_card + premium_discount)
    total_program_cost = program_fixed_cost + incentive_variable_cost
    
    return sq_losses, faura_losses, total_program_cost

# --- GENERATE DATA ---
x_range = np.linspace(0, 0.20, 21) 
data = []

for r in x_range:
    sq, faura, cost = calculate_scenario(r)
    claims_saved = sq - faura
    net_benefit = claims_saved - cost # The "Delta"
    
    # ROI Multiplier
    roi_mult = claims_saved / cost if cost > 0 else 0
    
    data.append({
        "Rate": r,
        "Label": f"{int(r*100)}%",
        "SQ_Losses": sq,
        "Faura_Losses": faura,
        "Claims_Saved": claims_saved,
        "Program_Cost": cost,
        "Net_Benefit": net_benefit,
        "ROI_Mult": roi_mult
    })

df = pd.DataFrame(data)

# --- METRICS ROW ---
col1, col2, col3 = st.columns(3)

# We grab the stats at the 20% mark (the end of the chart)
idx_20 = 20
stats_20 = df.iloc[idx_20]

with col1:
    st.metric(
        "Claims Prevented (at 20%)", 
        f"${stats_20['Claims_Saved']:,.0f}", 
        delta="Gross Savings"
    )
with col2:
    st.metric(
        "Total Program Cost (at 20%)", 
        f"${stats_20['Program_Cost']:,.0f}", 
        delta="Fees + Incentives",
        delta_color="inverse" # Make red mean "Cost"
    )
with col3:
    st.metric(
        "Net Project ROI (Delta)", 
        f"${stats_20['Net_Benefit']:,.0f}", 
        delta=f"{stats_20['ROI_Mult']:.1f}x Multiplier"
    )

# --- PLOTLY CHART ---
fig = go.Figure()

# 1. Status Quo Line (Flat Dashed)
fig.add_trace(go.Scatter(
    x=df['Rate'],
    y=df['SQ_Losses'],
    mode='lines',
    name='Status Quo Losses',
    line=dict(color='#EF553B', width=3, dash='dash'),
    hovertemplate='<b>Status Quo</b><br>Expected Losses: %{y:$,.0f}<extra></extra>'
))

# 2. Faura Losses Line (Interactive)
custom_data = np.stack((df['Claims_Saved'], df['Program_Cost'], df['Net_Benefit']), axis=-1)

fig.add_trace(go.Scatter(
    x=df['Rate'],
    y=df['Faura_Losses'],
    mode='lines+markers',
    name='Losses with Faura',
    line=dict(color='#4B604D', width=4),
    marker=dict(size=8),
    customdata=custom_data,
    hovertemplate=(
        "<b>Conversion: %{x:.0%}</b><br>" +
        "Expected Losses: %{y:$,.0f}<br>" +
        "-------------------<br>" +
        "🛡️ Claims Saved: %{customdata[0]:$,.0f}<br>" +
        "🧾 Program Cost: %{customdata[1]:$,.0f}<br>" +
        "💰 <b>Net Delta: %{customdata[2]:+$,.0f}</b>" +
        "<extra></extra>"
    )
))

fig.update_layout(
    title="Expected Annual Losses vs. Conversion Rate (0% - 20%)",
    xaxis_title="Conversion Rate (%)",
    yaxis_title="Expected Annual Losses ($)",
    xaxis=dict(
        tickmode='array',
        tickvals=x_range,
        ticktext=[f"{int(x*100)}%" for x in x_range],
        range=[-0.005, 0.205]
    ),
    hovermode="closest",
    template="plotly_white",
    height=600,
    legend=dict(yanchor="bottom", y=0.01, xanchor="left", x=0.01)
)

st.plotly_chart(fig, use_container_width=True)

# --- FOOTER ---
st.info("""
**Interpreting the Delta:**
* **Column 1 (Savings):** The pure reduction in fire claims risk.
* **Column 2 (Cost):** The total bill (Platform Fees + Gift Cards + Premium Discounts).
* **Column 3 (Delta):** The money you keep. As long as this is **Positive**, the program is profitable.
""")