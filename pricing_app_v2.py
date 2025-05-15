"""
Garden-Suite Estimator – Hawk Property Developments (v2.9.2 - GSheets + Enhanced Table)
-----------------------------------------------------------------

Run:
    streamlit run pricing_app.py
"""

from __future__ import annotations
import csv, datetime as dt, math
from pathlib import Path
from typing import Dict, List, Tuple

import streamlit as st
import pandas as pd
from PIL import Image

# MODIFICATION START: Re-added Google Sheets imports
import gspread
from google.oauth2.service_account import Credentials


try:
    SCOPE = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPE
    )
    gc = gspread.authorize(creds)
    # Use the sheet_id directly from the main gcp_service_account dictionary in secrets
    SHEET_ID = st.secrets["gcp_service_account"]["sheet_id"] 
    google_sheet = gc.open_by_key(SHEET_ID).worksheet("Leads") # Assuming worksheet name is "Leads"
    GSHEETS_ACTIVE = True
except Exception as e:
    st.error(f"Could not connect to Google Sheets. Leads will be saved locally only. Error: {e}")
    GSHEETS_ACTIVE = False
# MODIFICATION END: Re-added Google Sheets authorization

# ══════════════  CONSTANTS  ══════════════

NAVY_900 = "#0C233F"; TEAL_300 = "#5A8EA7"; NAVY_700 = "#123D63"; NAVY_500 = "#1F5A80"
BG_PAGE = "#F6F8FA"; CARD_BG = "#FFFFFF"; FONT = "Inter,Helvetica,Arial,sans-serif"

MARKUP_MODULE = 0.50  # 50% markup for module-related costs
MARKUP_SITE = 0.05    # 0% markup for site/other project costs
LOW, HIGH = 0.95, 1.05

#MARKUP, LOW, HIGH = 0.25, 0.95, 1.05
SITE_PREP_RATE = 10; COMPLETE_RATE = 10; CRANE_DAY_COST = 10_000
MODULE_W = 8; SHIP_MOD, ASM_MOD, DUTY = 8_000, 3_000, 0.07  # made duty 7% vs 6% in case of other fees we are not aware of
FOUND_RATE = {"Concrete Slab": 40, "Helical Piles": 50}; PILE_COST = 1_000
CSA_CERT = 25000
SECOND_BATHROOM_COST = 5000
SECOND_BEDROOM_COST  = 2500
FIXED = {
    "Permits & Drawings": 14_000,
    "Utility Connections": 11_000,
    "Landscaping Restoration": 5_000,
}
LEADS_CSV = Path("leads.csv") # Local CSV fallback

# ══════════════  PREMIUM OPTIONS  ══════════════

PREMIUM_PACKAGES = {
    "Standard Luxury - included": {"cost_sqft": 0, "description": "High-quality essentials for a modern, premium living space."},
    "Designer Curated": {"cost_sqft": 20, "description": "Upgraded fixtures, flooring, and cabinetry with designer touches."},
    "Ultimate Bespoke": {"cost_sqft": 40, "description": "Security, smart home features, and exterior detailing."},
}

# ══════════════  HELPERS  ══════════════

def module_rate_by_size(area: int) -> int:
    if area < 500:
        return 180
    elif area <= 800:
        return 160
    else:
        return 145

# Now takes a specific markup rate as an argument
def calculate_margin_with_specific_markup(base_cost: float, specific_markup_rate: float) -> Tuple[int, int]:
    marked_up_cost = base_cost * (1 + specific_markup_rate)
    return round(marked_up_cost * LOW), round(marked_up_cost * HIGH)
# The old `margin` lambda is replaced by this function.
#margin = lambda base: (round(base*(1+MARKUP)*LOW), round(base*(1+MARKUP)*HIGH))

