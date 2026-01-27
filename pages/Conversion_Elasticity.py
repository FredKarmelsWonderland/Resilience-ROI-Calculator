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

st.title("📈 Conversion Elasticity: Loss Reduction Analysis")
st.markdown("""
**The "Claims Slide":** This chart isolates the **Expected Annual Losses** to show exactly how claim volume decreases with every 1% of homeowner adoption.
It answers: *"If we get 5%, 10%, or 20% of people to engage, how much risk do we remove from the books?"*
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
# Note: We don't strictly need Premium/Expenses for "Expected Losses", but good to keep for context if needed later.
avg_tiv = currency_input("Avg TIV per Home", 1000000)

st.sidebar.markdown("---")
st.sidebar.header("2. Risk Inputs")
incident_prob = st.sidebar.number_input("Annual Incident Prob (%)", value=1.0, step=0.01, format="%.2f") / 100
mdr_unmitigated = st.sidebar.number_input("MDR (Unmitigated) %", value=80.0, step=0.1) / 100
mdr_mitigated = st.sidebar.number_input("MDR (Mitigated) %", value=30.0, step=0.1) / 100

st.sidebar.markdown("---")
st.sidebar.header("3. Faura Program Inputs")
st.sidebar.info("ℹ️ Analyzing Conversion from 0% to 20%")
# We technically don't need costs for a pure "Losses" chart, but keeping them implies we know the "Net" story exists.

# --- CALCULATION LOGIC ---
def calculate_losses(rate):
    # Unmitigated Baseline
    sq_losses = n_homes * avg_tiv * incident_prob * mdr_unmitigated
    
    # With Faura Conversion
    n_converted = n_homes * rate
    n_unconverted = n_homes * (1 - rate)
    
    loss_unconverted = n_unconverted * avg_tiv * incident_prob * mdr_unmitigated
    loss_converted = n_converted * avg_tiv * incident_prob * mdr_mitigated
    
    faura_losses = loss_unconverted + loss_converted
    
    return sq_losses, faura_losses

# --- GENERATE DATA (0% to 20% in 1% increments) ---
x_range = np.linspace(0, 0.20, 21) # 0.00, 0.01, ... 0.20
data = []

for r in x_range:
    sq, faura = calculate_losses(r)
    data.append({
        "Rate": r,
        "Label": f"{int(r*100)}%",
        "SQ_Losses": sq,
        "Faura_Losses": faura,
        "Saved": sq - faura
    })

df = pd.DataFrame(data)

# --- METRICS ROW ---
col1, col2, col3 = st.columns(3)
with col1:
    # Baseline Losses
    st.metric("Baseline Annual Losses (0% Conv)", f"${df.iloc[0]['SQ_Losses']:,.0f}")
with col2:
    # Savings at 10%
    idx_10 = 10
    saved_10 = df.iloc[idx_10]['Saved']
    st.metric("Losses Prevented at 10% Conv", f"${saved_10:,.0f}", delta="Risk Removed")
with col3:
    # Savings at 20%
    idx_20 = 20
    saved_20 = df.iloc[idx_20]['Saved']
    st.metric("Losses Prevented at 20% Conv", f"${saved_20:,.0f}", delta="Risk Removed")

# --- PLOTLY LINE CHART ---
fig = go.Figure()

# 1. Status Quo Line (Flat Dashed)
fig.add_trace(go.Scatter(
    x=df['Rate'],
    y=df['SQ_Losses'],
    mode='lines',
    name='Status Quo Expected Losses',
    line=dict(color='#EF553B', width=3, dash='dash')
))

# 2. Faura Losses Line (Downward Slope)
fig.add_trace(go.Scatter(
    x=df['Rate'],
    y=df['Faura_Losses'],
    mode='lines+markers', # Add markers to show the 1% ticks clearly
    name='Expected Losses with Faura',
    line=dict(color='#4B604D', width=4),
    marker=dict(size=8)
))

# 3. Add Annotation for the Drop
# Show the arrow at the 20% mark
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
        range=[-0.005, 0.205] # Add padding
    ),
    hovermode="x unified",
    template="plotly_white",
    height=600,
    legend=dict(yanchor="bottom", y=0.01, xanchor="left", x=0.01)
)

st.plotly_chart(fig, use_container_width=True)

# --- FOOTER ---
loss_per_1_percent = df.iloc[1]['Saved'] # Savings at 1%
st.info(f"""
**The Power of 1%:** For every **1%** of the portfolio that converts, you remove **${loss_per_1_percent:,.0f}** in expected annual claims from the books.
* At **5%** conversion, that sums to **${df.iloc[5]['Saved']:,.0f}**.
* At **15%** conversion, that sums to **${df.iloc[15]['Saved']:,.0f}**.
""")