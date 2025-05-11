"""
Garden‑Suite Estimator – Hawk Property Developments (Enhanced WOW MVP v2.0)
----------------------------------------------------------------------------
Run: streamlit run pricing_app.py
"""

from __future__ import annotations
import csv, datetime as dt, math, uuid, json
from pathlib import Path
from typing import Dict, List, Tuple, Any
import urllib.parse

import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from PIL import Image

# === CONFIG ===============================================================
MARKUP = 0.30
LOW_MULT, HIGH_MULT = 0.95, 1.05 # Range around the marked-up price
MODULE_BASE_RATE = 165 # $/sqft
SITE_PREP_RATE = 10 # $/sqft
PROJECT_COMPLETION_RATE = 10 # $/sqft
CRANE_DAY_COST = 10_000
MODULE_WIDTH_FT = 8 # Standard module width
FOUNDATION_RATE = {"Concrete Slab": 40, "Helical Piles": 50} # Slab: $/sqft, Piles: $/sqft (conceptual divisor for pile count)
PILE_UNIT_COST = 1_000 # Cost per helical pile
SHIPPING_PER_MODULE = 8_000
ASSEMBLY_PER_MODULE = 3_000
DUTY_RATE = 0.06

FIXED_COSTS = {
    "Permits & Drawings": 14_000,
    "CSA Certification & QA": 30_000,
    "Brokerage & Entry Fees": 1_000,
    "Utility Connections": 11_000,
    "Landscaping Restoration": 5_000,
}
LEADS_CSV = Path("leads.csv")

# --- New Configuration for "WOW" Enhancements ---
# Model Types and their base adjustments or specific imagery
MODEL_TYPES = {
    "The Urban Studio": {"base_sqft": 400, "image": "assets/model_studio.jpg", "cost_modifier_sqft": 0},
    "The Garden Loft (1 Bed)": {"base_sqft": 600, "image": "assets/model_one_bed.jpg", "cost_modifier_sqft": 5}, # Slightly more complex
    "The Estate Suite (2 Bed)": {"base_sqft": 850, "image": "assets/model_two_bed.jpg", "cost_modifier_sqft": 10}, # Larger, more features
}

# Premium Upgrade Packages
PREMIUM_PACKAGES = {
    "Standard Luxury": {"cost_sqft": 20, "description": "High-quality essentials for a modern, comfortable living space."},
    "Designer Curated": {"cost_sqft": 40, "description": "Upgraded fixtures, flooring, and cabinetry with designer touches."},
    "Ultimate Bespoke": {"cost_sqft": 70, "description": "Top-of-the-line materials, smart home features, and custom detailing."},
}
DEFAULT_PREMIUM_PACKAGE = "Designer Curated"