modules = lambda area,f: math.ceil(area/280) + (1 if f==2 else 0)
footprint = lambda a,m,f: (m*MODULE_W, a/(m*MODULE_W*f))
# --- MODIFICATION START: Update build_breakdown return signature and logic ---
def build_breakdown(area:int, floors:int, found:str, premium:str, beds:int, baths:int, csa_certification_cost:int) \
        -> Tuple[pd.DataFrame, int, int, int, int, int, int, int, int]: # Added base cost subtotals to return
    mods = modules(area,floors)
    prem_cost_sqft = PREMIUM_PACKAGES[premium]["cost_sqft"]
    module_rate = module_rate_by_size(area)
    
    # Now rows will store: (Category, LowMarkedUp, HighMarkedUp, BaseCost)
    rows: List[Tuple[str, int, int, float]] = [] 
    modular_categories_list = [] 

    # 1. CSA Approved Modular Units
    m_base = area * module_rate 
    csa_modular_units_base_cost = m_base + csa_certification_cost 
    category_csa_units = "CSA Approved Modular Units"
    low_val, high_val = calculate_margin_with_specific_markup(csa_modular_units_base_cost, MARKUP_MODULE)
    rows.append((category_csa_units, low_val, high_val, csa_modular_units_base_cost))
    modular_categories_list.append(category_csa_units)

    # 2. Premium Package
    p_base = area * prem_cost_sqft 
    premium_category_name = f"Premium: {premium}"
    low_val, high_val = calculate_margin_with_specific_markup(p_base, MARKUP_MODULE)
    rows.append((premium_category_name, low_val, high_val, p_base))
    modular_categories_list.append(premium_category_name)

    # 3. Additional Bedroom
    additional_bedroom_category_name = "Additional Bedroom"
    if beds==2:
        low_val, high_val = calculate_margin_with_specific_markup(SECOND_BEDROOM_COST, MARKUP_MODULE)
        rows.append((additional_bedroom_category_name, low_val, high_val, float(SECOND_BEDROOM_COST)))
        modular_categories_list.append(additional_bedroom_category_name)
    
    # 4. Additional Bathroom
    additional_bathroom_category_name = "Additional Bathroom"
    if baths==2:
        low_val, high_val = calculate_margin_with_specific_markup(SECOND_BATHROOM_COST, MARKUP_MODULE)
        rows.append((additional_bathroom_category_name, low_val, high_val, float(SECOND_BATHROOM_COST)))
        modular_categories_list.append(additional_bathroom_category_name)

    # --- Site-related and other fixed costs (apply MARKUP_SITE) ---
    for k, v_base_cost_fixed in FIXED.items(): 
        low_val, high_val = calculate_margin_with_specific_markup(v_base_cost_fixed, MARKUP_SITE)
        rows.append((k, low_val, high_val, float(v_base_cost_fixed)))
    
    site_prep_base_cost = float(area * SITE_PREP_RATE)
    low_val, high_val = calculate_margin_with_specific_markup(site_prep_base_cost, MARKUP_SITE)
    rows.append(("Site Prep", low_val, high_val, site_prep_base_cost))
    
    f_foundation_base_cost = float(area*FOUND_RATE[found] if found=="Concrete Slab" else (area/FOUND_RATE[found])*PILE_COST)
    low_val, high_val = calculate_margin_with_specific_markup(f_foundation_base_cost, MARKUP_SITE)
    rows.append((f"Foundation ({found})", low_val, high_val, f_foundation_base_cost))
    
    duties_on_materials_base = DUTY * (m_base + p_base) 
    brokerage_fee_base = 1000.0
    total_duties_brokerage_base_cost = duties_on_materials_base + brokerage_fee_base
    low_val, high_val = calculate_margin_with_specific_markup(total_duties_brokerage_base_cost, MARKUP_SITE)
    rows.append(("Deliver Coordination, Inspection Fees", low_val, high_val, total_duties_brokerage_base_cost))
    
    transport_base_cost = float(mods*SHIP_MOD)
    low_val, high_val = calculate_margin_with_specific_markup(transport_base_cost, MARKUP_SITE)
    rows.append((f"Transport {mods} modules to site", low_val, high_val, transport_base_cost))
    
    assembly_base_cost = float(mods*ASM_MOD)
    low_val, high_val = calculate_margin_with_specific_markup(assembly_base_cost, MARKUP_SITE)
    rows.append((f"Assembly of {mods} modules", low_val, high_val, assembly_base_cost))
    
    crane_base_cost = float((2 if (mods>5 or floors==2) else 1) * CRANE_DAY_COST)
    low_val, high_val = calculate_margin_with_specific_markup(crane_base_cost, MARKUP_SITE)
    rows.append(("Crane", low_val, high_val, crane_base_cost))
    
    project_completion_base_cost = float(area*COMPLETE_RATE)
    low_val, high_val = calculate_margin_with_specific_markup(project_completion_base_cost, MARKUP_SITE)
    rows.append(("Project Completion", low_val, high_val, project_completion_base_cost))

    order=[
        category_csa_units, premium_category_name,
        additional_bedroom_category_name if beds == 2 else None,
        additional_bathroom_category_name if baths == 2 else None,
        "Permits & Drawings","Site Prep",f"Foundation ({found})",
        "Deliver Coordination, Inspection Fees",
        f"Transport {mods} modules to site", f"Assembly of {mods} modules", "Crane",
        "Utility Connections","Project Completion","Landscaping Restoration"
    ]
    
    # Create DataFrame with BaseCost column
    df=pd.DataFrame(rows,columns=["Category","Low","High","BaseCost"]).set_index("Category")
    ordered_categories = [o for o in order if o is not None and o in df.index] 
    df = df.loc[ordered_categories].reset_index()

    # Calculate modular subtotals (both marked-up and base)
    modular_low_subtotal = 0
    modular_high_subtotal = 0
    base_modular_subtotal = 0
    for r_df in df.itertuples():
        if r_df.Category in modular_categories_list:
            modular_low_subtotal += r_df.Low
            modular_high_subtotal += r_df.High
            base_modular_subtotal += r_df.BaseCost # Sum base costs for modular items
            
    overall_low_total = int(df.Low.sum())
    overall_high_total = int(df.High.sum())
    total_base_cost = int(df.BaseCost.sum()) # Sum of all base costs
    
    # Calculate base other costs subtotal
    base_other_costs_subtotal = total_base_cost - base_modular_subtotal
    
    return (df, overall_low_total, overall_high_total, mods, 
            int(modular_low_subtotal), int(modular_high_subtotal),
            int(base_modular_subtotal), int(base_other_costs_subtotal), int(total_base_cost))
