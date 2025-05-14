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
# MODIFICATION END: Re-added Google Sheets imports

# MODIFICATION START: Re-added Google Sheets authorization
# Ensure your st.secrets are configured correctly for this to work.
# Example st.secrets.toml structure:
# [gcp_service_account]
# type = "service_account"
# project_id = "your-gcp-project-id"
# private_key_id = "your-private-key-id"
# private_key = "-----BEGIN PRIVATE KEY-----\nYOUR_PRIVATE_KEY\n-----END PRIVATE KEY-----\n"
# client_email = "your-service-account-email@your-gcp-project-id.iam.gserviceaccount.com"
# client_id = "your-client-id"
# auth_uri = "https://accounts.google.com/o/oauth2/auth"
# token_uri = "https://oauth2.googleapis.com/token"
# auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
# client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/your-service-account-email%40your-gcp-project-id.iam.gserviceaccount.com"
# sheet_id = "your_google_sheet_id" 

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

MARKUP, LOW, HIGH = 0.30, 0.95, 1.05
SITE_PREP_RATE = 10; COMPLETE_RATE = 10; CRANE_DAY_COST = 10_000
MODULE_W = 8; SHIP_MOD, ASM_MOD, DUTY = 8_000, 3_000, 0.06
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

margin = lambda base: (round(base*(1+MARKUP)*LOW), round(base*(1+MARKUP)*HIGH))
modules = lambda area,f: math.ceil(area/280) + (1 if f==2 else 0)
footprint = lambda a,m,f: (m*MODULE_W, a/(m*MODULE_W*f))

def build_breakdown(area:int,floors:int,found:str,premium:str,beds:int,baths:int,csa_certification_cost:int) -> Tuple[pd.DataFrame,int,int,int,int,int]:
    mods = modules(area,floors)
    prem_cost_sqft = PREMIUM_PACKAGES[premium]["cost_sqft"]
    module_rate = module_rate_by_size(area)
    
    rows: List[Tuple[str,int,int]] = []
    modular_categories_list = []

    m_base = area * module_rate
    csa_modular_units_cost = m_base + csa_certification_cost 
    rows.append(("CSA Approved Modular Units", *margin(csa_modular_units_cost)))
    modular_categories_list.append("CSA Approved Modular Units")

    p_base = area * prem_cost_sqft
    premium_category_name = f"Premium: {premium}"
    rows.append((premium_category_name, *margin(p_base)))
    modular_categories_list.append(premium_category_name)

    additional_bedroom_category_name = "Additional Bedroom"
    if beds==2:
        rows.append((additional_bedroom_category_name, *margin(SECOND_BEDROOM_COST)))
        modular_categories_list.append(additional_bedroom_category_name)
    
    additional_bathroom_category_name = "Additional Bathroom"
    if baths==2: # Ensuring 'baths' is used as per your function signature
        rows.append((additional_bathroom_category_name, *margin(SECOND_BATHROOM_COST)))
        modular_categories_list.append(additional_bathroom_category_name)

    for k,v in FIXED.items(): 
        rows.append((k,*margin(v)))
    
    rows.append(("Site Prep",*margin(area*SITE_PREP_RATE)))
    
    f_base_cost = area*FOUND_RATE[found] if found=="Concrete Slab" else (area/FOUND_RATE[found])*PILE_COST
    rows.append((f"Foundation ({found})",*margin(f_base_cost)))
    
    duties_on_materials = DUTY * (m_base + p_base) 
    brokerage_fee = 1000 
    total_duties_brokerage = duties_on_materials + brokerage_fee
    rows.append(("Duties & Brokerage Fees", *margin(total_duties_brokerage)))
    
    rows.append((f"Shipping {mods} modules to site",*margin(mods*SHIP_MOD)))
    rows.append((f"Assembly of {mods} modules",*margin(mods*ASM_MOD)))
    
    crane_days = 2 if (mods>5 or floors==2) else 1
    rows.append(("Crane",*margin(crane_days*CRANE_DAY_COST)))
    rows.append(("Project Completion",*margin(area*COMPLETE_RATE)))

    order=[
        "CSA Approved Modular Units", premium_category_name,
        additional_bedroom_category_name if beds == 2 else None,
        additional_bathroom_category_name if baths == 2 else None, # Use 'baths'
        "Permits & Drawings","Site Prep",f"Foundation ({found})",
        "Duties & Brokerage Fees",
        f"Shipping {mods} modules to site","Crane",f"Assembly of {mods} modules",
        "Utility Connections","Project Completion","Landscaping Restoration"
    ]
    
    df=pd.DataFrame(rows,columns=["Category","Low","High"]).set_index("Category")
    ordered_categories = [o for o in order if o is not None and o in df.index]
    df = df.loc[ordered_categories].reset_index()

    modular_low_subtotal = 0
    modular_high_subtotal = 0
    for r_df in df.itertuples(): # Changed iterator variable name
        if r_df.Category in modular_categories_list:
            modular_low_subtotal += r_df.Low
            modular_high_subtotal += r_df.High
            
    overall_low_total = int(df.Low.sum())
    overall_high_total = int(df.High.sum())
    
    return df, overall_low_total, overall_high_total, mods, int(modular_low_subtotal), int(modular_high_subtotal)

