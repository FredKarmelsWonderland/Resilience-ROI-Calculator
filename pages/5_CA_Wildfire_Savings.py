import streamlit as st
import pandas as pd
import os

# --- 2. CONFIG & DATA LOADING ---
st.set_page_config(page_title="Carrier Discount Calculator", layout="wide")

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


@st.cache_data
def load_carrier_data():
    current_dir = os.path.dirname(__file__)
    # Robust loader to find the CSV regardless of exact filename typos
    all_files = os.listdir(current_dir)
    target_file = next((f for f in all_files if "DiscountTable" in f and f.endswith(".csv")), None)
    
    if target_file is None:
        st.error(f"❌ Error: Could not find any CSV file starting with 'DiscountTable' in {current_dir}")
        return pd.DataFrame()
    
    csv_path = os.path.join(current_dir, target_file)
    return pd.read_csv(csv_path)

df_base = load_carrier_data()

st.title("🏘️ California Carrier Discount Calculator")
st.markdown("""
**Compare Savings Across Major Insurers:** Includes **Mercury** Separation Tiers, **Chubb** System Tiers, and **Auto Club** Counting logic.
""")


# --- 4. TOP METRICS CONTAINER ---
# We create the container here so it sits at the top, but we fill it at the end of the script.
st.markdown("---")
metrics_container = st.container()
st.markdown("---")

# --- 5. SIDEBAR CONFIG ---
st.sidebar.header("1. Carrier Selection")
selected_carrier = st.sidebar.selectbox("Select Insurance Carrier", df_base['Carrier'].unique())

carrier_row = df_base[df_base['Carrier'] == selected_carrier].iloc[0]
logic_type = carrier_row['Logic_Type']
discount_basis = carrier_row['Discount_Basis']

# --- DYNAMIC RISK INPUTS ---
risk_inputs = {}
st.sidebar.header("2. Risk Factors")

if logic_type == "Farmers_Fireline":
    st.sidebar.warning("⚠️ **Farmers:** Discounts depend on Zesty's Fireline Score.")
    risk_inputs['fireline_score'] = st.sidebar.slider("Zesty's Fireline Score (0-30)", 0, 30, 4)

elif logic_type == "Allstate_Zesty":
    st.sidebar.warning("⚠️ **Allstate:** Discounts depend on Zesty Level.")
    risk_inputs['zesty_score'] = st.sidebar.slider("Zesty Level 1 Group (1-10)", 1, 10, 6)

elif logic_type == "Chubb_Complex" or logic_type == "PacSpec_Zone":
    st.sidebar.warning(f"⚠️ **{selected_carrier}:** Some items require High Hazard Zone.")
    risk_inputs['hazard_zone'] = st.sidebar.selectbox("Wildfire Hazard Zone", ["Moderate", "High", "Very High"], index=1)

elif logic_type == "Mercury_Complex":
    st.sidebar.warning("⚠️ **Mercury:** Mitigation discounts depend on Structure Separation.")
    risk_inputs['separation'] = st.sidebar.selectbox("Structure Separation Distance", ["<= 10 ft", "> 10 ft and < 30 ft", ">= 30 ft"], index=0)

else:
    st.sidebar.info("Standard logic applies.")

# --- PREMIUM INPUTS ---
st.sidebar.markdown("---")
st.sidebar.header("3. Premium Details")
base_premium = st.sidebar.number_input("Total Annual Premium ($)", value=3500, step=100)

# Determine Eligible Basis
applies_to_wildfire_only = any(x in discount_basis for x in ["Wildfire", "Brushfire", "Fire"])
if applies_to_wildfire_only:
    wildfire_load_pct = st.sidebar.slider(f"Wildfire Portion (%)", 10, 100, 60) / 100
    eligible_premium = base_premium * wildfire_load_pct
    basis_label = f"Wildfire Portion ({wildfire_load_pct*100:.0f}%)"
else:
    wildfire_load_pct = 1.0
    eligible_premium = base_premium
    basis_label = "Total Premium"

st.sidebar.metric("Discountable Basis", f"${eligible_premium:,.0f}")