# --- MODIFICATION END ---




# ══════════════  UI & STREAMLIT LAYOUT  ══════════════

st.markdown(
    """ <style>
    .soft-panel{background:#F9FBFC;padding:1rem 1.2rem;border-radius:8px;}
    @media(min-width:768px){.sticky{position:sticky;top:1rem}}
    .tbl thead th{background:#FF7426;color:#fff; text-align:left; padding-left: 8px;}
    #.tbl tbody tr:nth-child(even){background:#EFF2E6;}
    #.tbl tbody tr:nth-child(odd){background:#EFF2E6;} 
    .tbl td {padding-left: 8px; padding-right: 8px;}
    .section-header-row td {font-weight: bold; background-color: #E0E0E0 !important; color: #333; padding-top: 8px; padding-bottom: 8px;}
    .subtotal-row td {font-weight: bold; background-color: #F0F0F0 !important;}
    </style>
    """,
    unsafe_allow_html=True,
)

with st.container():
    lcol, rcol = st.columns([15,5])
    with lcol:
        try:
            st.image("hawk_logo.png", width=250)
            st.markdown(" ")
            st.image("hero_banner.jpg", width=650)
            #st.markdown("<h2 style='margin:0'>GARDEN SUITE ESTIMATOR</h2>", unsafe_allow_html=True)
            #st.markdown(" ")
            st.markdown("<h3 style='margin:0'>Design it. Price it. Love it.</h3>", unsafe_allow_html=True)
        except FileNotFoundError:
            st.markdown("<h3>HAWK</h3>", unsafe_allow_html=True)
    with rcol:
        st.markdown("<p style='margin:.35rem 0 0;opacity:.9'>  </p>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.1rem; color: #555; margin-top: 5px;'><b>Welcome to the smarter way to build. We merge cutting-edge modular technology with luxury design to create exceptional backyard suites. Experience precision engineering, accelerated construction, and unparalleled quality, tailored perfectly for you.</b></p>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.1rem; color: #555; margin-top: 5px;'><b>Get your personalized suite estimate now. No waiting. No pressure. Just possibilities.</b></p>", unsafe_allow_html=True)

    #st.markdown("<p style='font-size: 1.1rem; color: #555; margin-top: 5px;'><b>Experience the future of luxury living, built faster and smarter. Our modular innovations deliver unparalleled precision and exceptional value. Transform and unlock the value of your backyard.</b></p>", unsafe_allow_html=True)
    #st.markdown("<p style='font-size: 1.1rem; color: #555; margin-top: 5px;'><b>Create our own custom estimate in minutes...</b></p>", unsafe_allow_html=True)
    #st.caption("Craft your dream backyard oasis and get a preliminary budget in minutes. Final costs exclude HST and are subject to site verification & detailed design.")
    st.markdown(" ")
    st.markdown(" ")

