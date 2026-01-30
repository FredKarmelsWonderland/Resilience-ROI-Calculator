import streamlit as st
# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="FAIR Plan Discount Calculator", layout="wide")

# --- 2. STANDARDIZED LOGIN BLOCK (Copy this to all pages) ---
def check_password():
    """Returns `True` if the user had the correct password."""
    # Check if the password is already correct in the session
    if st.session_state.get("password_correct", False):
        return True

    # Show input in the MAIN AREA (not sidebar)
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
    st.stop()  # Stop execution if password is wrong


st.title("🏛️ California FAIR Plan: Discount Calculator")
st.markdown("""
This calculator estimates the itemized premium reduction available to homeowners on the CA FAIR plan for verified mitigation actions.
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
    st.subheader("1. Community & Surroundings")
    
    # Community Discount (Calibrated to FAIR Plan ~5%)
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
    st.subheader("2. Structure Hardening")
    st.caption("Each item estimated at ~1.4% discount")
    
    s1 = st.checkbox("Class A Fire Rated Roof")
    s2 = st.checkbox("Enclosed Eaves")
    s3 = st.checkbox("Ember-Resistant Vents")
    s4 = st.checkbox("Multi-Pane Windows")
    s5 = st.checkbox("6-inch Vertical Clearance")
    
    structure_count = sum([s1, s2, s3, s4, s5])

# --- CALCULATION LOGIC (Calibrated to 16.4% Max) ---
discount_accumulated = 0.0

# 1. Community Discount (~5%)
if is_firewise:
    discount_accumulated += 0.05

# 2. Immediate Surroundings (~0.6% each, max 3%)
discount_accumulated += (surroundings_count * 0.006)

# 3. Structure Hardening (~1.4% each, max 7%)
discount_accumulated += (structure_count * 0.014)

# 4. Completion Bonus (~1.4% bonus to reach 16.4% if ALL items are done)
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
        # The Hero Metric: Showing the Wildfire portion shrinking
        st.metric("New Wildfire Portion", f"${wildfire_portion_new:,.0f}", delta=f"-${savings:,.0f}", delta_color="inverse")
        
    with c4:
        st.metric("New Total Annual Bill", f"${new_total_premium:,.0f}", delta=f"-{final_discount_pct*100:.1f}% Risk Portion Drop")

    # Progress/Bonus Notification
    if is_complete:
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
You must inform your insurance agent or broker to request these discounts. 
Documentation (photos, receipts, or inspection reports) is required to verify improvements.
""")
st.caption("""
**Source Methodology:** Discount estimates are calibrated to the **California FAIR Plan Discount Guide (November 2025)**, 
which caps total wildfire mitigation discounts at 16.4%.
[View Official FAIR Plan Discount Document](https://www.cfpnet.com/wp-content/uploads/2025/11/Discounts-for-Dwelling-Fire-Commercial-Policies-2025.11.15.pdf)
""")