import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go # <--- This was the missing import

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Risk Sensitivity Analysis", layout="wide")

# --- LOGIN BLOCK ---
def check_password():
    if st.session_state.get("password_correct", False):
        return True
    
    st.title("🔒 Faura Portfolio Map")
    with st.form("login_form"):
        st.write("Please enter the access code to view the map.")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log In"):
            if password == "Faura2026":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Password incorrect")
    return False

if not check_password():
    st.stop()

# --- MAIN CONTENT ---
st.title("Risk Sensitivity Analysis")
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

# --- SIDEBAR: PORTFOLIO & COST INPUTS ---
st.sidebar.header("1. Portfolio Inputs")
n_homes = st.sidebar.number_input("Number of Homes", value=100, step=1)
avg_premium = currency_input("Avg Premium per Home", 3000)
avg_tiv = currency_input("Avg TIV per Home", 500000)
expense_ratio_input = st.sidebar.number_input("Expense Ratio (%)", value=20.0, step=0.1, format="%.2f")
expense_ratio = expense_ratio_input / 100

st.sidebar.markdown("---")
st.sidebar.header("2. Faura Program Costs")
faura_cost = currency_input("Faura Cost per Home", 20)
gift_card = currency_input("Gift Card Incentive", 50)
premium_discount = currency_input("Premium Discount", 100)

# --- MAIN PAGE SLIDERS ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    incident_prob_input = st.slider("Incident Probability (%)", 0.0, 5.0, 1.0, 0.01, format="%.2f%%")
    current_Incident_prob = incident_prob_input / 100

with col2:
    mdr_unmitigated_input = st.slider("MDR Unmitigated (%)", 0.0, 100.0, 80.0, 1.0, format="%.0f%%")
    mdr_unmitigated = mdr_unmitigated_input / 100

with col3:
    mdr_mitigated_input = st.slider("MDR Mitigated (%)", 0.0, 100.0, 30.0, 1.0, format="%.0f%%")
    mdr_mitigated = mdr_mitigated_input / 100

with col4:
    conversion_input = st.slider("Conversion Rate (%)", 0.0, 100.0, 20.0, 1.0, format="%.0f%%")
    conversion_rate = conversion_input / 100

# --- BREAKEVEN ANALYSIS (TEXT) ---
loss_reduction_per_converted_home = (avg_tiv * current_Incident_prob * mdr_unmitigated) - (avg_tiv * current_Incident_prob * mdr_mitigated)
total_incentives_per_converted_home = gift_card + premium_discount
net_benefit_per_conversion = loss_reduction_per_converted_home - total_incentives_per_converted_home
total_portfolio_savings = loss_reduction_per_converted_home * n_homes * conversion_rate

if net_benefit_per_conversion <= 0:
    st.error(f"⚠️ **Impossible to Break Even:** Incentives cost more than the avoided losses.")
else:
    breakeven_rate = faura_cost / net_benefit_per_conversion
    breakeven_pct = breakeven_rate * 100
    if breakeven_pct > 100:
        st.warning(f"⚠️ **Impossible:** Need >100% conversion to cover base fees.")
    else:
        st.info(
            f"Reducing MDR from {mdr_unmitigated*100:.0f}% to {mdr_mitigated*100:.0f}% avoids **\${loss_reduction_per_converted_home:,.0f}** in losses per home.\n\n"
            f"**Total Impact:** At {conversion_rate*100:.0f}% conversion, you avoid **\${total_portfolio_savings:,.0f}** across the book.\n\n"
            f"🎯 **Breakeven Insight:** You need a **{breakeven_pct:.1f}%** conversion rate to cover program fees."
        )

