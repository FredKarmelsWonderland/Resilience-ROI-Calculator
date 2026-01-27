import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- PASSWORD PROTECTION ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "Faura2026":  # <--- Set your password here
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password
        else:
            st.session_state["password_correct"] = False

    # Initialize session state variables
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    # Show input if not authenticated
    if not st.session_state["password_correct"]:
        st.text_input(
            "Please enter the Sales Access Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        return False
    else:
        return True

if not check_password():
    st.stop()  # Do not run the rest of the app if password is wrong


# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Conversion Elasticity", layout="wide")

st.title("📈 Faura Conversion Elasticity Analysis")
st.markdown("""
**The "Partnership Curve":** This chart demonstrates why higher conversion rates drive exponential value for the carrier.
It answers: *"At what participation rate does the program pay for itself?"*
""")

# --- HELPER FUNCTION FOR CURRENCY INPUTS ---
def currency_input(label, default_value, tooltip=None):
    """
    Creates a text input that looks like currency ($1,000,000)
    but returns a clean float (1000000.0) for math.
    """
    user_input = st.sidebar.text_input(
        label, 
        value=f"${default_value:,.0f}", 
        help=tooltip
    )
    
    try:
        clean_val = float(user_input.replace('$', '').replace(',', '').strip())
    except ValueError:
        clean_val = default_value
        st.sidebar.error(f"Please enter a valid number for {label}")
        
    return clean_val

# --- SIDEBAR: INPUT VARIABLES ---
st.sidebar.header("1. Portfolio Inputs")

n_homes = st.sidebar.number_input(
    "Number of Homes", 
    value=1000, 
    step=100
)

avg_premium = currency_input("Avg Premium per Home", 2500)
avg_tiv = currency_input("Avg TIV per Home", 1000000)

expense_ratio_input = st.sidebar.number_input(
    "Expense Ratio (%)", 
    value=20.0, 
    step=0.1,
    format="%.2f"
)
expense_ratio = expense_ratio_input / 100

st.sidebar.markdown("---")
st.sidebar.header("2. Risk Inputs")

incident_prob_input = st.sidebar.number_input(
    "Annual incident Prob (%)", 
    value=1.0, 
    step=0.01,
    format="%.2f"
)
incident_prob = incident_prob_input / 100

mdr_unmitigated_input = st.sidebar.number_input("MDR (Unmitigated) %", value=80.0, step=0.1)
mdr_unmitigated = mdr_unmitigated_input / 100

mdr_mitigated_input = st.sidebar.number_input("MDR (Mitigated) %", value=30.0, step=0.1)
mdr_mitigated = mdr_mitigated_input / 100

st.sidebar.markdown("---")
st.sidebar.header("3. Faura Program Inputs")

faura_cost = currency_input("Faura Cost per Home", 30)

# Note: We don't ask for "Conversion Rate" here because that is the X-Axis of the chart!
st.sidebar.info("ℹ️ Conversion Rate is the variable we are testing (0% to 100%)")

gift_card = currency_input("Gift Card Incentive", 50)
premium_discount = currency_input("Premium Discount", 100)


# --- CALCULATION LOGIC ---
def calculate_elasticity():
    # Create a range of conversion rates from 0% to 100%
    conversion_rates = np.linspace(0, 1, 101) # 0.00, 0.01, ... 1.00
    
    results = []
    
    # Constant Values (Status Quo doesn't change with conversion)
    sq_losses = n_homes * avg_tiv * incident_prob * mdr_unmitigated
    sq_expenses = n_homes * avg_premium * expense_ratio
    sq_profit = (n_homes * avg_premium) - sq_expenses - sq_losses
    
    # Combined Incentive Cost
    total_incentives_per_conversion = gift_card + premium_discount
    
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
        incentive_costs = n_converted * total_incentives_per_conversion # Only paid if they convert
        
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
    breakeven_text = "Never"
    breakeven_color = "red"

# --- METRICS ROW ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Breakeven Conversion Rate", breakeven_text)
with col2:
    # Check 20% point for reference
    try:
        current_benefit_20 = df.iloc[20]['Net_Benefit'] # Index 20 corresponds to 20%
        st.metric("Net Benefit at 20% Conversion", f"${current_benefit_20:,.0f}")
    except:
        st.metric("Net Benefit at 20%", "N/A")
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
if breakeven_text != "Never":
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