# --- 6. TOOLTIP DICTIONARY ---
# Definitions from Table 1
tooltips = {
    "Firewise USA": "Firewise USA site in Good Standing.",
    "Fire Risk Community": "Listed by the California Board of Forestry and Fire Protection.",
    "Debris Removal": "Clearing of vegetation and debris from under decks.",
    "Zone 0 (5ft)": "Clearing of vegetation, debris, mulch, stored combustible materials, and any movable combustible objects, from the area within 5 feet of the building.",
    "Zone 0 (Improv)": "Incorporation of only noncombustible materials into property improvements, including fences and gates, within 5 feet of the property.",
    "30ft Clearance": "Removal or absence of combustible structures, including sheds and other outbuildings, from the area within 30 feet of the property.",
    "Section 4291": "Compliance with Section 4291 of the Public Resources Code, which requires defensible space around the building.",
    "Class A Roof": "Class A rated roofs are the most fire resistant.",
    "Enclosed Eaves": "Covering exposed rafters/eaves with wood or other materials to prevent embers from igniting the roof or reaching the attic space.",
    "Fire Res Vents": "Vents designed to provide airflow but prevent embers, flames, or intense heat from reaching the attic or crawl spaces.",
    "Multi-Pane Windows": "When closed, these cover the entire window and do not have openings, preventing fire from entering the home.",
    "6-inch Vert Space": "Create at least six inches of noncombustible vertical clearance at the bottom of the exterior surface to prevent ground fires from climbing walls.",
    "IBHS Std": "Home designated as Wildfire Prepared by the Insurance Institute for Business & Home Safety.",
    "IBHS Plus": "Home designated as Wildfire Prepared PLUS by the Insurance Institute for Business & Home Safety."
}

# --- 7. LOGIC ENGINE ---
def get_item_discount(item_key, base_val):
    """Calculates discount for a SINGLE item based on risk inputs."""
    
    # 1. AUTO CLUB (Count Logic)
    if logic_type == "ACSC_Count" and item_key not in ["Firewise USA", "Fire Risk Community"]:
        return 0.0 

    # 2. FARMERS (Zesty Fireline)
    if logic_type == "Farmers_Fireline":
        score = risk_inputs.get('fireline_score', 4)
        if score < 4: 
            if item_key in ["Firewise USA", "Fire Risk Community"]: return 0.3
            if base_val > 0: return 0.1 
        return base_val

    # 3. ALLSTATE (Zesty)
    if logic_type == "Allstate_Zesty":
        score = risk_inputs.get('zesty_score', 6)
        if score < 6: 
            if item_key in ["Firewise USA", "Fire Risk Community"]: return 0.4
            if base_val >= 0.2: return 0.1
        return base_val

    # 4. CHUBB (Hazard Logic - Note o)
    if logic_type == "Chubb_Complex":
        zone = risk_inputs.get('hazard_zone', 'High')
        is_high = zone in ["High", "Very High"]
        
        # Items requiring High Zone: Vents, Non-Comb Deck, Def Space Adj
        if item_key in ["Fire Res Vents", "Non_Comb_Ext", "Def_Space_Adj"]:
            return base_val if is_high else 0.0
        return base_val

    # 5. PACIFIC SPECIALTY (Hazard Logic)
    if logic_type == "PacSpec_Zone":
        zone = risk_inputs.get('hazard_zone', 'High')
        is_high = zone in ["High", "Very High"]
        if item_key == "Fire Res Vents":
            return 2.0 if is_high else 0.0
        return base_val

    # 6. MERCURY (Separation Logic for Mitigation Tiers)
    if logic_type == "Mercury_Complex":
        sep = risk_inputs.get('separation', "<= 10 ft")
        
        # Mercury Mitigation Standard (Notes g, h, i)
        if item_key == "Merc_Mit_Std":
            if sep == "<= 10 ft": return 5.0
            elif sep == ">= 30 ft": return 25.0
            else: return 8.0
            
        # Mercury Mitigation Plus (Notes g, h, i + k)
        if item_key == "Merc_Mit_Plus":
            if sep == "<= 10 ft": return 8.0
            elif sep == ">= 30 ft": return 33.0
            else: return 25.0
            
    return base_val

# --- 8. CHECKLIST UI ---
st.subheader(f"Mitigation Actions for {selected_carrier}")
col1, col2 = st.columns(2)

checked_items = []
accumulated_discount_pct = 0.0

def discount_item(label, csv_key, col, tooltip_key=None):
    base = carrier_row.get(csv_key, 0.0)
    final_val = get_item_discount(csv_key, base)
    
    # Text formatting
    display_text = label
    if logic_type == "ACSC_Count" and csv_key not in ["Firewise USA", "Fire Risk Community"]:
        display_text += " (Bundle Item)"
    elif final_val > 0:
        display_text += f" ({final_val:.2f}%)"
    
    # Get tooltip
    help_text = tooltips.get(tooltip_key, "") if tooltip_key else None

    if col.checkbox(display_text, key=csv_key, help=help_text):
        checked_items.append(csv_key)
        return final_val
    return 0.0

