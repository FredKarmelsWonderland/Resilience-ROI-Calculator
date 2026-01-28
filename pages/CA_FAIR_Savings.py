import streamlit as st

st.set_page_config(page_title="FAIR Plan Discount Calculator", layout="wide")

st.title("🏛️ California FAIR Plan: Discount Validator")
st.markdown("""
**The "TurboTax" for Wildfire Compliance:** This tool digitizes the **California 'Safer from Wildfires'** checklist. 
It calculates the itemized premium reduction available to the homeowner for verified mitigation actions.
""")

# --- SIDEBAR: POLICY INPUTS ---
st.sidebar.header("Policy Details")
base_premium = st.sidebar.number_input("Current Annual FAIR Plan Premium ($)", value=4500, step=100)
wildfire_load = st.sidebar.slider("Wildfire Portion of Premium (%)", 50, 100, 85) / 100
risk_premium = base_premium * wildfire_load

st.sidebar.info(f"📍 **Addressable Wildfire Premium:** ${risk_premium:,.0f}")

# --- CHECKLIST STATE ---
# We define the layout top-down, but we need to capture the inputs first to calculate the metrics.
# To keep the UI clean (Metrics at Top), we use a container strategy or just render columns below.
# Streamlit renders sequentially, so to put metrics at the top that depend on checkboxes below, 
# we usually render the inputs first. However, to meet your layout request ("Widgets above checklist"),
# we will render the metrics container *first*, but we need to fetch the checkbox values.
# The standard way in Streamlit is to put checkboxes in columns below, and they auto-update the metrics at the top on rerun.

# --- 1. DEFINE CHECKBOXES (But render them lower down) ---
# We create placeholders or just use the logic that Streamlit re-runs the whole script on interaction.

# --- 2. LAYOUT: METRICS ROW (Top) ---
metrics_container = st.container()

st.markdown("---")

# --- 3. LAYOUT: CHECKLIST COLUMNS (Bottom) ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Community & Surroundings")
    
    # Community Discount
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

# 4. Completion Bonus (approx 3% bonus if ALL 10 property items are done)
is_complete = (surroundings_count == 5) and (structure_count == 5)
if is_complete:
    discount_accumulated += 0.03 # Bonus kicker

# Cap total discount at regulatory max (usually around 25-29%)
final_discount_pct = min(discount_accumulated, 0.29)

# Financials
annual_savings = risk_premium * final_discount_pct
new_premium = base_premium - annual_savings

# --- RENDER METRICS (Populate the top container) ---
with metrics_container:
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Current Annual Premium", f"${base_premium:,.0f}", help="The base premium before mitigation")
    with m2:
        st.metric("New Annual Premium", f"${new_premium:,.0f}", delta=f"-{final_discount_pct*100:.1f}% Reduction", delta_color="normal")
    with m3:
        st.metric("Total Annual Savings", f"${annual_savings:,.0f}", delta="Money Back")
    
    # Progress/Bonus Notification
    if is_complete:
        st.success("✅ **MAXIMUM SAVINGS UNLOCKED:** You have qualified for the Completion Bonus.")
    elif (surroundings_count + structure_count) > 0:
        items_done = surroundings_count + structure_count
        st.progress(items_done / 10)
        st.caption(f"Complete {10 - items_done} more items to unlock the Completion Bonus.")

# --- CITATION FOOTER ---
st.markdown("---")
st.caption("""
**Source Methodology:** Discount estimates are based on the **California FAIR Plan Discount Guide (November 2025)**.
The specific weighting (approx. 10% for structure, 5% for surroundings, 5-10% for community) is derived from the "Discounts for Dwelling Fire & Commercial Policies" filing.
[View Official FAIR Plan Discount Document](https://www.cfpnet.com/wp-content/uploads/2025/11/Discounts-for-Dwelling-Fire-Commercial-Policies-2025.11.15.pdf)
""")