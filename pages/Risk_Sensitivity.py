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
st.set_page_config(page_title="See profitability breakeven", layout="wide")

st.title("See profitability breakeven")
st.markdown("### Adjust Risk & Program Performance")

# --- HELPER FUNCTION FOR CURRENCY INPUTS ---
def currency_input(label, default_value, tooltip=None):
    user_input = st.sidebar.text_input(
        label, 
        value=f"${default_value:,.0f}", 
        help=tooltip
    )
    try:
        clean_val = float(user_input.replace('$', '').replace(',', '').strip())
    except ValueError:
        clean_val = default_value
    return clean_val

# --- SIDEBAR: PORTFOLIO & COST INPUTS ONLY ---
st.sidebar.header("1. Portfolio Inputs")

n_homes = st.sidebar.number_input("Number of Homes", value=100, step=1)
avg_premium = currency_input("Avg Premium per Home", 10000)
avg_tiv = currency_input("Avg TIV per Home", 1000000)
expense_ratio_input = st.sidebar.number_input("Expense Ratio (%)", value=20.0, step=0.1, format="%.2f")
expense_ratio = expense_ratio_input / 100

st.sidebar.markdown("---")
st.sidebar.header("2. Faura Program Costs")
faura_cost = currency_input("Faura Cost per Home", 30)
gift_card = currency_input("Gift Card Incentive", 50)
premium_discount = currency_input("Premium Discount", 100)


# --- MAIN PAGE SLIDERS ---
# All ranges start at 0.0. Defaults set to sensible starting points.
col1, col2, col3, col4 = st.columns(4)

with col1:
    incident_prob_input = st.slider(
        "Incident Probability (%)", 
        min_value=0.00, 
        max_value=5.00, 
        value=1.00, 
        step=0.01,
        format="%.2f%%"
    )
    current_Incident_prob = incident_prob_input / 100

with col2:
    mdr_unmitigated_input = st.slider(
        "MDR Unmitigated (%)", 
        min_value=0.0, 
        max_value=100.0, 
        value=80.0, 
        step=1.0,
        format="%.0f%%"
    )
    mdr_unmitigated = mdr_unmitigated_input / 100

with col3:
    mdr_mitigated_input = st.slider(
        "MDR Mitigated (%)", 
        min_value=0.0, 
        max_value=100.0, 
        value=30.0, 
        step=1.0,
        format="%.0f%%"
    )
    mdr_mitigated = mdr_mitigated_input / 100

with col4:
    conversion_input = st.slider(
        "Conversion Rate (%)", 
        min_value=0.0, 
        max_value=100.0, 
        value=20.0, 
        step=1.0,
        format="%.0f%%"
    )
    conversion_rate = conversion_input / 100

# --- BREAKEVEN ANALYSIS (DYNAMIC TEXT) ---
loss_reduction_per_converted_home = (avg_tiv * current_Incident_prob * mdr_unmitigated) - (avg_tiv * current_Incident_prob * mdr_mitigated)
total_incentives_per_converted_home = gift_card + premium_discount
net_benefit_per_conversion = loss_reduction_per_converted_home - total_incentives_per_converted_home

# We use backslash-dollar sign (\$) to prevent Streamlit from thinking this is LaTeX Math
if net_benefit_per_conversion <= 0:
    st.error(f"⚠️ **Impossible to Break Even:** At this Incident Probability, the incentives (**\${total_incentives_per_converted_home:,.0f}**) cost more than the savings (**\${loss_reduction_per_converted_home:,.0f}**) per home.")
else:
    breakeven_rate = faura_cost / net_benefit_per_conversion
    breakeven_pct = breakeven_rate * 100
    
    if breakeven_pct > 100:
        st.warning(f"⚠️ **Impossible to Break Even:** You would need over 100% conversion ({breakeven_pct:.1f}%) to cover the base fees.")
    else:
        st.info(f"🎯 **Breakeven Insight:** For these inputs, if Faura converts **{breakeven_pct:.1f}%** of homes, the program will pay for itself in reduced expected losses.")

