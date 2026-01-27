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

st.title("📈 Conversion Elasticity: Interactive Loss Analysis")
st.markdown("""
**The "Claims Slide":** Hover over any point on the green line to see the exact financial breakdown for that conversion rate.
It answers: *"If we get X% participation, what is our Net ROI?"*
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
n_homes = st.sidebar.number_input("Number of Homes", value=100, step=100)
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
def calculate_scenario(rate):
    # Unmitigated Baseline (Status Quo)
    sq_losses = n_homes * avg_tiv * incident_prob * mdr_unmitigated
    
    # With Faura Conversion
    n_converted = n_homes * rate
    n_unconverted = n_homes * (1 - rate)
    
    loss_unconverted = n_unconverted * avg_tiv * incident_prob * mdr_unmitigated
    loss_converted = n_converted * avg_tiv * incident_prob * mdr_mitigated
    
    faura_losses = loss_unconverted + loss_converted
    
    # Calculate Costs (for ROI metrics)
    program_fixed_cost = n_homes * faura_cost
    incentive_variable_cost = n_converted * (gift_card + premium_discount)
    total_program_cost = program_fixed_cost + incentive_variable_cost
    
    return sq_losses, faura_losses, total_program_cost

# --- GENERATE DATA ---
x_range = np.linspace(0, 0.20, 21) # 0.00, 0.01, ... 0.20
data = []

for r in x_range:
    sq, faura, cost = calculate_scenario(r)
    saved = sq - faura
    net_roi = saved - cost
    roi_multiple = saved / cost if cost > 0 else 0
    
    data.append({
        "Rate": r,
        "Rate_Pct": f"{int(r*100)}%",
        "SQ_Losses": sq,
        "Faura_Losses": faura,
        "Saved": saved,
        "Program_Cost": cost,
        "Net_ROI": net_roi,
        "ROI_Mult": roi_multiple
    })

df = pd.DataFrame(data)

# --- METRICS ROW ---
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Baseline Annual Losses (0% Conv)", f"${df.iloc[0]['SQ_Losses']:,.0f}")
with col2:
    idx_20 = 20
    saved_20 = df.iloc[idx_20]['Saved']
    st.metric("Claims Prevented at 20% Conv", f"${saved_20:,.0f}", delta="Risk Removed")
with col3:
    net_20 = df.iloc[idx_20]['Net_ROI']
    roi_mult_20 = df.iloc[idx_20]['ROI_Mult']
    st.metric(f"Net Program ROI ({roi_mult_20:.1f}x)", f"${net_20:,.0f}", delta="Net Profit")

# --- PLOTLY LINE CHART WITH CUSTOM HOVER ---
fig = go.Figure()

# 1. Status Quo Line
fig.add_trace(go.Scatter(
    x=df['Rate'],
    y=df['SQ_Losses'],
    mode='lines',
    name='Status Quo',
    line=dict(color='#EF553B', width=3, dash='dash'),
    hovertemplate='<b>Status Quo</b><br>Losses: %{y:$,.0f}<extra></extra>'
))

# 2. Faura Losses Line (Interactive)
# We stack the extra data into a 'customdata' array so the hover tooltip can read it
custom_data = np.stack((df['Saved'], df['Program_Cost'], df['Net_ROI'], df['ROI_Mult']), axis=-1)

fig.add_trace(go.Scatter(
    x=df['Rate'],
    y=df['Faura_Losses'],
    mode='lines+markers',
    name='With Faura',
    line=dict(color='#4B604D', width=4),
    marker=dict(size=8),
    customdata=custom_data,
    hovertemplate=(
        "<b>Conversion: %{x:.0%}</b><br>" +
        "Expected Losses: %{y:$,.0f}<br>" +
        "-------------------<br>" +
        "📉 Claims Saved: %{customdata[0]:$,.0f}<br>" +
        "💸 Program Cost: %{customdata[1]:$,.0f}<br>" +
        "💰 <b>Net ROI: %{customdata[2]:$,.0f}</b><br>" +
        "🚀 Multiplier: %{customdata[3]:.1f}x" +
        "<extra></extra>" # Hides the secondary box on the side
    )
))

# 3. Add Annotation for the Drop at 20%
y_start = df.iloc[-1]['SQ_Losses']
y_end = df.iloc[-1]['Faura_Losses']
savings = y_start - y_end

fig.add_annotation(
    x=0.20,
    y=y_end,
    ax=0.20,
    ay=y_start,
    xref="x",
    yref="y",
    axref="x",
    ayref="y",
    text=f"<b>-${savings:,.0f}</b>",
    showarrow=True,
    arrowhead=2,
    arrowsize=1,
    arrowwidth=2,
    arrowcolor="green",
    font=dict(size=14, color="green")
)

fig.update_layout(
    title="Expected Portfolio Losses vs. Conversion Rate (0% - 20%)",
    xaxis_title="Conversion Rate (%)",
    yaxis_title="Annual Expected Losses ($)",
    xaxis=dict(
        tickmode='array',
        tickvals=x_range,
        ticktext=[f"{int(x*100)}%" for x in x_range],
        range=[-0.005, 0.205]
    ),
    hovermode="closest", # 'closest' works better for specific point tooltips than 'unified'
    template="plotly_white",
    height=600,
    legend=dict(yanchor="bottom", y=0.01, xanchor="left", x=0.01)
)

st.plotly_chart(fig, use_container_width=True)

# --- FOOTER ---
st.info("""
**How to use:** Hover your mouse over any green dot on the chart. 
A detailed popup will appear showing the **Savings**, **Cost**, and **Net ROI** for that specific participation rate.
""")