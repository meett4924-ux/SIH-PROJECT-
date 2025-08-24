import math
import time
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

# ----------------------------
# Domain constants
# ----------------------------
SOIL_TARGET_RANGE = {
    "रेतीली (Sandy)": (0.10, 0.18),
    "दोमट (Loam)": (0.18, 0.28),
    "चिकनी (Clay)": (0.25, 0.35),
}

SOIL_RAW_MM_PER_M = {
    "रेतीली (Sandy)": 60,
    "दोमट (Loam)": 90,
    "चिकनी (Clay)": 120,
}

ROOT_DEPTH_M = {
    "शुरुआती अवस्था": 0.3,
    "वनस्पति अवस्था": 0.6,
    "फूल आने की अवस्था": 0.8,
    "फल आने की अवस्था": 1.0,
}

KC_STAGE = {
    "शुरुआती अवस्था": 0.6,
    "वनस्पति अवस्था": 0.95,
    "फूल आने की अवस्था": 1.05,
    "फल आने की अवस्था": 0.9,
}

# ----------------------------
# Helper Functions
# ----------------------------
def area_to_sq_m(area_value: float, unit: str) -> float:
    if unit == "एकड़":
        return area_value * 4046.8564224
    if unit == "हेक्टेयर":
        return area_value * 10000.0
    if unit == "m²":
        return area_value
    return area_value

def simple_eto_mm_per_day(tmin_c: float, tmax_c: float) -> float:
    tmean = (tmin_c + tmax_c) / 2.0
    td = max(tmax_c - tmin_c, 0)
    eto = max(0.0, 0.0023 * (tmean + 17.8) * math.sqrt(td) * 10)
    return eto

def irrigation_need_liters(soil_type, stage, current_vwc, target_low, area_m2, tmin_c, tmax_c):
    root_m = ROOT_DEPTH_M[stage]
    raw_mm_per_m = SOIL_RAW_MM_PER_M[soil_type]
    deficit_frac = max(target_low - current_vwc, 0.0) / max(target_low, 1e-6)
    deficit_mm = deficit_frac * raw_mm_per_m * root_m
    eto = simple_eto_mm_per_day(tmin_c, tmax_c)
    kc = KC_STAGE[stage]
    etc_mm = kc * eto
    total_mm = max(0.0, deficit_mm + etc_mm)
    liters = total_mm * area_m2
    return liters, deficit_mm, etc_mm

# ----------------------------
# Streamlit UI
# ----------------------------
st.set_page_config(page_title="💧 स्मार्ट सिंचाई प्रणाली", page_icon="🌾", layout="wide")

st.markdown("<h1 style='text-align: center; color: green;'>💧 स्मार्ट सिंचाई प्रणाली </h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size:18px;'>यह डेमो आपको बताएगा कि कब और कितनी सिंचाई करनी है। फसल, मिट्टी और मौसम डेटा दर्ज करें और उचित सलाह प्राप्त करें।</p>", unsafe_allow_html=True)

# Sidebar Inputs
with st.sidebar:
    st.header("📋 खेत की जानकारी")
    crop = st.text_input("फसल का नाम (जैसे गेहूँ, धान, टमाटर)", value="टमाटर")
    soil_type = st.selectbox("मिट्टी का प्रकार चुनें", list(SOIL_TARGET_RANGE.keys()))
    area_value = st.number_input("खेत का क्षेत्रफल दर्ज करें", value=0.25, min_value=0.0, step=0.01)
    area_unit = st.selectbox("इकाई", ["एकड़", "हेक्टेयर", "m²"], index=0)
    stage = st.selectbox("फसल की अवस्था", list(ROOT_DEPTH_M.keys()), index=1)

    st.header("🌡 मौसम विवरण")
    tmin = st.number_input("आज का न्यूनतम तापमान (°C)", value=22.0)
    tmax = st.number_input("आज का अधिकतम तापमान (°C)", value=33.0)

    st.header("💧 मिट्टी की नमी")
    mode = st.radio("नमी डेटा इनपुट मोड", ["मैनुअल", "सिमुलेट"], horizontal=True)
    if mode == "मैनुअल":
        vwc = st.slider("मिट्टी की नमी (VWC)", 0.0, 0.6, 0.16, 0.01)
    else:
        seed = st.number_input("सिमुलेशन सीड", value=42, step=1)
        np.random.seed(seed)
        vwc = float(np.clip(np.random.normal(0.16, 0.03), 0, 0.6))
        st.metric("सिमुलेटेड नमी", f"{vwc:.2f}")

area_m2 = area_to_sq_m(area_value, area_unit)
low, high = SOIL_TARGET_RANGE[soil_type]

# Advisory
liters, deficit_mm, etc_mm = irrigation_need_liters(soil_type, stage, vwc, low, area_m2, tmin, tmax)

col1, col2, col3 = st.columns(3)
with col1:
    st.subheader("स्थिति")
    if vwc < low:
        st.success("🌱 अभी सिंचाई करें (नमी कम है)")
    elif vwc > high:
        st.info("✅ सिंचाई की आवश्यकता नहीं")
    else:
        st.warning("⚠️ निगरानी रखें (नमी सही है)")

with col2:
    st.subheader("अनुमानित पानी की जरूरत")
    st.metric("आज का पानी (लीटर)", f"{liters:,.0f} L")
    st.caption(f"घाटा: {deficit_mm:.1f} mm · ETc: {etc_mm:.1f} mm")

with col3:
    st.subheader("खेत विवरण")
    st.metric("क्षेत्रफल", f"{area_m2:,.0f} m²")
    st.metric("लक्षित नमी सीमा", f"{low:.2f} – {high:.2f}")

st.divider()

## ----------------------------
# 7 दिन की सिंचाई योजना
# ----------------------------
st.subheader("📅 7 दिन की सिंचाई योजना")

dates = [datetime.today() + timedelta(days=i) for i in range(7)]
plan_data = []

for d in dates:
    # हर दिन का मौसम थोड़ा बदलता हुआ सिमुलेट करें
    tmin_d = tmin + np.random.uniform(-1, 1)
    tmax_d = tmax + np.random.uniform(-1, 1)
    eto_d = simple_eto_mm_per_day(tmin_d, tmax_d)
    kc = KC_STAGE[stage]
    etc_mm_d = kc * eto_d
    liters_d = etc_mm_d * area_m2
    plan_data.append({"तारीख": d.strftime("%d-%m-%Y"), "अनुमानित ETc (mm)": round(etc_mm_d, 2), "पानी की आवश्यकता (लीटर)": round(liters_d, 2)})

df_plan = pd.DataFrame(plan_data)

st.dataframe(df_plan, use_container_width=True)

# डाउनलोड बटन
csv = df_plan.to_csv(index=False).encode('utf-8')
st.download_button(label="⬇️ योजना डाउनलोड करें (CSV)", data=csv, file_name="sichai_yajana.csv", mime="text/csv")



