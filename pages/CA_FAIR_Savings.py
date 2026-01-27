import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="FAIR Plan Discount Calculator", layout="wide")

st.title("🏛️ California FAIR Plan: Discount Validator")
st.markdown("""
**The "TurboTax" for Wildfire Compliance:** This tool digitizes the **California 'Safer from Wildfires'** checklist. 
It calculates the immediate premium reduction available to the homeowner for verified mitigation actions.
""")

# --- INPUTS ---
col1, col2 = st.columns(2)

with col1:
    st.header("1. Policy Details")
    base_premium = st.number_input("Annual FAIR Plan Premium ($)", value=4500, step=100)
    wildfire_portion = st.slider("Wildfire Risk Portion of Premium (%)", 50, 100, 85) / 100
    risk_premium = base_premium * wildfire_portion
    st.info(f"📍 **Addressable Wildfire Premium:** ${risk_premium:,.0f}")

with col2:
    st.header("2. Mitigation Checklist (Verify)")
    
    st.markdown("### 🌲 Immediate Surroundings")
    c1 = st.checkbox("Zone 0 (5ft Non-Combustible)", help="No mulch/wood within 5ft")
    c2 = st.checkbox("Decks Cleared", help="No debris under decks")
    c3 = st.checkbox("Fencing (Non-Combustible)", help="No wood fences attached to house")
    c4 = st.checkbox("Sheds Moved (>30ft)", help="Combustibles away from home")
    c5 = st.checkbox("Defensible Space Compliant", help="Trees trimmed, brush cleared")
    
    surroundings_score = sum([c1, c2, c3, c4, c5])
    
    st.markdown("### 🏠 Structure Hardening")
    s1 = st.checkbox("Class A Fire Rated Roof")
    s2 = st.checkbox("Enclosed Eaves")
    s3 = st.checkbox("Ember-Resistant Vents")
    s4 = st.checkbox("Multi-Pane Windows")
    s5 = st.checkbox("6-inch Vertical Clearance")
    
    structure_score = sum([s1, s2, s3, s4, s5])

# --- DISCOUNT LOGIC (Estimates based on filings) ---
# FAIR Plan discounts often work in tiers. This is a simplified proxy.
discount_pct = 0.0

# 1. Surroundings Discount (Usually ~5% if ALL are met)
if surroundings_score == 5:
    discount_pct += 0.05
else:
    # Partial credit logic (optional, usually it's all-or-nothing for the tier)
    discount_pct += (surroundings_score * 0.005) 

# 2. Structure Discount (Usually ~10% if ALL are met)
if structure_score == 5:
    discount_pct += 0.10
else:
    discount_pct += (structure_score * 0.015)

# 3. Prop 103 / Completion Bonus
if surroundings_score == 5 and structure_score == 5:
    discount_pct += 0.02 # Bonus for doing everything

# Cap at plausible max (approx 20%)
discount_pct = min(discount_pct, 0.20)

# --- RESULTS ---
savings = risk_premium * discount_pct
new_premium = base_premium - savings

st.markdown("---")
st.subheader("💰 Financial Impact")

metric1, metric2, metric3 = st.columns(3)
with metric1:
    st.metric("Current Annual Premium", f"${base_premium:,.0f}")
with metric2:
    st.metric("New Annual Premium", f"${new_premium:,.0f}", delta=f"-{discount_pct*100:.1f}%")
with metric3:
    st.metric("Cash Savings (Per Year)", f"${savings:,.0f}", delta="Money Back")

# --- VISUALIZATION ---
fig = go.Figure()

fig.add_trace(go.Bar(
    y=['Premium Cost'],
    x=[new_premium],
    name='New Premium',
    orientation='h',
    marker_color='#4B604D',
    text=f"${new_premium:,.0f}",
    textposition='auto'
))

fig.add_trace(go.Bar(
    y=['Premium Cost'],
    x=[savings],
    name='Savings',
    orientation='h',
    marker_color='#EF553B',
    text=f"SAVINGS: ${savings:,.0f}",
    textposition='auto'
))

fig.update_layout(barmode='stack', title="Premium Breakdown", height=200)
st.plotly_chart(fig, use_container_width=True)

if savings > 1000:
    st.success("🚀 **High Impact:** The savings from these mitigations ($1,000+) likely pay for the upgrade costs within 1-3 years!")