# --- CALCULATION LOGIC ---
def calculate_metrics():
    total_premium = n_homes * avg_premium
    total_uw_expense = total_premium * expense_ratio

    # Status Quo
    sq_losses = n_homes * avg_tiv * current_Incident_prob * mdr_unmitigated
    sq_profit = total_premium - (total_uw_expense + sq_losses)

    # Faura Scenario
    n_converted = n_homes * conversion_rate
    n_unconverted = n_homes * (1 - conversion_rate)

    faura_loss = (n_unconverted * avg_tiv * current_Incident_prob * mdr_unmitigated) + \
                 (n_converted * avg_tiv * current_Incident_prob * mdr_mitigated)

    total_faura_fee = n_homes * faura_cost
    total_incentives = n_converted * (gift_card + premium_discount)
    
    faura_profit = total_premium - (total_uw_expense + faura_loss + total_faura_fee + total_incentives)

    return {"sq_profit": sq_profit, "faura_profit": faura_profit}

metrics = calculate_metrics()

# --- BAR CHART GENERATION (UPDATED) ---
fig = go.Figure()

x_labels = ['Status Quo', 'With Faura']
y_values = [metrics['sq_profit'], metrics['faura_profit']]
colors = ['#EF553B', '#4B604D'] 

fig.add_trace(go.Bar(
    x=x_labels,
    y=y_values,
    marker_color=colors,
    text=[f"${val:,.0f}" for val in y_values],
    textposition='outside',             
    textfont=dict(size=22, color='#333333'), 
    cliponaxis=False                    
))

# Annotations
delta = metrics['faura_profit'] - metrics['sq_profit']
text_color = "green" if delta > 0 else "red"
sign = "+" if delta > 0 else ""

max_val = max(max(y_values), 0)
min_val = min(min(y_values), 0)
range_buffer = (max_val - min_val) * 0.2 if max_val != min_val else max_val * 0.2

fig.add_annotation(
    x=1, 
    y=metrics['faura_profit'],
    text=f"<b>{sign}${delta:,.0f}</b>",
    showarrow=True,
    arrowhead=2,
    ax=0,
    ay=-60,
    font=dict(size=24, color=text_color)
)

fig.update_layout(
    title=dict(text="Net Profit Comparison", font=dict(size=24)),
    yaxis=dict(
        title="Net Profit ($)", 
        title_font=dict(size=18),
        range=[min_val - (range_buffer/2), max_val + range_buffer] 
    ),
    xaxis=dict(tickfont=dict(size=18)),
    template="plotly_white",
    height=500,
    showlegend=False,
    margin=dict(t=80) 
)

st.plotly_chart(fig, use_container_width=True)

# --- EXPLANATION FOOTER ---
st.markdown("---")
st.subheader("💡 Why Does ROI Change?")

col_left, col_right = st.columns([1, 1])

# Re-calculate vars for text display
total_incentives = gift_card + premium_discount
weighted_incentives = total_incentives * conversion_rate
avg_prog_cost = faura_cost + weighted_incentives
loss_reduction_per_home = (avg_tiv * current_Incident_prob * mdr_unmitigated) - (avg_tiv * current_Incident_prob * mdr_mitigated)
weighted_savings = loss_reduction_per_home * conversion_rate
net_result = weighted_savings - avg_prog_cost

with col_left:
    st.markdown("### 1. Cost to Run Program")
    st.latex(rf'''
        \${faura_cost:,.0f} + (\${total_incentives:,.0f} \times {conversion_rate*100:.0f}\%) = \boxed{{\textbf{{\${avg_prog_cost:,.0f}}}}}
    ''')
    st.info(f"👉 **Hurdle Rate:** You spend **\${avg_prog_cost:,.0f}** per home to run this.")

with col_right:
    st.markdown("### 2. Expected Loss Avoidance")
    result_color = "green" if net_result > 0 else "red"
    result_word = "PROFIT" if net_result > 0 else "LOSS"
    
    st.markdown(f"""
    **Result:** At this risk level, you **avoid \${weighted_savings:,.0f}** in expected losses per home.
    
    Since **\${weighted_savings:,.0f}** (Avoided Loss) - **\${avg_prog_cost:,.0f}** (Cost) = :{result_color}[**\${net_result:,.0f}**], the program generates a **{result_word}**.
    """)