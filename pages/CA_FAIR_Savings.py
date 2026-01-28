import streamlit as st
import plotly.graph_objects as go

st.set_page_config(page_title="FAIR Plan Discount Calculator", layout="wide")

st.title("🏛️ California FAIR Plan: Discount Validator")
st.markdown("""
**The "TurboTax" for Wildfire Compliance:** This tool digitizes the **California 'Safer from Wildfires'** checklist. 
It calculates the itemized premium reduction available to the homeowner for verified mitigation actions.
""")

# --- SIDEBAR: POLICY DETAILS ---
st.sidebar.header("Policy Details")
base_premium = st.sidebar.number_input("Current Annual FAIR Plan Premium ($)", value=4500, step=100)
wildfire_load = st.sidebar.slider("Wildfire Portion of Premium (%)", 50, 100, 85) / 100
risk_premium = base_premium * wildfire_load

st.sidebar.info(f"📍 **Addressable Wildfire Premium:** ${risk_premium:,.0f}")

# --- MAIN COLUMNS ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Community & Surroundings")
    
    # Community Discount (The Big One)
    st.markdown("**Community Level**")
    is_firewise = st.checkbox("📍 Located in Firewise USA Site", help="Automatic ~10% discount")
    
    st.markdown("**Immediate Surroundings (Zone 0-5)**")
    st.caption("Each item is estimated at ~1% discount")
    c1 = st.checkbox("Zone 0 (5ft Non-Combustible)", help="No mulch/wood within 5ft")
    c2 = st.checkbox("Decks Cleared", help="No debris under decks")
    c3 = st.checkbox("Fencing (Non-Combustible)", help="No wood fences attached to house")
    c4 = st.checkbox("Sheds Moved (>30ft)", help="Combustibles away from home")
    c5 = st.checkbox("Defensible Space Compliant", help="Trees trimmed, brush cleared")
    
    surroundings_count = sum([c1, c2, c3, c4, c5])

with col2:
    st.subheader("2. Structure Hardening")
    st.caption("Each item is estimated at ~2% discount")
    
    s1 = st.checkbox("Class A Fire Rated Roof")
    s2 = st.checkbox("Enclosed Eaves")
    s3 = st.checkbox("Ember-Resistant Vents")
    s4 = st.checkbox("Multi-Pane Windows")
    s5 = st.checkbox("6-inch Vertical Clearance")
    
    structure_count = sum([s1, s2, s3, s4, s5])

# --- CALCULATION LOGIC ---
discount_accumulated = 0.0

# 1. Community Discount (approx 10%)
if is_firewise:
    discount_accumulated += 0.10

# 2. Immediate Surroundings (approx 1% each, max 5%)
discount_accumulated += (surroundings_count * 0.01)

# 3. Structure Hardening (approx 2% each, max 10%)
discount_accumulated += (structure_count * 0.02)

# 4. Completion Bonus (approx 2-5% bonus if ALL 10 property items are done)
is_complete = (surroundings_count == 5) and (structure_count == 5)
if is_complete:
    discount_accumulated += 0.03 # Bonus kicker
    st.balloons() # Visual reward for "100% Verified"

# Cap total discount at regulatory max (usually around 25-29%)
final_discount_pct = min(discount_accumulated, 0.29)

# Financials
annual_savings = risk_premium * final_discount_pct
new_premium = base_premium - annual_savings

# --- RESULTS DASHBOARD ---
st.markdown("---")

# Metrics
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Current Annual Premium", f"${base_premium:,.0f}", help="The base premium before mitigation")
with m2:
    st.metric("New Annual Premium", f"${new_premium:,.0f}", delta=f"-{final_discount_pct*100:.1f}% Reduction", delta_color="normal")
with m3:
    st.metric("Total Annual Savings", f"${annual_savings:,.0f}", delta="Money Back")

# Progress Bar for "Completion Bonus"
if not is_complete:
    items_done = surroundings_count + structure_count
    st.warning(f"⚠️ **Unlock the Bonus:** You have completed {items_done}/10 property items. Finish all 10 to unlock the extra 3% Completion Discount.")
    st.progress(items_done / 10)
else:
    st.success("✅ **MAXIMUM SAVINGS UNLOCKED:** You have qualified for the Completion Bonus.")

# Visualization
fig = go.Figure()

# Stacked Bar: Premium Cost vs Savings
fig.add_trace(go.Bar(
    y=['Total Cost'],
    x=[new_premium],
    name='New Premium',
    orientation='h',
    marker_color='#4B604D',
    text=f"${new_premium:,.0f}",
    textposition='auto'
))

fig.add_trace(go.Bar(
    y=['Total Cost'],
    x=[annual_savings],
    name='Savings',
    orientation='h',
    marker_color='#EF553B',
    text=f"SAVINGS: ${annual_savings:,.0f}",
    textposition='auto'
))

fig.update_layout(
    title="Premium Breakdown", 
    barmode='stack', 
    height=250,
    xaxis_title="Dollars ($)",
    yaxis=dict(showticklabels=False)
)

st.plotly_chart(fig, use_container_width=True)

# --- CITATION FOOTER ---
st.markdown("---")
st.caption("""
**Source Methodology:** Discount estimates are based on the **California Department of Insurance Regulation 2644.9** ("Safer from Wildfires"), 
which mandates insurers offer premium reductions for specific mitigation actions. 
The FAIR Plan's specific discount weights (approx. 10% for structure, 5% for surroundings, 5-10% for community) 
are derived from their 2023-2024 Rate Filings.
[Read the Official Regulation](https://www.insurance.ca.gov/01-consumers/105-type/95-guides/03-res/Safer-from-Wildfires.cfm)
""")