# === CUSTOM CSS FOR "APPLE-LIKE" AESTHETICS & WOW FACTOR ================
def load_custom_css():
    st.markdown(f"""
    <style>
        /* --- General Theme & Body --- */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        body {{
            font-family: 'Inter', sans-serif;
            color: #333; /* Darker text for readability */
            background-color: #F0F2F6; /* Light, modern background */
        }}

        /* --- Main App Container --- */
        .main .block-container {{
            padding-top: 2rem;
            padding-bottom: 2rem;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
            max-width: 1200px; /* Control max width for better desktop layout */
        }}

        /* --- Headers & Text --- */
        h1, h2, h3 {{
            font-weight: 600;
            color: #1E3A5F; /* Hawk PD Dark Blue */
        }}
        h1 {{ font-size: 2.8rem; margin-bottom: 0.5rem; }}
        h2 {{ font-size: 1.9rem; margin-top: 1.5rem; margin-bottom: 0.8rem; border-bottom: 2px solid #D0D0D0; padding-bottom: 0.3rem; }}
        h3 {{ font-size: 1.4rem; color: #2c5282; /* Slightly lighter blue */ margin-bottom: 0.5rem;}}
        
        .stApp > header {{
            background-color: transparent; /* Hide default Streamlit header */
        }}
        
        /* --- Streamlit Widgets Styling --- */
        .stButton>button {{
            background-color: #4A90E2; /* Hawk PD Primary Blue */
            color: white;
            padding: 0.6rem 1.5rem;
            border-radius: 8px;
            border: none;
            font-weight: 500;
            transition: background-color 0.2s ease-in-out;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .stButton>button:hover {{
            background-color: #357ABD; /* Darker blue on hover */
        }}
        .stButton>button:focus {{
            outline: none;
            box-shadow: 0 0 0 3px rgba(74, 144, 226, 0.4);
        }}

        .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] > div {{
            border-radius: 6px;
            border: 1px solid #CBD5E0; /* Lighter border */
            padding: 0.5rem;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }}
        .stTextInput input:focus, .stNumberInput input:focus {{
             border-color: #4A90E2;
             box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.3);
        }}

        .stRadio > label {{ /* Make radio buttons look more like segmented controls */
            padding: 0.4rem 0.8rem;
            margin: 0.2rem;
            border: 1px solid #CBD5E0;
            border-radius: 6px;
            transition: background-color 0.2s, color 0.2s;
        }}
         .stRadio > label[data-baseweb="radio"]:hover {{
            background-color: #E2E8F0;
         }}
        .stRadio input[type="radio"]:checked + div {{ /* Style for selected radio */
            background-color: #4A90E2 !important;
            color: white !important;
            border-color: #4A90E2 !important;
        }}
        
        .stSlider [data-baseweb="slider"] {{
            padding-top: 10px; /* Add some space above slider */
        }}

        /* --- Card Styling for Sections --- */
        .form-section, .estimate-section, .hawk-advantage-section {{
            background-color: #FFFFFF;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
            margin-bottom: 1.5rem;
        }}
        
        /* --- Estimate Display Styling --- */
        .estimate-summary {{
            background: linear-gradient(135deg, #4A90E2 0%, #357ABD 100%);
            color: white;
            padding: 1.5rem;
            border-radius: 10px;
            text-align: center;
            margin-bottom: 1.5rem;
            box-shadow: 0 4px 8px rgba(0,0,0,0.15);
        }}
        .estimate-summary .label {{
            font-size: 0.9rem;
            opacity: 0.8;
            text-transform: uppercase;
            margin-bottom: 0.2rem;
        }}
        .estimate-summary .price {{
            font-size: 2.4rem;
            font-weight: 700;
            line-height: 1.2;
        }}
        .estimate-summary .price-separator {{
            font-size: 1.2rem;
            font-weight: 300;
            margin: 0.5rem 0;
        }}
        .estimate-summary .price-per-sqft {{
            font-size: 0.9rem;
            opacity: 0.9;
            margin-top: 0.7rem;
        }}
        
        /* --- Dataframe Styling --- */
        .stDataFrame {{
            border-radius: 8px;
            overflow: hidden; /* Ensures border radius is respected by table */
        }}
        
        /* --- Expander styling --- */
        .stExpander {{
            border: 1px solid #E2E8F0;
            border-radius: 8px;
            background-color: #FAFBFC;
        }}
        .stExpander header {{
            font-weight: 500;
            color: #1E3A5F;
        }}

        /* --- Logo & Hero --- */
        .logo-container img {{
            max-height: 60px; /* Adjust as needed */
            margin-bottom: 1rem;
        }}
        .hero-banner img {{
            width: 100%;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 6px 15px rgba(0,0,0,0.1);
        }}

        /* --- Share Button --- */
        .share-button-container {{
            text-align: center;
            margin-top: 1.5rem;
        }}

        /* --- Mobile Responsiveness Tweaks --- */
        @media (max-width: 768px) {{
            .main .block-container {{
                padding-left: 1rem;
                padding-right: 1rem;
            }}
            h1 {{ font-size: 2rem; }}
            h2 {{ font-size: 1.5rem; }}
            .estimate-summary .price {{ font-size: 2rem; }}

            /* Stack columns on mobile for better readability */
            .stHorizontal {{
                flex-direction: column !important; /* Force columns to stack */
            }}
            .stHorizontal > div {{
                width: 100% !important; /* Make each column take full width */
                margin-bottom: 1rem; /* Add space between stacked columns */
            }}
        }}
    </style>
    """, unsafe_allow_html=True)

# === UTILITIES ============================================================

def margin_low_high(base: float) -> Tuple[int, int]:
    p = base * (1 + MARKUP)
    return round(p * LOW_MULT), round(p * HIGH_MULT)

