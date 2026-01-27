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

st.title("📈 Conversion Elasticity: Net Profitability")
st.markdown("""
The more homeowners that "convert" and improve their home's resilience, the less expected losses you'll have.
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
n_homes = st.sidebar.number_input("Number of Homes", value=100, step=10) # CHANGED TO 100
avg_premium = currency_input("Avg Premium per Home", 10000)
avg_tiv = currency_input("Avg TIV per Home", 1000000)
expense_ratio = st.sidebar.number_input("Expense Ratio (%)", value=15.0, step=0.1, format="%.2f") / 100

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
def calculate_profit(rate):
    # --- 1. REVENUE (Premium) ---
    # Status Quo: Everyone pays full premium
    sq_revenue = n_homes * avg_premium
    
    # Faura: Converted users pay LESS (Discount)
    n_converted = n_homes * rate
    n_unconverted = n_homes * (1 - rate)
    
    # Revenue is Full Premium for unconverted + Discounted Premium for converted
    faura_revenue = (n_unconverted * avg_premium) + (n_converted * (avg_premium - premium_discount))
    
    # --- 2. EXPENSES (Fixed) ---
    # We assume expense ratio applies to the written premium
    sq_expenses = sq_revenue * expense_ratio
    faura_expenses = faura_revenue * expense_ratio
    
    # --- 3. LOSSES (Claims) ---
    sq_losses = n_homes * avg_tiv * incident_prob * mdr_unmitigated
    
    loss_unconverted = n_unconverted * avg_tiv * incident_prob * mdr_unmitigated
    loss_converted = n_converted * avg_tiv * incident_prob * mdr_mitigated
    faura_losses = loss_unconverted + loss_converted
    
    # --- 4. PROGRAM COSTS ---
    program_fixed_cost = n_homes * faura_cost
    incentive_cost = n_converted * gift_card # Discount is already handled in Revenue line
    total_program_cost = program_fixed_cost + incentive_cost
    
    # --- NET PROFIT CALC ---
    sq_profit = sq_revenue - sq_expenses - sq_losses
    faura_profit = faura_revenue - faura_expenses - faura_losses - total_program_cost
    
    return sq_profit, faura_profit, faura_losses, total_program_cost

# --- GENERATE DATA ---
x_range = np.linspace(0, 0.20, 21) 
data = []

for r in x_range:
    sq, faura, losses, prog_cost = calculate_profit(r)
    net_benefit = faura - sq
    
    data.append({
        "Rate": r,
        "Label": f"{int(r*100)}%",
        "SQ_Profit": sq,
        "Faura_Profit": faura,
        "Net_Benefit": net_benefit,
        "Faura_Losses": losses,
        "Program_Spend": prog_cost
    })

df = pd.DataFrame(data)

# --- METRICS ROW ---
# Reduced to 2 columns to remove the middle box
col1, col2 = st.columns(2)
with col1:
    st.metric("Status Quo Profit", f"${df.iloc[0]['SQ_Profit']:,.0f}")
with col2:
    # Breakeven Check
    try:
        be_row = df[df['Net_Benefit'] > 0].iloc[0]
        be_text = f"{be_row['Rate']*100:.0f}%"
    except:
        be_text = "None (Costs > Savings)"
    st.metric("Conversion required for Profitability", be_text)

# --- PLOTLY CHART ---
fig = go.Figure()

# 1. Status Quo Line (Flat)
fig.add_trace(go.Scatter(
    x=df['Rate'],
    y=df['SQ_Profit'],
    mode='lines',
    name='Status Quo Profit',
    line=dict(color='#EF553B', width=3, dash='dash'),
    hovertemplate='<b>Status Quo</b><br>Profit: %{y:$,.0f}<extra></extra>'
))

# 2. Faura Profit Line (Rising)
custom_data = np.stack((df['Net_Benefit'], df['Faura_Losses'], df['Program_Spend']), axis=-1)

fig.add_trace(go.Scatter(
    x=df['Rate'],
    y=df['Faura_Profit'],
    mode='lines+markers',
    name='Profit with Faura',
    line=dict(color='#4B604D', width=4),
    marker=dict(size=8),
    customdata=custom_data,
    hovertemplate=(
        "<b>Conversion: %{x:.0%}</b><br>" +
        "Net Profit: %{y:$,.0f}<br>" +
        "-------------------<br>" +
        "💰 <b>Net Benefit: %{customdata[0]:+$,.0f}</b><br>" +
        "📉 Expected Losses: %{customdata[1]:$,.0f}<br>" +
        "💸 Program Fees: %{customdata[2]:$,.0f}" +
        "<extra></extra>"
    )
))

# Removed the annotation code block here

fig.update_layout(
    title="Net Underwriting Profit vs. Conversion Rate (0% - 20%)",
    xaxis_title="Conversion Rate (%)",
    yaxis_title="Total Underwriting Profit ($)",
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
**Why Profit Matters:** This model accounts for the **Premium Discount**. 
Notice that even though you are charging the converted customers *less money* (lowering revenue), your Profit (Green Line) still rises. 
This proves that the **Risk Reduction** outpaces the **Revenue Reduction**.
""")