with col1:
    st.markdown("#### 🏡 Property Level")
    accumulated_discount_pct += discount_item("1. Debris Removal Under Deck", "Debris Removal", st, "Debris Removal")
    accumulated_discount_pct += discount_item("2. Zone 0: 5ft Non-Combustible", "Zone 0 (5ft)", st, "Zone 0 (5ft)")
    accumulated_discount_pct += discount_item("3. Zone 0: Property Improvements", "Zone 0 (Improv)", st, "Zone 0 (Improv)")
    accumulated_discount_pct += discount_item("4. 30ft Combustible Clearance", "30ft Clearance", st, "30ft Clearance")
    accumulated_discount_pct += discount_item("5. Section 4291 Compliance", "Section 4291", st, "Section 4291")
    
    st.markdown("#### 🏘️ Community Level")
    accumulated_discount_pct += discount_item("Firewise USA Site", "Firewise USA", st, "Firewise USA")
    accumulated_discount_pct += discount_item("Fire Risk Reduction Community", "Fire Risk Community", st, "Fire Risk Community")

with col2:
    st.markdown("#### 🏗️ Structure Hardening")
    accumulated_discount_pct += discount_item("6. Class A Fire Rated Roof", "Class A Roof", st, "Class A Roof")
    accumulated_discount_pct += discount_item("7. Enclosed Eaves", "Enclosed Eaves", st, "Enclosed Eaves")
    accumulated_discount_pct += discount_item("8. Fire Resistant Vents", "Fire Res Vents", st, "Fire Res Vents")
    accumulated_discount_pct += discount_item("9. Multi-Pane Windows", "Multi-Pane Windows", st, "Multi-Pane Windows")
    accumulated_discount_pct += discount_item("10. 6-inch Vertical Clearance", "6-inch Vert Space", st, "6-inch Vert Space")
    
    # IBHS or Mercury/Chubb Specifics
    st.markdown("#### 🏆 Major Designations")
    if logic_type == "Mercury_Complex":
        accumulated_discount_pct += discount_item("Mercury Wildfire Mitigation (Std)", "Merc_Mit_Std", st)
        accumulated_discount_pct += discount_item("Mercury Wildfire Mitigation (Plus)", "Merc_Mit_Plus", st)
    else:
        accumulated_discount_pct += discount_item("IBHS Wildfire Prepared Home (Std)", "IBHS Std", st, "IBHS Std")
        accumulated_discount_pct += discount_item("IBHS Wildfire Prepared Home (Plus)", "IBHS Plus", st, "IBHS Plus")

# --- 9. SPECIAL "OTHERS" SECTION ---
st.markdown("---")
st.subheader("➕ Additional Options")

c1, c2, c3 = st.columns(3)

# CHUBB SYSTEM LOGIC
if logic_type == "Chubb_Complex":
    with c1:
        st.markdown("**Wildfire Suppression System**")
        sys_type = st.selectbox("System Type", ["None", "Manual", "Auto (Water Only)", "Auto (Retardant)"])
        sys_val = 0.0
        if sys_type == "Manual": sys_val = 3.0
        elif sys_type == "Auto (Water Only)": sys_val = 5.0
        elif sys_type == "Auto (Retardant)": sys_val = 10.0
        
        if sys_val > 0:
            accumulated_discount_pct += sys_val
            st.success(f"+{sys_val}% Applied")

# MERCURY COMMUNITY STACKING
if logic_type == "Mercury_Complex":
    with c1:
        if st.checkbox("Mercury Wildfire Mitigation Community (15%)"):
            has_fw = "Firewise USA" in checked_items
            has_fr = "Fire Risk Community" in checked_items
            
            deduction = 0.0
            if has_fw: deduction += 5.0
            if has_fr: deduction += 0.1
            
            final_comm_val = 15.0
            if has_fw and has_fr: final_comm_val = 16.1
            elif has_fw: final_comm_val = 16.0
            elif has_fr: final_comm_val = 15.1
            
            accumulated_discount_pct = accumulated_discount_pct - deduction + final_comm_val
            st.success(f"🎉 **Community Bundle:** {final_comm_val}% (Replaces individual credits)")