def module_count(area: int, floors: int) -> int:
    # Adjusted logic: A 280 sqft module is quite small if that's the effective build area per module.
    # Assuming 280 sqft is a rough guide for shipping/handling.
    # For a premium feel, actual module sizes might be larger or more integrated.
    # This calculation will heavily influence "module-based" costs.
    # Let's say a typical module is ~400-500 effective sqft for assembly/shipping purposes.
    # This example keeps your logic but it's a key area to refine based on your actual modular system.
    base_modules = math.ceil(area / 400) # e.g. if average module contributes 400 sqft build area
    return base_modules + (1 if floors == 2 and base_modules > 0 else 0) # Add an extra module for stairs/structure in 2-story

def footprint_display(area: int, floors: int) -> str:
    # This is a simplification for display. Actual footprint depends on design.
    # Assuming roughly rectangular.
    if floors == 1:
        # Try to make it somewhat squarish or typical garden suite proportions
        if area <= 400: width_approx = 16 # ~16x25
        elif area <= 650: width_approx = 20 # ~20x32
        else: width_approx = 24 # ~24x40
        length_approx = area / width_approx
        return f"Approx. Footprint: {width_approx:.0f} ft W × {length_approx:.1f} ft L"
    else: # 2 floors
        footprint_area = area / 2
        if footprint_area <= 300: width_approx = 14 # ~14x21
        elif footprint_area <= 500: width_approx = 16 # ~16x31
        else: width_approx = 20 # ~20x25
        length_approx = footprint_area / width_approx
        return f"Approx. Footprint (per floor): {width_approx:.0f} ft W × {length_approx:.1f} ft L"


# === Google Places city picker (Unchanged from your code) =================
def city_autocomplete(api_key: str) -> Tuple[str, str]:
    eid = f"city_{uuid.uuid4().hex[:8]}"
    html = f"""
    <input id='{eid}' style='width:100%;padding:10px;border:1px solid #ccc;border-radius:6px' placeholder='Enter City (e.g., Toronto)'>
    <script src='https://maps.googleapis.com/maps/api/js?key={api_key}&libraries=places'></script>
    <script>
      const input=document.getElementById('{eid}');
      const ac=new google.maps.places.Autocomplete(input, {{types:['(cities)']}});
      ac.addListener('place_changed',() => {{
        const p=ac.getPlace();
        const g=(t)=>(p.address_components||[]).find(c=>c.types.includes(t))?.long_name||'';
        const city=g('locality')||g('administrative_area_level_1')||p.name;
        const country=g('country');
        window.parent.postMessage({{isStreamlitMessage:true,type:'city',city:city,country:country}}, '*');
      }});
    </script>"""
    res = components.html(html, height=48, scrolling=False) # Increased height for better touch
    if isinstance(res, dict) and res.get("type") == "city":
        return res.get("city", ""), res.get("country", "")
    return "", ""

