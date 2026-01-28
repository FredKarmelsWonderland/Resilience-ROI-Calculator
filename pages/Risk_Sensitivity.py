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
st.set_page_config(page_title="Faura Risk Scenarios", layout="wide")

st.title("🔥 Faura Risk Sensitivity:  See how profitability changes with incident probability")

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
    value=100, 
    step=1
)

avg_premium = currency_input("Avg Premium per Home", 10000)
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

# NOTE: This input is for the "Current State" table at the bottom
Incident_prob_input = st.sidebar.number_input(
    "Current Annual Incident Prob (%)", 
    value=1.0, 
    step=0.01,
    format="%.2f"
)
current_Incident_prob = Incident_prob_input / 100

mdr_unmitigated_input = st.sidebar.number_input("MDR (Unmitigated) %", value=80.0, step=0.1)
mdr_unmitigated = mdr_unmitigated_input / 100

mdr_mitigated_input = st.sidebar.number_input("MDR (Mitigated) %", value=30.0, step=0.1)
mdr_mitigated = mdr_mitigated_input / 100

st.sidebar.markdown("---")
st.sidebar.header("3. Faura Program Inputs")

faura_cost = currency_input("Faura Cost per Home", 30)

conversion_input = st.sidebar.number_input("Conversion Rate (%)", value=20.0, step=1.0)
conversion_rate = conversion_input / 100

gift_card = currency_input("Gift Card Incentive", 50)
premium_discount = currency_input("Premium Discount", 100)


# --- CALCULATION LOGIC ---
def calculate_metrics(override_Incident_prob=None):
    calc_Incident_prob = override_Incident_prob if override_Incident_prob is not None else current_Incident_prob

    total_premium = n_homes * avg_premium
    total_uw_expense = total_premium * expense_ratio

    # --- STATUS QUO ---
    sq_losses = n_homes * avg_tiv * calc_Incident_prob * mdr_unmitigated
    sq_profit = total_premium - (total_uw_expense + sq_losses)

    # --- FAURA ---
    n_converted = n_homes * conversion_rate
    n_unconverted = n_homes * (1 - conversion_rate)

    faura_loss_unconverted = n_unconverted * avg_tiv * calc_Incident_prob * mdr_unmitigated
    faura_loss_converted = n_converted * avg_tiv * calc_Incident_prob * mdr_mitigated
    faura_total_losses = faura_loss_unconverted + faura_loss_converted

    total_faura_fee = n_homes * faura_cost
    total_gift_cards = n_converted * gift_card
    total_discounts = n_converted * premium_discount
    
    faura_total_cost = (
        total_uw_expense + 
        faura_total_losses + 
        total_faura_fee + 
        total_gift_cards + 
        total_discounts
    )
    
    faura_profit = total_premium - faura_total_cost

    return {
        "sq_profit": sq_profit,
        "faura_profit": faura_profit,
        "sq_losses": sq_losses,
        "faura_losses": faura_total_losses,
        "faura_program_cost": total_faura_fee,
        "faura_incentives": total_gift_cards + total_discounts,
        "total_premium": total_premium,
        "expenses": total_uw_expense
    }

metrics = calculate_metrics()

# --- CROSSOVER CALCULATION ---
total_program_cost = metrics['faura_program_cost'] + metrics['faura_incentives']
n_converted = n_homes * conversion_rate
mdr_diff = mdr_unmitigated - mdr_mitigated
tiv_risk_pool = n_converted * avg_tiv

if tiv_risk_pool > 0 and mdr_diff > 0:
    crossover_Incident_prob = total_program_cost / (tiv_risk_pool * mdr_diff)
else:
    crossover_Incident_prob = 0 
crossover_percent = crossover_Incident_prob * 100


# --- SCENARIO BAR CHART ---
#st.subheader("See how Profitability Changes with Incident Probability")

# Define the specific scenarios requested
scenarios = [0.0001, 0.001, 0.005, 0.01, 0.02]
scenario_labels = ["0.01%", "0.10%", "0.50%", "1.00%", "2.00%"]

sq_data = []
faura_data = []
deltas = []

for prob in scenarios:
    res = calculate_metrics(override_Incident_prob=prob)
    sq_data.append(res['sq_profit'])
    faura_data.append(res['faura_profit'])
    deltas.append(res['faura_profit'] - res['sq_profit'])

fig = go.Figure()

# 1. Status Quo Bars
fig.add_trace(go.Bar(
    name='Status Quo',
    x=scenario_labels,
    y=sq_data,
    marker_color='#EF553B',
    text=[f"${x:,.0f}" for x in sq_data],
    textposition='auto',
    textfont=dict(size=18, color="white", family="Arial Black")
))