# DYNAMIC CHECKBOXES FOR "SPARSE" COLUMNS
extras_map = {
    "Fire_Resist_Const": "Fire Resistive Construction",
    "Shelter_In_Place": "Shelter in Place Community",
    "Def_Space_Adj": "Defensible Space Adjustment",
    "Non_Comb_Ext": "Non-Combustible Deck/Exterior",
    "Func_Shutters": "Functional Shutters"
}

col_idx = 1
cols = [c1, c2, c3]

for key, label in extras_map.items():
    base = carrier_row.get(key, 0.0)
    if base == 0: continue
    
    val = get_item_discount(key, base)
    
    if val > 0:
        with cols[col_idx % 3]:
            if st.checkbox(f"{label} ({val}%)", key=key):
                accumulated_discount_pct += val
        col_idx += 1

# --- 10. COMPLETION & BUNDLE LOGIC ---

# A. AUTO CLUB (Count Items)
if logic_type == "ACSC_Count":
    prop_items = ["Debris Removal", "Zone 0 (5ft)", "Zone 0 (Improv)", "30ft Clearance", "Section 4291", 
                  "Class A Roof", "Enclosed Eaves", "Fire Res Vents", "Multi-Pane Windows", "6-inch Vert Space"]
    count = sum(1 for item in prop_items if item in checked_items)
    acsc_map = {1:1.0, 2:2.0, 3:3.0, 4:4.0, 5:5.0, 6:6.0, 7:8.0, 8:10.0, 9:12.0, 10:15.0}
    val = acsc_map.get(count, 0.0)
    if val > 0:
        accumulated_discount_pct += val
        st.success(f"🎉 **Bundle:** {count} items = +{val}%")

# B. FARMERS / ALLSTATE / TRAVELERS (All Items)
prop_items_all = ["Debris Removal", "Zone 0 (5ft)", "Zone 0 (Improv)", "30ft Clearance", "Section 4291", 
              "Class A Roof", "Enclosed Eaves", "Fire Res Vents", "Multi-Pane Windows", "6-inch Vert Space"]
comm_items = ["Firewise USA", "Fire Risk Community"]
all_12_items = prop_items_all + comm_items

if logic_type == "Farmers_Fireline":
    if all(item in checked_items for item in all_12_items):
        accumulated_discount_pct += 2.9
        st.success("🎉 **Completion Bonus:** All 12 items verified! (+2.9%)")

if logic_type == "Allstate_Zesty":
    if all(item in checked_items for item in prop_items_all):
        zesty = risk_inputs.get('zesty_score', 6)
        bonus = 7.0 if zesty >= 6 else 2.5
        accumulated_discount_pct += bonus
        st.success(f"🎉 **Completion Bonus:** All property items verified! (+{bonus}%)")

if logic_type == "Travelers_Comp":
    if all(item in checked_items for item in prop_items_all):
        accumulated_discount_pct += 5.0
        st.success(f"🎉 **Completion Bonus:** All property items verified! (+5.0%)")
    elif all(item in checked_items for item in ["Debris Removal", "Zone 0 (5ft)", "Zone 0 (Improv)", "30ft Clearance", "6-inch Vert Space"]):
        accumulated_discount_pct += 1.5
        st.success(f"🎉 **Partial Bonus:** Perimeter + Vertical Clearance verified! (+1.5%)")

# --- 11. FINAL CALCULATIONS & POPULATING TOP WIDGETS ---
total_savings = eligible_premium * (accumulated_discount_pct / 100)
new_premium = base_premium - total_savings

# WRITE TO THE TOP CONTAINER
with metrics_container:
    m1, m2, m3 = st.columns(3)
    with m1: 
        st.metric("Current Annual Premium", f"${base_premium:,.0f}")
    with m2: 
        st.metric("Estimated Savings", f"${total_savings:,.0f}", delta=f"{accumulated_discount_pct:.2f}% off {basis_label}")
    with m3: 
        st.metric("New Annual Premium", f"${new_premium:,.0f}", delta=f"-${total_savings:,.0f}", delta_color="inverse")

# --- 3. DISCLAIMERS (Updated) ---
st.info("""
**⚠️ Important Disclaimer:** * **Talk to a Broker:** You must inform your insurance agent or broker to request these discounts. Documentation (photos/receipts) is usually required.
* **Data Source:** These estimates are based on **rate filings as of October 2025** and the **"Insurance for Good" blog post (November 4, 2025)**. 
* **Subject to Change:** Carrier underwriting guidelines and rates are subject to change at any time. Actual premiums depend on specific underwriting criteria, TIV, and final carrier approval.
""")

if df_base.empty: st.stop()