# === PRICING BREAKDOWN ====================================================
def build_breakdown(
    area: int,
    floors: int,
    foundation: str,
    selected_model: str, # New input
    premium_package_name: str # New input
) -> Tuple[pd.DataFrame,int,int,int]:

    mods = module_count(area, floors)
    rows: List[Tuple[str,int,int]] = []

    # --- Apply Model & Premium Package Cost Adjustments ---
    model_cost_modifier_sqft = MODEL_TYPES[selected_model].get("cost_modifier_sqft", 0)
    premium_package_cost_sqft = PREMIUM_PACKAGES[premium_package_name]["cost_sqft"]

    current_module_base_rate = MODULE_BASE_RATE + model_cost_modifier_sqft
    # Premium is now separate and more descriptive
    
    # fixed rows
    for label, cost in FIXED_COSTS.items():
        rows.append((label, *margin_low_high(cost)))

    # variable rows
    rows.append(("Site Preparation", *margin_low_high(area * SITE_PREP_RATE)))
    
    if foundation == "Concrete Slab":
        f_base = area * FOUNDATION_RATE[foundation]
    else: # Helical Piles
        # Simplified: assume FOUNDATION_RATE["Helical Piles"] is a divisor for area to get # of piles
        # e.g., if it's 50, it means 1 pile per 50 sqft. This is highly conceptual.
        num_piles = math.ceil(area / FOUNDATION_RATE[foundation]) 
        f_base = num_piles * PILE_UNIT_COST
    rows.append((f"Foundation ({foundation})", *margin_low_high(f_base)))

    mod_base_cost = area * current_module_base_rate
    prem_base_cost = area * premium_package_cost_sqft
    
    rows.append(("CSA Approved Modular Units", *margin_low_high(mod_base_cost)))
    if prem_base_cost > 0:
        rows.append((f"Upgrades: {premium_package_name}", *margin_low_high(prem_base_cost)))
    
    # Duty applies to imported modules and potentially some premium materials
    duty_applicable_cost = mod_base_cost + (prem_base_cost * 0.7) # Assume 70% of premium upgrades are dutiable
    rows.append(("Duty & Importation", *margin_low_high(DUTY_RATE * duty_applicable_cost)))


    rows.append((f"Shipping to Site ({mods} mod.)", *margin_low_high(mods * SHIPPING_PER_MODULE)))
    rows.append((f"Module Assembly ({mods} mod.)", *margin_low_high(mods * ASSEMBLY_PER_MODULE)))
    

    crane_days = 1
    if mods > 4: crane_days = 2
    if floors == 2 and mods > 2 : crane_days = 2 # Two story likely needs more crane time
    if area > 800 and floors == 2: crane_days = 3 # Large two story

    rows.append(("Crane Services", *margin_low_high(crane_days * CRANE_DAY_COST)))
    rows.append(("Project Finishing & On-Site Work", *margin_low_high(area * PROJECT_COMPLETION_RATE)))

    # Define category order for the final DataFrame
    category_order = [
        "Permits & Drawings", "Site Preparation", f"Foundation ({foundation})",
        "CSA Approved Modular Units",
        (f"Upgrades: {premium_package_name}" if prem_base_cost > 0 else None),
        "CSA Certification & QA", f"Shipping to Site ({mods} mod.)",
        "Brokerage & Entry Fees", "Duty & Importation", "Crane Services",
        f"Module Assembly ({mods} mod.)", "Utility Connections",
        "Project Finishing & On-Site Work", "Landscaping Restoration"
    ]
    category_order = [cat for cat in category_order if cat is not None] # Remove None if no premium

    df = pd.DataFrame(rows, columns=["Category", "Low ($)", "High ($)"]).set_index("Category")
    # Reorder and fill missing (if any, though unlikely with this setup)
    df = df.loc[df.index.intersection(category_order)].reindex(category_order).dropna(how='all').reset_index()

    low, high = int(df["Low ($)"].sum()), int(df["High ($)"].sum())
    return df, low, high, mods

# === PERSIST LEAD & EMAIL (Placeholder for actual email sending) ========
def save_lead(d: Dict[str,Any]):
    fresh = not LEADS_CSV.exists()
    # Ensure all keys exist in the dictionary before writing
    fieldnames_order = [
        "timestamp", "name", "email", "phone", "city", "country", "model_type", 
        "area_ft2", "floors", "modules", "foundation", "premium_package", 
        "low_total", "high_total", "notes"
    ]
    # Prepare data with all fieldnames, filling missing ones with None or empty string
    row_data = {field: d.get(field) for field in fieldnames_order}

    with LEADS_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames_order)
        if fresh:
            w.writeheader()
        w.writerow(row_data)

def send_email_quote_to_user(lead_data: Dict[str, Any]):
    # THIS IS A PLACEHOLDER. Implement actual email sending here.
    # Example: Use smtplib with Gmail or a service like SendGrid.
    # For now, we just simulate success.
    # st.success(f"A copy of your estimate has been sent to {lead_data['email']}!")
    # You might want to include a nicely formatted summary of their choices in the email.
    pass

# === SHARE FUNCTIONALITY =================================================
def generate_share_summary(config_data: Dict[str, Any], low: int, high: int) -> str:
    summary = f"Check out this Garden Suite estimate from Hawk Property Developments!\n\n"
    summary += f"Model: {config_data['model_type']}\n"
    summary += f"Size: {config_data['area_ft2']} sq ft, {config_data['floors']} floor(s)\n"
    summary += f"Foundation: {config_data['foundation']}\n"
    summary += f"Upgrades: {config_data['premium_package']}\n"
    summary += f"Estimated Budget: ${low:,} - ${high:,}\n\n"
    summary += f"Explore your own options at: {st.secrets.get('APP_BASE_URL', 'YOUR_APP_URL_HERE')}\n" # Replace with your app's deployed URL
    return summary

def share_via_email_link(summary_text: str, recipient_email: str = "") -> str:
    subject = "Hawk PD Garden Suite Estimate"
    body = summary_text
    return f"mailto:{recipient_email}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"


