import streamlit as st
import pandas as pd
import plotly.graph_objects as go

# --- PASSWORD PROTECTION ---
def check_password():
    """Returns `True` if the user had the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == "Faura2026":
            st.session_state["password_correct"] = True
            del st.session_state["password"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

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
    st.stop()

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="Faura ROI Calculator", layout="wide")

st.title("🔥 Faura Underwriting Profit Calculator")
st.markdown("### Status Quo vs. Active Mitigation")

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
        st.sidebar.error(f"Please enter a valid number for {label}")
    return clean_val

# --- SIDEBAR: INPUT VARIABLES ---
st.sidebar.header("1. Portfolio Inputs")

n_homes = st.sidebar.number_input("Number of Homes", value=100, step=1)
avg_premium = currency_input("Avg Premium per Home", 10000)
avg_tiv = currency_input("Avg TIV per Home", 1000000)

expense_ratio_input = st.sidebar.number_input("Expense Ratio (%)", value=15.0, step=0.1, format="%.2f")
expense_ratio = expense_ratio_input / 100

st.sidebar.markdown("---")
st.sidebar.header("2. Risk Inputs")

incident_prob_input = st.sidebar.number_input("Annual Incident Probability (%)", value=1.0, step=0.01, format="%.2f")
incident_prob = incident_prob_input / 100

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
def calculate_metrics():
    total_premium = n_homes * avg_premium
    total_uw_expense = total_premium * expense_ratio

    # Status Quo
    sq_losses = n_homes * avg_tiv * incident_prob * mdr_unmitigated
    sq_profit = total_premium - (total_uw_expense + sq_losses)

    # With Faura
    n_converted = n_homes * conversion_rate
    n_unconverted = n_homes * (1 - conversion_rate)
    faura_loss_unconverted = n_unconverted * avg_tiv * incident_prob * mdr_unmitigated
    faura_loss_converted = n_converted * avg_tiv * incident_prob * mdr_mitigated
    faura_total_losses = faura_loss_unconverted + faura_loss_converted

    total_faura_fee = n_homes * faura_cost
    total_gift_cards = n_converted * gift_card
    total_discounts = n_converted * premium_discount
    
    faura_total_cost = total_uw_expense + faura_total_losses + total_faura_fee + total_gift_cards + total_discounts
    faura_profit = total_premium - faura_total_cost

    return {
        "sq_profit": sq_profit,
        "sq_losses": sq_losses,
        "sq_expenses": total_uw_expense,
        "faura_profit": faura_profit,
        "faura_losses": faura_total_losses,
        "faura_program_cost": total_faura_fee,
        "faura_incentives": total_gift_cards + total_discounts,
        "faura_expenses": total_uw_expense,
        "total_premium": total_premium
    }

metrics = calculate_metrics()

# --- DASHBOARD LAYOUT ---

# ROW 1: High Level Portfolio Profit
st.subheader("1. Portfolio Impact")
col1, col2, col3, col4 = st.columns(4)
profit_diff = metrics['faura_profit'] - metrics['sq_profit']

with col1:
    st.metric(label="Status Quo Profit", value=f"${metrics['sq_profit']:,.0f}")
with col2:
    st.metric(label="With Faura Profit", value=f"${metrics['faura_profit']:,.0f}", delta=f"${profit_diff:,.0f}")
with col3:
    st.metric(label="Net Improvement (Spread)", value=f"${profit_diff:,.0f}", delta_color="off")
with col4:
    program_investment = metrics['faura_program_cost'] + metrics['faura_incentives']
    if program_investment > 0:
        roi = (profit_diff / program_investment) * 100
        st.metric(label="ROI on Mitigation Spend", value=f"{roi:,.1f}%")
    else:
        st.metric(label="ROI on Mitigation Spend", value="0%")

st.markdown("---")

# ROW 2: Program Economics (THE NEW WIDGETS)
st.subheader("2. Program Economics Breakdown")
m1, m2, m3 = st.columns(3)

# Calculate the new values
claims_saved = metrics['sq_losses'] - metrics['faura_losses']
total_program_cost = metrics['faura_program_cost'] + metrics['faura_incentives']
net_project_roi_dollars = claims_saved - total_program_cost

with m1:
    st.metric(
        label="🛡️ Claims Saved", 
        value=f"${claims_saved:,.0f}", 
        help="Gross reduction in expected losses due to mitigation."
    )
with m2:
    st.metric(
        label="🧾 Total Program Cost", 
        value=f"${total_program_cost:,.0f}", 
        help="Includes Faura Fees + Gift Cards + Premium Discounts.",
        delta_color="inverse" # Standard Streamlit: Red implies 'Cost'
    )
with m3:
    st.metric(
        label="💰 Net Project ROI ($)", 
        value=f"${net_project_roi_dollars:,.0f}", 
        delta="Net Benefit",
        help="Claims Saved minus Program Cost."
    )

st.markdown("---")

# Bar Chart
fig = go.Figure()
fig.add_trace(go.Bar(
    x=['Status Quo'], y=[metrics['sq_profit']], name='Status Quo',
    text=[f"${metrics['sq_profit']:,.0f}"], textposition='auto',
    textfont=dict(size=20, color="white", family="Arial Black"), marker_color='#EF553B'
))
fig.add_trace(go.Bar(
    x=['With Faura'], y=[metrics['faura_profit']], name='With Faura',
    text=[f"${metrics['faura_profit']:,.0f}"], textposition='auto',
    textfont=dict(size=20, color="white", family="Arial Black"), marker_color='#4B604D'
))
fig.update_layout(
    title=dict(text="Net Underwriting Profit Comparison", font=dict(size=26)),
    xaxis=dict(title="Scenario", title_font=dict(size=22), tickfont=dict(size=18)),
    yaxis=dict(title="Profit ($)", title_font=dict(size=22), tickfont=dict(size=18)),
    template="plotly_white", height=500
)
st.plotly_chart(fig, use_container_width=True)

# Data Table
st.subheader("Financial Breakdown")
table_data = {
    "Line Item": ["Gross Written Premium", "(-) Underwriting Expenses", "(-) Expected Incident Losses", "(-) Faura Program Fees", "(-) Incentives (Cards + Discounts)", "= NET PROFIT"],
    "Status Quo": [metrics['total_premium'], -metrics['sq_expenses'], -metrics['sq_losses'], 0, 0, metrics['sq_profit']],
    "With Faura": [metrics['total_premium'], -metrics['faura_expenses'], -metrics['faura_losses'], -metrics['faura_program_cost'], -metrics['faura_incentives'], metrics['faura_profit']]
}
df = pd.DataFrame(table_data)
def fmt(x): return f"${x:,.0f}"
df["Status Quo"] = df["Status Quo"].apply(fmt)
df["With Faura"] = df["With Faura"].apply(fmt)

def highlight_total(row):
    if row.name == 5: return ['font-weight: bold; background-color: #f0f2f6; color: black'] * len(row)
    return [''] * len(row)

styled_df = df.style.apply(highlight_total, axis=1)
st.table(styled_df)

# Glossary
st.markdown("---")
with st.expander("ℹ️ Glossary & Formula Logic (Click to Expand)", expanded=False):
    st.markdown("""
    ### 1. Variable Definitions
    * **MDR (Mean Damage Ratio):** The average % of the home destroyed if a Incident occurs.
    * **Incident Probability:** The annual chance (in %) that a home catches Incident.
    * **TIV:** Total Insurable Value (Replacement Cost).
    """)
    st.latex(r'''
        \text{Profit} = \text{Gross Premium} - \Big( \text{UW Expenses} + \text{Expected Losses} + \text{Faura Costs} + \text{Incentives} \Big)
    ''')