# 2. Faura Bars
fig.add_trace(go.Bar(
    name='With Faura',
    x=scenario_labels,
    y=faura_data,
    marker_color='#4B604D',
    text=[f"${x:,.0f}" for x in faura_data],
    textposition='auto',
    textfont=dict(size=18, color="white", family="Arial Black")
))

# 3. Add Annotation for the DIFFERENCE (The "Net Benefit")
for i, delta in enumerate(deltas):
    max_height = max(sq_data[i], faura_data[i])
    text_color = "green" if delta > 0 else "red"
    sign = "+" if delta > 0 else ""
    
    fig.add_annotation(
        x=scenario_labels[i],
        y=max_height,
        text=f"<b>{sign}${delta:,.0f}</b>",
        showarrow=False,
        yshift=30, 
        font=dict(size=20, color=text_color)
    )

fig.update_layout(
    title=dict(
        text="Net Profit Comparison by Incident Probability",
        font=dict(size=26)
    ),
    xaxis=dict(
        title="Incident Probability Scenario",
        title_font=dict(size=22),
        tickfont=dict(size=18)
    ),
    yaxis=dict(
        title="Net Profit ($)",
        title_font=dict(size=22),
        tickfont=dict(size=18)
    ),
    barmode='group',
    template="plotly_white",
    height=600,
    legend=dict(
        orientation="h", 
        yanchor="bottom", 
        y=1.02, 
        xanchor="right", 
        x=1,
        font=dict(size=18)
    )
)

st.plotly_chart(fig, use_container_width=True)

# --- EXPLANATION FOOTER ---
st.markdown("---")
st.subheader("💡 Why Does ROI Change with Risk?")

col_left, col_right = st.columns([1, 1])

# --- DYNAMIC CALCULATION FOR TEXT ---
# 1. Calculate Average Program Cost (Weighted by Conversion)
total_incentives = gift_card + premium_discount
weighted_incentives = total_incentives * conversion_rate
avg_prog_cost = faura_cost + weighted_incentives

# 2. Calculate Weighted Average Savings
# Low Risk Example (0.01%)
low_prob = 0.0001
low_loss_diff = (avg_tiv * low_prob * mdr_unmitigated) - (avg_tiv * low_prob * mdr_mitigated)
low_weighted_savings = low_loss_diff * conversion_rate

# High Risk Example (1.00%)
high_prob = 0.01
high_loss_diff = (avg_tiv * high_prob * mdr_unmitigated) - (avg_tiv * high_prob * mdr_mitigated)
high_weighted_savings = high_loss_diff * conversion_rate

with col_left:
    st.markdown("### 1. Program Cost Breakdown (Weighted)")
    st.markdown(f"""
    To understand ROI, we calculate the **Average Cost per Home** across the entire book.
    
    * **Base Fee:** \${faura_cost:,.0f} (Paid for 100% of homes)
    * **Incentives:** \${total_incentives:,.0f} (Only paid for the {conversion_rate*100:.0f}% who convert)
    
    **The Weighted Calculation:**
    Since only {conversion_rate*100:.0f}% of homeowners earn the incentives, we average that cost across the whole group:
    """)
    
    # Visual Equation
    st.latex(rf'''
        \underbrace{{\${faura_cost:,.0f}}}_{{\text{{Base Fee}}}} + 
        (\underbrace{{\${total_incentives:,.0f}}}_{{\text{{Incentives}}}} \times \underbrace{{{conversion_rate*100:.0f}\%}}_{{\text{{Conv Rate}}}}) = 
        \boxed{{\textbf{{\${avg_prog_cost:,.0f}}}}}
    ''')
    
    # REPLACED st.caption WITH st.info FOR VISIBILITY
    st.info(f"👉 **Hurdle Rate:** We need to generate at least **\${avg_prog_cost:,.0f}** in savings per home just to break even on the program costs.")

with col_right:
    st.markdown("### 2. The Value Proposition Curve")
    
    st.markdown(f"""
    **We compare that calculated \${avg_prog_cost:,.0f} Cost against the "Expected Savings."**
    
    * **At Low Risk (0.01%):** The expected savings is tiny (\${low_weighted_savings:,.2f}). Since the program costs \${avg_prog_cost:,.0f}, **you lose money.**
    
    * **At High Risk (1.00%):** The expected savings jumps to **\${high_weighted_savings:,.0f}**. Since the program cost stays flat at \${avg_prog_cost:,.0f}, **you gain massive profit.**
    """)
    
    if crossover_percent > 0:
        # REPLACED BLOCKQUOTE WITH st.success FOR VISIBILITY
        st.success(f"✅ **Critical Insight:** For your current inputs, Faura becomes profitable once the annual Incident probability exceeds **{crossover_percent:.3f}%**.")