# ══════════════  UI & STREAMLIT LAYOUT  ══════════════

st.markdown(
    """ <style>
    .soft-panel{background:#F9FBFC;padding:1rem 1.2rem;border-radius:8px;}
    @media(min-width:768px){.sticky{position:sticky;top:1rem}}
    .tbl thead th{background:#FF7426;color:#fff; text-align:left; padding-left: 8px;}
    .tbl tbody tr:nth-child(even){background:#EFF2E6;}
    .tbl tbody tr:nth-child(odd){background:#EFF2E6;} 
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
    area_input = st.slider("📐 Suite Size (ft²)", 350, 1000, 600, 10)
    lot_input = st.slider("🌳 Your lot Size (ft²)", 3000, 12000, 8000, 25)
    cover_calc = (area_input / lot_input) * 100 if lot_input > 0 else 0
    st.markdown(
        f""" <div style='text-align: center; font-color: #4F5C2E; font-size:.9rem; background-color: #F8FAF4; padding: 0.75rem 1rem; border-radius: 6px; margin: 1rem 0;'>
        Your suite will cover {cover_calc:.1f}% of your total lot<br> </div>
        """, unsafe_allow_html=True
    )
    if cover_calc > 10:
        st.warning("Looks like we’re pushing coverage of >10 % - let’s flag this for our zoning team 👍")
    
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

with right:
    df_data, low_total, high_total, mods_output_val, modular_low_sub_val, modular_high_sub_val = build_breakdown(
        area_input, floors_input, foundation_input, premium_input, beds_input, bathrooms_input, CSA_CERT
    )
    mid_total_val = (low_total + high_total) // 2
    mid_modular_sub_val = (modular_low_sub_val + modular_high_sub_val) // 2

    st.markdown(f"<p style='font-size:1.8rem;text-align:center;margin:.25rem 0;'><strong>Step 2. Price It</strong></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:1rem;font-color: #4F5C2E; text-align:center;margin:.25rem 0;'><strong>See dynamic pricing based on your design — fully transparent and tailored</strong></p>", unsafe_allow_html=True)
    st.markdown(" ")
    st.markdown(f"<p style='font-size:2rem;text-align:center;margin:.25rem 0; color:#FF4B4B'><strong>$ {mid_total_val:,}</strong></p>", unsafe_allow_html=True)
    st.markdown(
        f"<p style='text-align:center;font-size:1rem;margin:0 0 .6rem; color:#FF4B4B'><strong>"
        f"$ {mid_total_val//area_input if area_input > 0 else 0:,} $/ft²</p>",
        unsafe_allow_html=True
    )

    table_html_str = "<table class='tbl' style='width:100%;border-collapse:collapse;font-size:.9rem'>"
    table_html_str += "<thead><tr><th>Category</th><th style='text-align:right'>Estimate</th></tr></thead>"
    table_html_str += "<tbody>"

    #table_html_str += "<tr class='section-header-row'><td colspan='2'>Modular Building Costs</td></tr>"
    table_html_str += (
        f"<tr class='section-header-row'>"
        f"<td colspan='2'>Modular Building Costs for {area_input:,} sq&nbsp;ft</td>"
        f"</tr>"
    )
    
    modular_categories_in_df_order = [
        "CSA Approved Modular Units", 
        f"Premium: {premium_input}", # Use the input variable
    ]
    if beds_input == 2: modular_categories_in_df_order.append("Additional Bedroom")
    if bathrooms_input == 2: modular_categories_in_df_order.append("Additional Bathroom")

    for category_name in modular_categories_in_df_order:
        row_data_item = df_data[df_data['Category'] == category_name]
        if not row_data_item.empty:
            r_low_item = row_data_item.iloc[0]['Low']
            r_high_item = row_data_item.iloc[0]['High']
            r_mid_item = (r_low_item + r_high_item) // 2
            table_html_str += f"<tr><td>{category_name}</td><td style='text-align:right'>${r_mid_item:,}</td></tr>"
            
    table_html_str += f"<tr class='subtotal-row'><td><strong>Modular Building Subtotal</strong></td><td style='text-align:right'><strong>${mid_modular_sub_val:,}</strong></td></tr>"

    table_html_str += "<tr class='section-header-row'><td colspan='2'>Other Project Costs</td></tr>"
    
    all_df_categories_list = df_data['Category'].tolist()
    other_cost_categories_list = [cat for cat in all_df_categories_list if cat not in modular_categories_in_df_order]

    for category_name_other in other_cost_categories_list:
        row_data_other = df_data[df_data['Category'] == category_name_other]
        if not row_data_other.empty:
            r_low_other = row_data_other.iloc[0]['Low']
            r_high_other = row_data_other.iloc[0]['High']
            r_mid_other = (r_low_other + r_high_other) // 2
            table_html_str += f"<tr><td>{category_name_other}</td><td style='text-align:right'>${r_mid_other:,}</td></tr>"

    table_html_str += "</tbody></table>"
    st.markdown(table_html_str, unsafe_allow_html=True)
    
    st.markdown(
        f""" <div style='text-align: center; font-color: #4F5C2E; background-color: #F8FAF4; padding: 0.75rem 1rem; border-radius: 6px; margin: 1rem 0;'> <strong>We estimate you will need {mods_output_val} building<br>
        modules and your custom building footprint will be roughly {w_calc} ft × {l_calc:.1f} ft</strong> </div>
        """, unsafe_allow_html=True
    )
    # Removed potentially unclosed div from here


# ══════════════  LEAD FORM  ══════════════
# MODIFICATION START: Re-integrated Google Sheets Lead Saving
GSHEET_HEADER_ORDER = [ # Define the order of columns for Google Sheets
    "timestamp","name","email","area","floors","modules","foundation",
    "premium_package","beds","bathrooms","mid_total","notes"
]

if GSHEETS_ACTIVE:
    try:
        if google_sheet.row_count == 0: # Check if sheet is empty to add header
            google_sheet.append_row(GSHEET_HEADER_ORDER, value_input_option="RAW")
    except Exception as ge: # Catch potential gspread error if sheet doesn't exist or perm issues
        st.warning(f"Could not verify or write header to Google Sheet 'Leads'. Error: {ge}")
        GSHEETS_ACTIVE = False # Disable further GSheets attempts if header check fails

st.markdown("<div class='card' style='margin-top:1.2rem'>",unsafe_allow_html=True)
st.markdown(f"<p style='font-size:1.8rem;text-align:center;margin:.25rem 0;'><strong>Step 3. Love It</strong></p>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Your design. Your budget. Our expertise. Let’s bring it all to life — together.</p>", unsafe_allow_html=True)
with st.form("lead_form",clear_on_submit=True):
    name_form_input = st.text_input("Name*",placeholder="Your Name")
    email_form_input = st.text_input("Email Address*",placeholder="you@example.com")
    notes_form_input = st.text_area("Specific Questions or Notes (Optional)",height=60, placeholder="e.g., Sloped backyard, lots of trees, need a basement, specific design ideas...")
    submitted_form = st.form_submit_button("📧 Send My Custom Estimate")

    if submitted_form:
        if not name_form_input or not email_form_input:
            st.error("Please provide your Name and Email Address.", icon="🚨")
        else:
            # Prepare data as a list in the GSheet header order
            lead_data_row_list = [
                dt.datetime.utcnow().isoformat(timespec="seconds"),
                name_form_input, email_form_input,
                area_input, floors_input, mods_output_val, 
                foundation_input, premium_input,
                beds_input, bathrooms_input, 
                mid_total_val, notes_form_input,
            ]
            
            gsheet_success = False
            if GSHEETS_ACTIVE:
                try:
                    google_sheet.append_row(lead_data_row_list, value_input_option="USER_ENTERED")
                    st.success(f"Thanks {name_form_input}! Your estimate details have been recorded. Our team will be in touch shortly via {email_form_input}.")
                    st.balloons()
                    gsheet_success = True
                except Exception as e_gsheet:
                    st.error(f"An error occurred while saving to our primary system. Your data will be saved locally. Error: {e_gsheet}")
                    # Fall through to CSV saving
            
            if not gsheet_success: # Save to CSV if GSheets not active or failed
                try:
                    LEADS_CSV.parent.mkdir(parents=True, exist_ok=True)
                    is_new_csv_file = not LEADS_CSV.exists()
                    with LEADS_CSV.open("a", newline="", encoding="utf-8") as f_csv:
                        writer_csv = csv.writer(f_csv)
                        if is_new_csv_file:
                            writer_csv.writerow(GSHEET_HEADER_ORDER) # Use same header for consistency
                        writer_csv.writerow(lead_data_row_list)
                    
                    if GSHEETS_ACTIVE : # Implies GSheets failed, but CSV succeeded
                         st.warning(f"Thanks {name_form_input}! We had an issue with our primary system, but your request was saved securely. We'll be in touch!")
                    else: # GSheets was never active
                        st.success(f"Thanks {name_form_input}! Your estimate details have been saved locally. Our team will be in touch shortly via {email_form_input}.")
                    if not gsheet_success : st.balloons() # Show balloons if primary GSheet didn't show them

                except Exception as e_csv:
                    st.error(f"CRITICAL: Could not save your estimate data. Please contact us directly. Error: {e_csv}")
# MODIFICATION END: Re-integrated Google Sheets Lead Saving

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<p style='text-align:center;font-size:.8rem;margin-top:1rem;color:#666'>© 2025 Hawk Property Developments – Prices are preliminary and subject to consultation, final design drawings and site verification. HST not included.</p>", unsafe_allow_html=True)

# if __name__ == "__main__":
#     pass 