# --- CALCULATION LOGIC ---
def calculate_metrics():
    total_premium = n_homes * avg_premium
    total_uw_expense = total_premium * expense_ratio

    # --- STATUS QUO ---
    sq_losses = n_homes * avg_tiv * current_Incident_prob * mdr_unmitigated
    sq_profit = total_premium - (total_uw_expense + sq_losses)

    # --- FAURA ---
    n_converted = n_homes * conversion_rate
    n_unconverted = n_homes * (1 - conversion_rate)

    faura_loss_unconverted = n_unconverted * avg_tiv * current_Incident_prob * mdr_unmitigated
    faura_loss_converted = n_converted * avg_tiv * current_Incident_prob * mdr_mitigated
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
        "faura_incentives": total_gift_cards + total_discounts
    }

metrics = calculate_metrics()

# --- BAR CHART GENERATION ---
fig = go.Figure()

x_labels = ['Status Quo', 'With Faura']
y_values = [metrics['sq_profit'], metrics['faura_profit']]
colors = ['#EF553B', '#4B604D'] # Red / Green

fig.add_trace(go.Bar(
    x=x_labels,
    y=y_values,
    marker_color=colors,
    text=[f"${val:,.0f}" for val in y_values],
    textposition='auto',
))

# Calculate Delta for Annotation
delta = metrics['faura_profit'] - metrics['sq_profit']
text_color = "green" if delta > 0 else "red"
sign = "+" if delta > 0 else ""

# Add Annotation above the 'With Faura' bar
# If y_values are 0 (start of sliders), handle gracefully
max_y = max(y_values) if max(y_values) > 0 else 1000 

fig.add_annotation(
    x=1, # Index of 'With Faura'
    y=metrics['faura_profit'],
    text=f"<b>{sign}${delta:,.0f}</b>",
    showarrow=True,
    arrowhead=2,
    ax=0,
    ay=-40,
    font=dict(size=24, color=text_color)
)

fig.update_layout(
    title=dict(text="Net Profit Comparison", font=dict(size=24)),
    yaxis=dict(title="Net Profit ($)", title_font=dict(size=18)),
    xaxis=dict(tickfont=dict(size=18)),
    template="plotly_white",
    height=500,
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)


# --- EXPLANATION FOOTER ---
st.markdown("---")
st.subheader("💡 Why Does ROI Change?")

col_left, col_right = st.columns([1, 1])

# Dynamic Text Calculations
total_incentives = gift_card + premium_discount
weighted_incentives = total_incentives * conversion_rate
avg_prog_cost = faura_cost + weighted_incentives
loss_reduction_per_home = (avg_tiv * current_Incident_prob * mdr_unmitigated) - (avg_tiv * current_Incident_prob * mdr_mitigated)
weighted_savings = loss_reduction_per_home * conversion_rate

with col_left:
    st.markdown("### 1. Cost to Run Program")
    st.markdown(f"""
    We calculate the **Weighted Cost per Home** across the whole book:
    
    * **Base Fee:** \${faura_cost:,.0f} (Paid for 100% of homes)
    * **Incentives:** \${total_incentives:,.0f} (Only paid for the {conversion_rate*100:.0f}% who convert)
    """)
    
    st.latex(rf'''
        \${faura_cost:,.0f} + (\${total_incentives:,.0f} \times {conversion_rate*100:.0f}\%) = \boxed{{\textbf{{\${avg_prog_cost:,.0f}}}}}
    ''')
    
    st.info(f"👉 **Hurdle Rate:** You spend **\${avg_prog_cost:,.0f}** per home to run this.")

with col_right:
    st.markdown("### 2. Savings Generated")
    st.markdown(f"""
    We compare that cost against the **Expected Loss Reduction**:
    
    * **Loss Diff:** An unmitigated home loses \${(avg_tiv*current_Incident_prob*mdr_unmitigated):,.0f} vs. \${(avg_tiv*current_Incident_prob*mdr_mitigated):,.0f} mitigated.
    * **Probability:** This happens {current_Incident_prob*100:.2f}% of the time.
    """)
    
    net_result = weighted_savings - avg_prog_cost
    result_color = "green" if net_result > 0 else "red"
    result_word = "PROFIT" if net_result > 0 else "LOSS"
    
    st.markdown(f"""
    **Result:** At this risk level, you save **\${weighted_savings:,.0f}** per home (weighted).
    
    Since **\${weighted_savings:,.0f}** (Savings) - **\${avg_prog_cost:,.0f}** (Cost) = :{result_color}[**\${net_result:,.0f}**], the program generates a **{result_word}**.
    """)