left, right = st.columns((1, 1), gap="large")

with left:
    st.markdown(f"<p style='font-size:1.8rem;text-align:center;margin:.25rem 0;'><strong>Step 1. Design It</strong></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:1rem;font-color: #4F5C2E; text-align:center;margin:.25rem 0;'><strong>Customize your suite with features that fit your lifestyle</strong></p>", unsafe_allow_html=True)
    st.markdown(" ")
    st.markdown(" ")
    area_input = st.slider("📐 Customize Your Personal Suite Size (ft²)", 350, 1000, 600, 10)
    lot_input = st.slider("🌳 Your lot Size (ft²)", 3000, 12000, 8000, 25)
    cover_calc = (area_input / lot_input) * 100 if lot_input > 0 else 0
    st.markdown(
        f""" <div style='text-align: center; font-color: #4F5C2E; font-size:.9rem; background-color: #F8FAF4; padding: 0.75rem 1rem; border-radius: 6px; margin: 1rem 0;'>
        Your suite will cover {cover_calc:.1f}% of your total lot<br> </div>
        """, unsafe_allow_html=True
    )
    if cover_calc > 10:
        st.warning("Looks like we’re pushing coverage of >10 % - let’s flag this for our zoning team")
    
    floors_input = st.radio("🏠 Floors", [1, 2], horizontal=True)
    if floors_input == 2:
        floor_area_calc = int(area_input / 2)
        st.markdown(
            f""" <div style='text-align: center; font-color: #4F5C2E; font-size:.9rem; background-color: #F8FAF4; padding: 0.75rem 1rem; border-radius: 6px; margin: 1rem 0;'>
            Based on {floors_input} floors, each floor will have<br>roughly {floor_area_calc} sq ft </div>
            """, unsafe_allow_html=True
        )
    
    col1, col2 = st.columns(2)
    with col1:
        beds_input = st.radio("🛏️ Bedrooms", [1, 2], horizontal=True)
        if beds_input == 2 and area_input < 450:
            st.warning(f"For {beds_input} bedrooms, we recommend a suite area greater than {area_input} sq ft for comfort.")
    with col2:
        bathrooms_input = st.radio("🛁 Bathrooms", [1, 2], horizontal=True)
    
    mods_calc_val = modules(area_input, floors_input); w_calc, l_calc = footprint(area_input, mods_calc_val, floors_input)
    
    foundation_input = st.radio("🏗️ Foundation", ["Concrete Slab", "Helical Piles"], horizontal=True)
    premium_input = st.radio("✨ Premium Package", list(PREMIUM_PACKAGES.keys()), index=1)
    st.markdown(f"<p style='font-size:.9rem; color:#444; margin-top: -0.5rem;'><em>{PREMIUM_PACKAGES[premium_input]['description']}</em></p>", unsafe_allow_html=True)
    # Removed potentially unclosed div from here

