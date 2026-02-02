import streamlit as st

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="FAIR Plan Discount Calculator", layout="wide")

# --- STANDARDIZED LOGIN BLOCK ---
def check_password():
    """Returns `True` if the user had the correct password."""
    if st.session_state.get("password_correct", False):
        return True

    st.title("🔒 Faura Portfolio Map")
    
    with st.form("login_form"):
        st.write("Please enter the access code to view the map.")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log In")
        
        if submitted:
            if password == "Faura2026":
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Password incorrect")
    return False

if not check_password():
    st.stop()


# --- MAIN APP CONTENT ---
st.title("🏛️ California FAIR Plan: Discount Calculator")
st.markdown("""
This calculator estimates the itemized premium reduction available to homeowners on the CA FAIR plan.
It separates savings into **Surroundings (Bucket A)** and **Structure (Bucket B)** to highlight eligibility blockers.
""")

# --- SIDEBAR: POLICY INPUTS ---
st.sidebar.header("Policy Details")
base_premium = st.sidebar.number_input("Total Annual FAIR Plan Premium ($)", value=4500, step=100)
wildfire_load = st.sidebar.slider("Wildfire Portion of Premium (%)", 50, 100, 85, help="Since FAIR Plan is primarily for fire, this is usually high (85-95%).") / 100

# Calculate the split
wildfire_portion_initial = base_premium * wildfire_load
other_portion = base_premium - wildfire_portion_initial

# --- LAYOUT: METRICS CONTAINER (Top) ---
metrics_container = st.container()

st.markdown("---")

# --- LAYOUT: CHECKLIST COLUMNS (Bottom) ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("1. Community & Surroundings (Bucket A)")
    st.info("✅ **Always Eligible:** These discounts are available regardless of roof type.")
    
    # Community Discount
    st.markdown("**Community Level**")
    is_firewise = st.checkbox("📍 Located in Firewise USA Site", help="Estimated ~5% discount")
    
    st.markdown("**Immediate Surroundings (Zone 0-5)**")
    st.caption("Each item estimated at ~0.6% discount")
    c1 = st.checkbox("Zone 0 (5ft Non-Combustible)", help="No mulch/wood within 5ft")
    c2 = st.checkbox("Decks Cleared", help="No debris under decks")
    c3 = st.checkbox("Fencing (Non-Combustible)", help="No wood fences attached to house")
    c4 = st.checkbox("Sheds Moved (>30ft)", help="Combustibles away from home")
    c5 = st.checkbox("Defensible Space Compliant", help="Trees trimmed, brush cleared")
    
    surroundings_count = sum([c1, c2, c3, c4, c5])

with col2:
    st.subheader("2. Structure Hardening (Bucket B)")
    
    # --- THE LOGIC GATE ---
    # We ask the disqualifying question first.
    has_wood_shake = st.toggle("⚠️ Does home have a Wood Shake Roof?", value=False)
    
    if has_wood_shake:
        st.error("⛔ **DISQUALIFIED:** Wood roofs are ineligible for Structure discounts.")
        st.caption("Action Required: Replace roof to unlock ~7-10% savings below.")
        disable_structure = True
    else:
        st.success("✅ **ELIGIBLE:** Roof type qualifies for Structure discounts.")
        disable_structure = False
    
    st.markdown("**Structure Checklist**")
    st.caption("All items typically required for full 10% Bundle")
    
    # If Wood Shake is YES, we disable these boxes so they can't be clicked.
    s1 = st.checkbox("Class A Fire Rated Roof", value=True if not has_wood_shake else False, disabled=True, help="Must be verified Class A")
    s2 = st.checkbox("Enclosed Eaves", disabled=disable_structure)
    s3 = st.checkbox("Ember-Resistant Vents", disabled=disable_structure)
    s4 = st.checkbox("Multi-Pane Windows", disabled=disable_structure)
    s5 = st.checkbox("6-inch Vertical Clearance", disabled=disable_structure)
    
    if has_wood_shake:
        structure_count = 0
    else:
        # We assume s1 is "checked" if they passed the gate, but we only count user actions s2-s5 + the roof credit
        structure_count = sum([s1, s2, s3, s4, s5])

# --- CALCULATION LOGIC ---
discount_accumulated = 0.0

# 1. Community Discount (~5%)
if is_firewise:
    discount_accumulated += 0.05

# 2. Immediate Surroundings (~0.6% each, max 3%)
discount_accumulated += (surroundings_count * 0.006)

# 3. Structure Hardening (~1.4% each, max 7%)
discount_accumulated += (structure_count * 0.014)

# 4. Completion Bonus (~1.4% bonus to reach 16.4% if ALL items are done)
# Note: If wood shake is True, structure_count is 0, so is_complete is False.
is_complete = (surroundings_count == 5) and (structure_count == 5)
if is_complete:
    discount_accumulated += 0.014 # Bonus kicker

# Cap total discount at FAIR Plan specific max (16.4%)
final_discount_pct = min(discount_accumulated, 0.164)

# Financials
savings = wildfire_portion_initial * final_discount_pct
wildfire_portion_new = wildfire_portion_initial - savings
new_total_premium = other_portion + wildfire_portion_new

# --- POPULATE METRICS (Top) ---
with metrics_container:
    # Row 1: The Breakdown
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        st.metric("Total Base Premium", f"${base_premium:,.0f}", help="Total amount you pay today")
    
    with c2:
        st.metric("Wildfire Risk Portion", f"${wildfire_portion_initial:,.0f}", help="The specific portion of the bill eligible for discounts")
        
    with c3:
        # The Hero Metric
        st.metric("New Wildfire Portion", f"${wildfire_portion_new:,.0f}", delta=f"-${savings:,.0f}", delta_color="inverse")
        
    with c4:
        st.metric("New Total Annual Bill", f"${new_total_premium:,.0f}", delta=f"-{final_discount_pct*100:.1f}% Risk Portion Drop")

    # Progress/Bonus Notification
    if has_wood_shake:
        st.warning("⚠️ **Structure Savings Locked:** Replace wood roof to unlock maximum potential.")
    elif is_complete:
        st.success("✅ **MAXIMUM SAVINGS UNLOCKED:** You have reached the 16.4% Cap.")
    elif (surroundings_count + structure_count) > 0:
        items_done = surroundings_count + structure_count
        st.progress(items_done / 10)
        st.caption(f"Complete {10 - items_done} more items to unlock the Completion Bonus.")

# --- CITATION & DISCLAIMER FOOTER ---
st.markdown("---")
st.warning("""
**Disclaimer:** All discount percentages are **estimates** based on the 16.4% maximum defined in the FAIR Plan "Safer from Wildfires" filing. 
Actual credits may vary based on your specific location, policy limits, and final underwriting. 
**Wood Shake Roofs:** Homes with wood shake roofs are generally ineligible for structural discounts until the roof is replaced with a Class A rated material.
""")
st.caption("""
**Source Methodology:** Discount estimates are calibrated to the **California FAIR Plan Discount Guide (November 2025)**, 
which caps total wildfire mitigation discounts at 16.4%.
""")