# === MAIN UI ==============================================================
def main():
    st.set_page_config("Garden Suite Estimator | Hawk PD", "🦅", layout="wide")
    load_custom_css()

    # --- Header & Logo ---
    c1, c2 = st.columns([1,3])
    with c1:
        try:
            st.image(Image.open("assets/hawk_logo.png"), width=200) # Adjust width as needed
        except FileNotFoundError:
            st.markdown("<h1 style='font-size: 1.5rem; color: #1E3A5F;'>HAWK PROPERTY DEVELOPMENTS</h1>", unsafe_allow_html=True)
    with c2:
        st.markdown("<h1 style='margin-top:10px; margin-bottom:0;'>Garden Suite Budget Estimator</h1>", unsafe_allow_html=True)
        st.caption("Craft your dream backyard oasis and get a preliminary budget in minutes. Final costs exclude HST and are subject to site verification & detailed design.")
    
    st.markdown("---") # Visual separator

    # --- Hero Banner (Optional but adds WOW) ---
    try:
        st.image(Image.open("assets/hero_banner.jpg"), caption="Imagine the Possibilities...")
        st.markdown("---")
    except FileNotFoundError:
        pass # If no hero banner, just continue

    # --- Main Layout: Inputs on Left, Estimate on Right ---
    # On mobile, these will stack thanks to CSS, but on desktop, they are side-by-side.
    col_inputs, col_estimate = st.columns(2, gap="large")

    # --- INPUTS SECTION ---
    with col_inputs:
        st.markdown("<div class='form-section'>", unsafe_allow_html=True)
        st.header("1. Your Vision")

        selected_model = st.selectbox(
            "Select a Base Model Style:",
            options=list(MODEL_TYPES.keys()),
            help="Each model has unique architectural features and a slightly different base cost."
        )
        # Display image for selected model
        try:
            st.image(Image.open(MODEL_TYPES[selected_model]["image"]), caption=f"Concept: {selected_model}", use_column_width=True)
        except FileNotFoundError:
            st.caption("Image coming soon for this model.")


        initial_area = MODEL_TYPES[selected_model]["base_sqft"]
        area = st.slider("Suite Size (sq ft)", 350, 1200, initial_area, 10, help="Total interior livable space.")
        
        floors = st.radio("Number of Floors:", [1,2], horizontal=True, index=0)
        
        st.info(footprint_display(area, floors)) # Display approximate footprint

        foundation = st.selectbox(
            "Foundation Type:",
            ["Concrete Slab", "Helical Piles"],
            help="Concrete slabs are common. Helical piles can be better for sloped sites or near trees."
        )

        premium_package = st.selectbox(
            "Select Interior Upgrade Package:",
            options=list(PREMIUM_PACKAGES.keys()),
            index=list(PREMIUM_PACKAGES.keys()).index(DEFAULT_PREMIUM_PACKAGE), # Default selection
            help="Choose a package that reflects your desired level of luxury and features."
        )
        st.caption(PREMIUM_PACKAGES[premium_package]["description"])
        st.markdown("</div>", unsafe_allow_html=True)


        st.markdown("<div class='form-section'>", unsafe_allow_html=True)
        st.header("2. Project Location")
        # Use secrets for API key if available (recommended for deployed apps)
        # if "google_places_api_key" in st.secrets:
        #     city, country = city_autocomplete(st.secrets["google_places_api_key"])
        # else:
        #     st.warning("Google Places API key not found. Please enter city manually.", icon="⚠️")
        city = st.text_input("Project City (e.g., Toronto)") # Simplified if API key is an issue
        country = st.text_input("Project Country (e.g., Canada)", value="Canada") # Default
        st.markdown("</div>", unsafe_allow_html=True)


    # --- ESTIMATE SECTION ---
    with col_estimate:
        st.markdown("<div class='estimate-section'>", unsafe_allow_html=True)
        st.header("Your Estimated Budget")

        df_breakdown, low_estimate, high_estimate, num_modules = build_breakdown(
            area, floors, foundation, selected_model, premium_package
        )

        # --- Stylish Price Display ---
        st.markdown(
            f"""
            <div class='estimate-summary'>
                <div class='label'>Preliminary Budget Range</div>
                <div class='price'>${low_estimate:,}</div>
                <div class='price-separator'>to</div>
                <div class='price'>${high_estimate:,}</div>
                <div class='price-per-sqft'>
                    Approx. ${low_estimate//area:,} - ${high_estimate//area:,} per sq ft
                </div>
            </div>
            """, unsafe_allow_html=True
        )
        
        st.caption(f"This estimate assumes approximately **{num_modules} factory-built modules** for efficient assembly. Your final design may vary.")

        with st.expander("View Detailed Cost Breakdown"):
            # Refine dataframe display
            df_display = df_breakdown.copy()
            df_display["Low ($)"] = df_display["Low ($)"].apply(lambda x: f"${x:,.0f}")
            df_display["High ($)"] = df_display["High ($)"].apply(lambda x: f"${x:,.0f}")
            st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        st.markdown("</div>", unsafe_allow_html=True)

        # --- HAWK PD ADVANTAGE (WOW Factor) ---
        st.markdown("<div class='hawk-advantage-section'>", unsafe_allow_html=True)
        st.subheader("The Hawk PD Advantage 🦅")
        st.markdown("""
        *   **Precision & Quality:** Built in a climate-controlled factory for superior craftsmanship.
        *   **Speed & Efficiency:** Modular construction significantly reduces on-site build times.
        *   **Cost Predictability:** Transparent pricing and fewer surprises compared to traditional builds.
        *   **Luxury Design:** Premium materials and finishes come standard with our approach.
        *   **Sustainability Focus:** Minimized waste and optimized material usage.
        """)
        st.markdown("</div>", unsafe_allow_html=True)


    st.markdown("---")

    # --- LEAD CAPTURE & SHARE FORM ---
    st.header("Ready for the Next Step?")
    st.markdown("Save your estimate and let our specialists provide a more detailed consultation.")

    form_cols = st.columns([2,1]) # Make form fields wider

    with form_cols[0]:
        with st.form("lead_form", clear_on_submit=True):
            st.subheader("Get Your Personalized Estimate Summary")
            name = st.text_input("Full Name*", placeholder="Your Name")
            email = st.text_input("Email Address*", placeholder="you@example.com")
            phone = st.text_input("Phone Number (Optional)", placeholder="(555) 123-4567")
            notes = st.text_area("Specific Questions or Notes (Optional)", height=100, placeholder="e.g., Sloped backyard, specific design ideas...")
            
            submitted = st.form_submit_button("📧 Email Me My Quote & Connect")

            if submitted:
                if not name or not email:
                    st.error("Please provide your Name and Email Address.", icon="🚨")
                else:
                    lead_data = {
                        "timestamp": dt.datetime.utcnow().isoformat(timespec="seconds"),
                        "name": name, "email": email, "phone": phone,
                        "city": city, "country": country,
                        "model_type": selected_model, "area_ft2": area, "floors": floors,
                        "modules": num_modules, "foundation": foundation,
                        "premium_package": premium_package,
                        "low_total": low_estimate, "high_total": high_estimate,
                        "notes": notes,
                    }
                    save_lead(lead_data)
                    send_email_quote_to_user(lead_data) # Placeholder for actual email
                    
                    st.success(f"Thank you, {name}! Your estimate details have been noted. We'll be in touch soon. A summary will also be sent to {email}.", icon="✅")
                    st.balloons()
    
    with form_cols[1]: # Share section
        st.markdown("<div class='share-button-container' style='margin-top:2.5rem;'>", unsafe_allow_html=True) # Align with button better
        st.subheader("Share Your Vision!")
        config_data_for_share = {
            "model_type": selected_model, "area_ft2": area, "floors": floors,
            "foundation": foundation, "premium_package": premium_package,
        }
        share_summary_text = generate_share_summary(config_data_for_share, low_estimate, high_estimate)
        
        # Using a link that opens the default email client
        share_link = share_via_email_link(share_summary_text)
        st.markdown(f'<a href="{share_link}" target="_blank"><button style="background-color: #5cb85c; color: white; padding: 0.6rem 1.5rem; border-radius: 8px; border: none; font-weight: 500; cursor: pointer; width: 100%;">Share via Email</button></a>', unsafe_allow_html=True)
        st.caption("Share this configuration with friends or family.")
        st.markdown("</div>", unsafe_allow_html=True)


    st.markdown("---")
    st.caption("© " + str(dt.date.today().year) + " Hawk Property Developments Inc. All rights reserved. "
               "Pricing and offerings subject to change without notice. "
               "This estimator provides a preliminary budget for planning purposes only. "
               "Consult with a Hawk PD representative for a formal quotation. HST is not included.")

if __name__ == "__main__":
    main()