with right: # Assuming 'right' is your Streamlit column

    df_data, low_total, high_total, mods_output_val, \
    modular_low_sub_val, modular_high_sub_val, \
    base_modular_subtotal_val, base_other_costs_subtotal_val, total_base_cost_val = build_breakdown(
        area_input, floors_input, foundation_input, premium_input, beds_input, bathrooms_input, CSA_CERT
    )

    mid_modular_sub_val = (modular_low_sub_val + modular_high_sub_val) // 2
    other_marked_up_costs_mid_sum = 0
    temp_all_df_categories_list = df_data['Category'].tolist()

    current_modular_categories_for_display = ["CSA Approved Modular Units", f"Premium: {premium_input}"]
    if beds_input == 2: current_modular_categories_for_display.append("Additional Bedroom")
    if bathrooms_input == 2: current_modular_categories_for_display.append("Additional Bathroom")

    temp_other_cost_categories_list_corrected = [cat for cat in temp_all_df_categories_list if cat not in current_modular_categories_for_display]

    for category_name_other_temp in temp_other_cost_categories_list_corrected:
        row_data_other_temp = df_data[df_data['Category'] == category_name_other_temp]
        if not row_data_other_temp.empty:
            r_low_other_temp = row_data_other_temp.iloc[0]['Low']
            r_high_other_temp = row_data_other_temp.iloc[0]['High']
            other_marked_up_costs_mid_sum += (r_low_other_temp + r_high_other_temp) // 2
    
    other_costs_subtotal_mid_marked_up = other_marked_up_costs_mid_sum # This is the marked-up mid for other costs

    complete_project_cost_mid_marked_up = mid_modular_sub_val + other_costs_subtotal_mid_marked_up


    # --- Calculate Profits ---
    profit_modular_mid = mid_modular_sub_val - base_modular_subtotal_val
    profit_other_costs_mid = other_costs_subtotal_mid_marked_up - base_other_costs_subtotal_val # Use marked-up other costs
    profit_total_project_mid = complete_project_cost_mid_marked_up - total_base_cost_val
    # Or: profit_total_project_mid = profit_modular_mid + profit_other_costs_mid

    # --- UI Display (Table and Totals) ---
    # (Your existing st.markdown for "Step 2. Price It" and Modular Building Estimate remains)
    st.markdown(f"<p style='font-size:1.8rem;text-align:center;margin:.25rem 0;'><strong>Step 2. Price It</strong></p>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='font-size:1rem;  text-align:center; margin:.25rem 0;'>"
        f"<strong>Modular Building Estimate</strong></p>",
        unsafe_allow_html=True
    )
    st.markdown(" ")
    st.markdown(f"<p style='font-size:2rem;text-align:center;margin:.25rem 0; color:#FF4B4B'><strong>$ {mid_modular_sub_val:,}</strong></p>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='text-align:center;font-size:1rem;margin:0 0 .6rem; color:#FF4B4B'><strong>"
        f"$ {mid_modular_sub_val//area_input if area_input > 0 else 0:,} $/ft² (Modular Only)</p>",
        unsafe_allow_html=True
    )

    table_html_str = "<table class='tbl' style='width:100%;border-collapse:collapse;font-size:.9rem'>"
    table_html_str += "<thead><tr><th>Category</th><th style='text-align:right'>Estimate</th></tr></thead>"
    table_html_str += "<tbody>"
    table_html_str += f"<tr class='section-header-row'><td colspan='2'>Modular Building Costs for {area_input:,} sq ft</td></tr>"
    
    for category_name in current_modular_categories_for_display: # Use the locally defined list
        row_data_item = df_data[df_data['Category'] == category_name]
        if not row_data_item.empty:
            r_mid_item = (row_data_item.iloc[0]['Low'] + row_data_item.iloc[0]['High']) // 2
            table_html_str += f"<tr><td>{category_name}</td><td style='text-align:right'>${r_mid_item:,}</td></tr>"
            
    table_html_str += f"<tr class='subtotal-row'><td><strong>Modular Building Subtotal</strong></td><td style='text-align:right'><strong>${mid_modular_sub_val:,}</strong></td></tr>"
    table_html_str += "<tr class='section-header-row'><td colspan='2'>Other Project Costs - Full Transparency</td></tr>"
    
    # The 'other_costs_subtotal_mid' from your previous table loop is now 'other_costs_subtotal_mid_marked_up'
    for category_name_other in temp_other_cost_categories_list_corrected: # Use the corrected list
        row_data_other = df_data[df_data['Category'] == category_name_other]
        if not row_data_other.empty:
            r_mid_other = (row_data_other.iloc[0]['Low'] + row_data_other.iloc[0]['High']) // 2
            table_html_str += f"<tr><td>{category_name_other}</td><td style='text-align:right'>${r_mid_other:,}</td></tr>"
            
    # Display the subtotal for other costs (optional, but good for consistency if you had it)
    table_html_str += f"<tr class='subtotal-row'><td><strong>Other Project Costs Subtotal</strong></td><td style='text-align:right'><strong>${other_costs_subtotal_mid_marked_up:,}</strong></td></tr>"

    table_html_str += f"<tr class='subtotal-row' style='border-top: 2px solid #ccc; background-color: #e8e8e8 !important; font-size:1.05em !important;'>"
    table_html_str += f"<td><strong>Complete Project Cost Estimate</strong></td>"
    table_html_str += f"<td style='text-align:right'><strong>${complete_project_cost_mid_marked_up:,}</strong></td>"
    table_html_str += f"</tr></tbody></table>"
    st.markdown(table_html_str, unsafe_allow_html=True)

    # (Your st.markdown for "We estimate you will need..." remains)
    #st.markdown(
    #    f""" <div style='text-align: center; font-color: #4F5C2E; background-color: #F8FAF4; padding: 0.75rem 1rem; border-radius: 6px; margin: 1rem 0;'> <strong>We estimate you will need {mods_output_val} building<br>
    #    modules for your custom project</strong> </div>
    #    """, unsafe_allow_html=True
    #)



