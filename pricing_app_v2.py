"""
Garden‑Suite Estimator – Hawk Property Developments (v2.9)
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

import gspread
from google.oauth2.service_account import Credentials

#st.write("✅ st.secrets keys:", list(st.secrets.keys()))
#st.write("✅ gcp_service_account keys:", list(st.secrets["gcp_service_account"].keys()))
#st.write("✅ Sheet ID:", st.secrets["sheet_id"])



# ── Google Sheets authorisation ───────────────────────────────
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"], scopes=SCOPE
)
gc = gspread.authorize(creds)

sheet = gc.open_by_key(st.secrets["gcp_service_account"]["sheet_id"]).worksheet("Leads")


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
LEADS_CSV = Path("leads.csv")

# ══════════════  PREMIUM OPTIONS  ══════════════
PREMIUM_PACKAGES = {
    "Standard Luxury": {"cost_sqft": 0, "description": "High-quality essentials for a modern, premium living space."},
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

def build_breakdown(area:int,floors:int,found:str,premium:str,beds:int,baths:int,CSA_CERT:int)->Tuple[pd.DataFrame,int,int,int]:
    mods = modules(area,floors)
    prem_cost = PREMIUM_PACKAGES[premium]["cost_sqft"]
    module_rate = module_rate_by_size(area)
    rows: List[Tuple[str,int,int]] = []
    for k,v in FIXED.items(): rows.append((k,*margin(v)))
    rows.append(("Site Prep",*margin(area*SITE_PREP_RATE)))
    f_base = area*FOUND_RATE[found] if found=="Concrete Slab" else (area/FOUND_RATE[found])*PILE_COST
    rows.append((f"Foundation ({found})",*margin(f_base)))
    m_base = area * module_rate
    p_base = area * prem_cost
    rows += [
        ("CSA Approved Modular Units",*margin(m_base + CSA_CERT)),
        (f"Premium: {premium}",*margin(p_base))
    ]
    if beds==2: rows.append(("Additional Bedroom",*margin(SECOND_BEDROOM_COST)))
    if baths==2: rows.append(("Additional Bathroom",*margin(SECOND_BATHROOM_COST)))
    duties_base = DUTY * (m_base + p_base) + 1000
    rows.append(("Duties & Brokerage Fees", *margin(duties_base)))
    rows += [
        (f"Shipping {mods} modules to site",*margin(mods*SHIP_MOD)),
        (f"Assembly of {mods} modules",*margin(mods*ASM_MOD))
    ]
    crane_days = 2 if (mods>5 or floors==2) else 1
    rows.append(("Crane",*margin(crane_days*CRANE_DAY_COST)))
    rows.append(("Project Completion",*margin(area*COMPLETE_RATE)))
    order=[
        "Permits & Drawings","Site Prep",f"Foundation ({found})","CSA Approved Modular Units",f"Premium: {premium}",
        "Additional Bedroom" if beds == 2 else None,
        "Additional Bathroom" if bathrooms == 2 else None,
        "Duties & Brokerage Fees",
        f"Shipping {mods} modules to site","Crane",f"Assembly of {mods} modules",
        "Utility Connections","Project Completion","Landscaping Restoration"
    ]
    df=pd.DataFrame(rows,columns=["Category","Low","High"]).set_index("Category").loc[[o for o in order if o]].reset_index()
    return df,int(df.Low.sum()),int(df.High.sum()),mods

# ══════════════  UI & STREAMLIT LAYOUT  ══════════════

# Global soft background panels
st.markdown(
    """
    <style>
    .soft-panel{background:#F9FBFC;padding:1rem 1.2rem;border-radius:8px;}
    @media(min-width:768px){.sticky{position:sticky;top:1rem}}
    /* orange header cells */
    .tbl thead th{background:#FF7426;color:#fff;}
    .tbl tbody tr:nth-child(even){background:#EFF2E6;}
    .tbl tbody tr:nth-child(odd){background:#EFF2E6;}
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
    #st.markdown(f"<h3 style='text-align:left;margin:0;color:{NAVY_900}'>Step 1. Design It</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:1.8rem;text-align:center;margin:.25rem 0;'><strong>Step 1. Design It</strong></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:1rem;font-color: #4F5C2E; text-align:center;margin:.25rem 0;'><strong>Customize your suite with features that fit your lifestyle</strong></p>", unsafe_allow_html=True)
    st.markdown(" ")
    st.markdown(" ")
    #st.markdown("<div class='card'>", unsafe_allow_html=True)
    #st.markdown("<div class='soft-panel'>",unsafe_allow_html=True)
    area = st.slider("📐 Suite Size (ft²)", 350, 1000, 600, 10)
    lot = st.slider("🌳 Your lot Size (ft²)", 3000, 12000, 6000, 25)
    cover = (area / lot) * 100
    #st.info(f"Your suite will cover {cover:.1f}% of our total lot")
    st.markdown(
    f"""
    <div style='text-align: center; font-color: #4F5C2E; font-size:.9rem; background-color: #F8FAF4; padding: 0.75rem 1rem; border-radius: 6px; margin: 1rem 0;'>
        Your suite will cover {cover:.1f}% of your total lot<br>
    </div>
    """,
    unsafe_allow_html=True
    )
    if cover > 10:
        st.warning("Looks like we’re pushing coverage of >10 % - let’s flag this for our zoning team 👍")
    floors = st.radio("🏠 Floors", [1, 2], horizontal=True)
    if floors == 2:
        floor_area = int(area / 2)
        st.markdown(
        f"""
        <div style='text-align: center; font-color: #4F5C2E; font-size:.9rem; background-color: #F8FAF4; padding: 0.75rem 1rem; border-radius: 6px; margin: 1rem 0;'>
            Based on {floors} floors, each floor will have<br>roughly {floor_area} sq ft
        </div>
        """,
        unsafe_allow_html=True
        )
        #st.info(f"Based on {floors} floors, each floor will have roughly {floor_area} sq ft.")
    col1, col2 = st.columns(2)
    with col1:
        beds = st.radio("🛏️ Bedrooms", [1, 2], horizontal=True)
        if beds == 2 and area < 450:
            st.warning(f"For {beds} bedrooms, we recommend a suite area greater than {area} sq ft.")
    with col2:
        bathrooms = st.radio("🛁 Bathrooms", [1, 2], horizontal=True)

    #beds  =st.radio("🛏️ Bedrooms",[1,2],horizontal=True)
    #if beds == 2 and area<450:
    #    st.warning(f"For {beds} bedrooms, we recommend a suite area greater than {area} sq ft.")
    #bathrooms = st.radio("🛁 Bathrooms", [1, 2], horizontal=True)
    mods = modules(area, floors); w, l = footprint(area, mods, floors)
    #st.info(f"We estimate you will need {mods} modules and your custom building footprint will be roughly {w} ft × {l:.1f} ft ")
    #st.info(f"Your approximate building footprint will be {w} ft × {l:.1f} ft")
    foundation = st.radio("🏗️ Foundation", ["Concrete Slab", "Helical Piles"], horizontal=True)
    premium = st.radio("✨ Premium Package", list(PREMIUM_PACKAGES.keys()), index=1)
    #st.caption(PREMIUM_PACKAGES[premium]["description"])
    st.markdown(f"<p style='font-size:.9rem; color:#444; margin-top: -0.5rem;'><em>{PREMIUM_PACKAGES[premium]['description']}</em></p>", unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

with right:
    #st.markdown("<div class='card sticky'>", unsafe_allow_html=True)
    #st.markdown(" ")
    #st.markdown(" ")
    #st.markdown(" ")
    #st.markdown(" ")
    #st.markdown(" ")
    df, low, high, mods = build_breakdown(area, floors, foundation, premium, beds, bathrooms, CSA_CERT)
    mid = (low + high) // 2
    #st.markdown(f"<h3 style='text-align:center;margin:0;color:{NAVY_900}'>Step 2: Price It</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:1.8rem;text-align:center;margin:.25rem 0;'><strong>Step 2. Price It</strong></p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:1rem;font-color: #4F5C2E; text-align:center;margin:.25rem 0;'><strong>See dynamic pricing based on your design — fully transparent and tailored</strong></p>", unsafe_allow_html=True)
    st.markdown(" ")
    st.markdown(f"<p style='font-size:2rem;text-align:center;margin:.25rem 0; color:#FF4B4B'><strong>$ {mid:,}</strong></p>", unsafe_allow_html=True)
    st.markdown(
    f"<p style='text-align:center;font-size:1rem;margin:0 0 .6rem; color:#FF4B4B'><strong>"
    f"$ {mid//area:,} $/ft²</p>",
    unsafe_allow_html=True
    )
    #st.markdown(f"<p style='text-align:center;font-size:.85rem;margin:0 0 .6rem'>$ {mid//area:,} $/ft²</p>", unsafe_allow_html=True)
    rows = "".join(f"<tr><td>{r.Category}</td><td style='text-align:right'>${(r.Low + r.High)//2:,}</td></tr>" for r in df.itertuples())
    st.markdown(f"<table class='tbl' style='width:100%;border-collapse:collapse;font-size:.9rem'><thead><tr><th>Category</th><th style='text-align:right'>Estimate</th></tr></thead><tbody>{rows}</tbody></table>", unsafe_allow_html=True)
    st.markdown(
    f"""
    <div style='text-align: center; font-color: #4F5C2E; background-color: #F8FAF4; padding: 0.75rem 1rem; border-radius: 6px; margin: 1rem 0;'>
        <strong>We estimate you will need {mods} building<br>
        modules and your custom building footprint will be roughly {w} ft × {l:.1f} ft</strong>
    </div>
    """,
    unsafe_allow_html=True
    )

    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════  LEAD FORM  ══════════════
HEADER = [
    "timestamp","name","email","area","floors","modules","foundation",
    "premium_package","beds","bathrooms","mid_total","notes"
]
if sheet.row_count == 0:
    sheet.append_row(HEADER, value_input_option="RAW")

st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #F8FAF4;
        color: #4F5C2E;
        font-weight: bold;
        border-radius: 6px;
        padding: 0.5rem 1.25rem;
    }
    div.stButton > button:first-child:hover {
        background-color: #F8FAF4;
        color: #4F5C2E;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("<div class='card' style='margin-top:1.2rem'>",unsafe_allow_html=True)
st.markdown(f"<p style='font-size:1.8rem;text-align:center;margin:.25rem 0;'><strong>Step 3. Love It</strong></p>", unsafe_allow_html=True)
#st.markdown(f"<h3 style='text-align:left;margin:0;color:{NAVY_900}'>Step 3. Get Your Custom Detailed Estimate</h3>", unsafe_allow_html=True)
#st.header("Step 2. Get Your Detailed Quote")
st.markdown("<p style='text-align: center;'>Save your custom design estimate and let our specialists provide a more detailed consultation.</p>", unsafe_allow_html=True)
with st.form("lead_form",clear_on_submit=True):
    name=st.text_input("Name*",placeholder="Your Name")
    email=st.text_input("Email Address*",placeholder="you@example.com")
    #phone=st.text_input("Phone Number (Optional)", placeholder="(555) 123-4567")
    notes=st.text_area("Specific Questions or Notes (Optional)",height=60, placeholder="e.g., Sloped backyard, lots of trees, need a basement, specific design ideas...")
    #submitted=st.form_submit_button("📧 Send My Custom Estimate")
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        submitted = st.form_submit_button("📧 Send Estimate")

    if submitted:
        if not name or not email:
            st.error("Please provide your Name and Email Address.", icon="🚨")
        else:
            row = [
                dt.datetime.utcnow().isoformat(timespec="seconds"),
                name,
                email,
                area,
                floors,
                mods,
                foundation,
                premium,
                beds,
                bathrooms,
                mid,
                notes,
            ]
            try:
                sheet.append_row(row, value_input_option="USER_ENTERED")
                st.success(f"Thanks {name}! A summary will be sent to {email} and our team will reach out shortly.")
                st.balloons()
            except Exception as e:
                st.error("Could not save your request right now. Please try again.")
                st.exception(e)



st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<p style='text-align:center;font-size:.8rem;margin-top:1rem;color:#666'>© 2025 Hawk Property Developments – Prices are preliminary and subject to consultation and site verification. HST not included.</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    pass
