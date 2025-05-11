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

# ══════════════  CONSTANTS  ══════════════
NAVY_900 = "#0C233F"; TEAL_300 = "#5A8EA7"; NAVY_700 = "#123D63"; NAVY_500 = "#1F5A80"
BG_PAGE = "#F6F8FA"; CARD_BG = "#FFFFFF"; FONT = "Inter,Helvetica,Arial,sans-serif"

MARKUP, LOW, HIGH = 0.25, 0.95, 1.05
SITE_PREP_RATE = 10; COMPLETE_RATE = 10; CRANE_DAY_COST = 10_000
MODULE_W = 8; SHIP_MOD, ASM_MOD, DUTY = 8_000, 3_000, 0.06
FOUND_RATE = {"Concrete Slab": 40, "Helical Piles": 50}; PILE_COST = 1_000
SECOND_BATHROOM_COST = 5000
FIXED = {
    "Permits & Drawings": 14_000,
    "CSA Certification & QA": 25_000,
    "Utility Connections": 11_000,
    "Landscaping Restoration": 5_000,
}
LEADS_CSV = Path("leads.csv")

# ══════════════  PREMIUM OPTIONS  ══════════════
PREMIUM_PACKAGES = {
    "Standard Luxury": {"cost_sqft": 0, "description": "High-quality essentials for a modern, comfortable living space."},
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

def build_breakdown(area:int,floors:int,found:str,premium:str,bathrooms:int)->Tuple[pd.DataFrame,int,int,int]:
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
        ("CSA Approved Modular Units",*margin(m_base)),
        (f"Premium: {premium}",*margin(p_base))
    ]
    if bathrooms == 2:
        rows.append(("Additional Bathroom", *margin(SECOND_BATHROOM_COST)))
    duties_base = DUTY * (m_base + p_base) + 1000
    rows.append(("Duties & Brokerage Fees", *margin(duties_base)))
    rows += [
        (f"Shipping to Site ({mods} modules)",*margin(mods*SHIP_MOD)),
        (f"Assembly of Modules ({mods} modules)",*margin(mods*ASM_MOD))
    ]
    crane_days = 2 if (mods>5 or floors==2) else 1
    rows.append(("Crane",*margin(crane_days*CRANE_DAY_COST)))
    rows.append(("Project Completion",*margin(area*COMPLETE_RATE)))
    order=[
        "Permits & Drawings","Site Prep",f"Foundation ({found})","CSA Approved Modular Units",f"Premium: {premium}","CSA Certification & QA",
        "Additional Bathroom" if bathrooms == 2 else None,
        "Duties & Brokerage Fees",
        f"Shipping to Site ({mods} modules)","Crane",f"Assembly of Modules ({mods} modules)",
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
    .tbl tbody tr:nth-child(even){background:#F3F4F5;}
    .tbl tbody tr:nth-child(odd){background:#F3F4F5;}
    </style>
    """,
    unsafe_allow_html=True,
)


with st.container():
    lcol, rcol = st.columns([12,5])
    with lcol:
        try:
            st.image("hawk_logo.png", width=250)
            st.markdown("<h2 style='margin:0'>Design your custom premium garden suite in minutes.....</h2>", unsafe_allow_html=True)
        except FileNotFoundError:
            st.markdown("<h3>HAWK</h3>", unsafe_allow_html=True)
    with rcol:
        st.markdown("<p style='margin:.35rem 0 0;opacity:.9'>  </p>", unsafe_allow_html=True)

    st.markdown(" ")
    st.markdown(" ")

left, right = st.columns((1.1, 1), gap="large")

with left:
    st.markdown(f"<h3 style='text-align:left;margin:0;color:{NAVY_900}'>Your Vision</h3>", unsafe_allow_html=True)
    st.markdown(" ")
    #st.markdown("<div class='card'>", unsafe_allow_html=True)
    #st.markdown("<div class='soft-panel'>",unsafe_allow_html=True)
    area = st.slider("📐 Suite Size (ft²)", 350, 1000, 600, 10)
    lot = st.slider("🌳 Your lot Size (ft²)", 3000, 12000, 6000, 25)
    cover = (area / lot) * 100
    st.info(f"Garden Suite Lot Coverage Ratio: {cover:.1f}%")
    if cover > 10:
        st.warning("Lot coverage exceeds 10% — check with your local municipality for specific constraints.")
    floors = st.radio("🏠 Floors", [1, 2], horizontal=True)
    bathrooms = st.radio("🛁 Bathrooms", [1, 2], horizontal=True)
    mods = modules(area, floors); w, l = footprint(area, mods, floors)
    st.info(f"Based on inputs, you will need {mods} Modules")
    st.info(f"Your approximate building Footprint will be {w} ft × {l:.1f} ft")
    foundation = st.radio("🏗️ Foundation", ["Concrete Slab", "Helical Piles"], horizontal=True)
    premium = st.radio("✨ Premium Package", list(PREMIUM_PACKAGES.keys()), index=1)
    st.caption(PREMIUM_PACKAGES[premium]["description"])
    st.markdown("</div>", unsafe_allow_html=True)

with right:
    #st.markdown("<div class='card sticky'>", unsafe_allow_html=True)
    #st.markdown(" ")
    df, low, high, mods = build_breakdown(area, floors, foundation, premium, bathrooms)
    mid = (low + high) // 2
    st.markdown(f"<h3 style='text-align:center;margin:0;color:{NAVY_900}'>Your Personal Estimate</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:2.2rem;text-align:center;margin:.25rem 0; color:#FF4B4B'><strong>$ {mid:,}</strong></p>", unsafe_allow_html=True)
    st.markdown(
    f"<p style='text-align:center;font-size:1rem;margin:0 0 .6rem; color:#FF4B4B'><strong>"
    f"$ {mid//area:,} $/ft²</p>",
    unsafe_allow_html=True
    )
    #st.markdown(f"<p style='text-align:center;font-size:.85rem;margin:0 0 .6rem'>$ {mid//area:,} $/ft²</p>", unsafe_allow_html=True)
    rows = "".join(f"<tr><td>{r.Category}</td><td style='text-align:right'>${(r.Low + r.High)//2:,}</td></tr>" for r in df.itertuples())
    st.markdown(f"<table class='tbl' style='width:100%;border-collapse:collapse;font-size:.9rem'><thead><tr><th>Category</th><th style='text-align:right'>Estimate</th></tr></thead><tbody>{rows}</tbody></table>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# ══════════════  LEAD FORM  ══════════════

st.markdown("<div class='card' style='margin-top:1.2rem'>",unsafe_allow_html=True)
st.header("Ready for the Next Step?")
st.markdown("Save your estimate and let our specialists provide a more detailed consultation.")
with st.form("lead_form",clear_on_submit=True):
    name=st.text_input("Full Name*",placeholder="Your Name")
    email=st.text_input("Email Address*",placeholder="you@example.com")
    phone=st.text_input("Phone Number (Optional)", placeholder="(555) 123-4567")
    notes=st.text_area("Specific Questions or Notes (Optional)",height=60, placeholder="e.g., Sloped backyard, lots of trees, need a basement, specific design ideas...")
    submitted=st.form_submit_button("📧 Email Me My Estimate & Connect")
    if submitted:
        if not name or not email:
                    st.error("Please provide your Name and Email Address.", icon="🚨")
        else:
            LEADS_CSV.touch(exist_ok=True)
            with LEADS_CSV.open("a",newline="",encoding="utf-8") as f:
                writer=csv.DictWriter(f,fieldnames=["timestamp","name","email","phone","area","floors","modules","foundation","premium_package","bathrooms","mid_total","notes"])
                if f.tell()==0: writer.writeheader()
                writer.writerow({
                    "timestamp":dt.datetime.utcnow().isoformat(timespec="seconds"),
                    "name":name,
                    "email":email,
                    "phone":phone,
                    "area":area,
                    "floors":floors,
                    "modules":mods,
                    "foundation":foundation,
                    "premium_package":premium,
                    "bathrooms":bathrooms,
                    "mid_total":mid,
                    "notes":notes,
                })
            st.success(f"Thanks {name}! A summary will be sent to {email} and our team will reach out shortly.")
            st.balloons()


st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<p style='text-align:center;font-size:.8rem;margin-top:1rem;color:#666'>© 2025 Hawk Property Developments – Prices are preliminary and subject to site verification. HST not included.</p>", unsafe_allow_html=True)

if __name__ == "__main__":
    pass