# ══════════════  LEAD FORM  ══════════════
# MODIFICATION START: Updated GSheet Header Order
GSHEET_HEADER_ORDER = [ 
    "timestamp", "name", "email", "area_sqft", "floors", "modules_count",
    "foundation_type", "premium_package", "bedrooms_count", "bathrooms_count",
    "mid_modular_subtotal_marked_up", # Marked-up value
    "other_costs_subtotal_marked_up", # Marked-up value
    "complete_project_cost_mid_marked_up", # Marked-up value
    "base_modular_subtotal",        # NEW
    "base_other_costs_subtotal",    # NEW
    "total_base_cost",              # NEW
    "profit_modular_mid",           # NEW
    "profit_other_costs_mid",       # NEW
    "profit_total_project_mid",     # NEW
    "notes"
]
# --- MODIFICATION END ---

# ... (Your GSheets header check logic remains the same) ...
if GSHEETS_ACTIVE:
    try:
        sheet_is_truly_empty = (google_sheet.row_count == 0)
        header_needs_writing = False
        if sheet_is_truly_empty:
            header_needs_writing = True
        else:
            try:
                existing_header_row = google_sheet.row_values(1) 
                if not existing_header_row or existing_header_row != GSHEET_HEADER_ORDER:
                    st.warning(
                        "Google Sheet header mismatch or missing. "
                        "Data might be appended incorrectly or to the wrong sheet. "
                        "Please ensure the 'Leads' sheet has the correct header columns or is empty."
                    )
            except gspread.exceptions.APIError as e_api:
                if "exceeds grid limits" in str(e_api).lower() or "Unable to parse range" in str(e_api):
                    header_needs_writing = True 
                else:
                    st.warning(f"Error checking Google Sheet header: {e_api}. Proceeding with caution.")
        if header_needs_writing:
            google_sheet.append_row(GSHEET_HEADER_ORDER, value_input_option="RAW")
    except Exception as ge: 
        st.warning(f"Could not verify or write header to Google Sheet 'Leads'. Error: {ge}")
        GSHEETS_ACTIVE = False

# ... (Your st.markdown for "Step 3. Love It" and form setup remains the same) ...
st.markdown("<div class='card' style='margin-top:1.2rem'>",unsafe_allow_html=True)
st.markdown(f"<p style='font-size:1.8rem;text-align:center;margin:.25rem 0;'><strong>Step 3. Love It</strong></p>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Your design. Your Size. Your budget. Our expertise. Let’s bring it all to life — together.</p>", unsafe_allow_html=True)
with st.form("lead_form",clear_on_submit=True):
    name_form_input = st.text_input("Name*",placeholder="Your Name")
    email_form_input = st.text_input("Email Address*",placeholder="you@example.com")
    notes_form_input = st.text_area("Specific Questions or Notes (Optional)",height=60, placeholder="e.g., Sloped backyard, any power lines, lots of trees, need a basement, specific design ideas...")
    #submitted_form = st.form_submit_button("📧 Send My Custom Estimate")
    # --- Centering the button ---
    col1, col2, col3 = st.columns([1, 1.1, 1]) # Adjust ratios as needed, e.g., [1,1,1] or [2,1,2]
    with col2: # Place button in the middle column
        submitted_form = st.form_submit_button("📧 Send My Custom Estimate")
    # --- End centering ---

    if submitted_form:
        if not name_form_input or not email_form_input:
            st.error("Please provide your Name and Email Address.", icon="🚨")
        else:
            # --- MODIFICATION START: Add profit and base cost values to lead_data_row_list ---
            lead_data_row_list = [
                dt.datetime.utcnow().isoformat(timespec="seconds"),
                name_form_input,
                email_form_input,
                int(area_input),
                int(floors_input),
                int(mods_output_val),
                foundation_input,
                premium_input,
                int(beds_input),
                int(bathrooms_input),
                int(mid_modular_sub_val),                # Marked-up modular subtotal
                int(other_costs_subtotal_mid_marked_up), # Marked-up other costs subtotal
                int(complete_project_cost_mid_marked_up),# Marked-up complete project cost
                int(base_modular_subtotal_val),          # Base modular subtotal
                int(base_other_costs_subtotal_val),      # Base other costs subtotal
                int(total_base_cost_val),                # Total base cost
                int(profit_modular_mid),                 # Profit on modular
                int(profit_other_costs_mid),             # Profit on other costs
                int(profit_total_project_mid),           # Total project profit
                notes_form_input,
            ]
            # --- MODIFICATION END ---
            
            gsheet_success = False
            # ... (Rest of your GSheet and CSV saving logic remains the same) ...
            if GSHEETS_ACTIVE:
                try:
                    google_sheet.append_row(lead_data_row_list, value_input_option="USER_ENTERED")
                    st.success(f"Thanks {name_form_input}! Your estimate details have been recorded. Our team will be in touch shortly via {email_form_input}.")
                    st.balloons()
                    gsheet_success = True
                except Exception as e_gsheet:
                    st.error(f"An error occurred while saving to our primary system. Your data will be saved locally. Error: {e_gsheet}")
            
            if not gsheet_success: 
                try:
                    LEADS_CSV.parent.mkdir(parents=True, exist_ok=True)
                    is_new_csv_file = not LEADS_CSV.exists()
                    with LEADS_CSV.open("a", newline="", encoding="utf-8") as f_csv:
                        writer_csv = csv.writer(f_csv)
                        if is_new_csv_file:
                            writer_csv.writerow(GSHEET_HEADER_ORDER) 
                        writer_csv.writerow(lead_data_row_list)
                    
                    if GSHEETS_ACTIVE : 
                         st.warning(f"Thanks {name_form_input}! We had an issue with our primary system, but your request was saved securely. We'll be in touch!")
                    else: 
                        st.success(f"Thanks {name_form_input}! Your estimate details have been saved locally. Our team will be in touch shortly via {email_form_input}.")
                    if not gsheet_success : st.balloons()

                except Exception as e_csv:
                    st.error(f"CRITICAL: Could not save your estimate data. Please contact us directly. Error: {e_csv}")

st.markdown("</div>", unsafe_allow_html=True) # Closes the card div for the form

st.markdown("<p style='text-align:center;font-size:.8rem;margin-top:1rem;color:#666'>© 2025 Hawk Property Developments – Prices are preliminary and subject to consultation, final design drawings and site verification. HST not included.</p>", unsafe_allow_html=True)
# if __name__ == "__main__":
#     pass 