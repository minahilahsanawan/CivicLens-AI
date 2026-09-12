import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import streamlit as st
import altair as alt
from dotenv import load_dotenv

load_dotenv()
try:
    for secret_name in ("GROQ_API_KEY",):
        if not os.getenv(secret_name) and st.secrets.get(secret_name, ""):
            os.environ[secret_name] = st.secrets[secret_name]
except Exception:
    pass

from utils.database import STATUS_OPTIONS, create_complaint, get_complaint, get_complaints, get_events, save_feedback, save_resolution, update_status
from utils.rag import route_issue
from utils.vision import classify_image, verify_resolution

st.set_page_config(page_title="CivicLens AI", page_icon="CL", layout="wide", initial_sidebar_state="expanded")
BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

if "theme" not in st.session_state:
    st.session_state["theme"] = "Light"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&family=Noto+Naskh+Arabic:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #f5f1ed; color: #202124; }
[data-testid="stSidebar"] { background: #17191d; border-right: 1px solid #2c3036; }
[data-testid="stSidebar"] * { color: #edf3ff !important; }
[data-testid="stSidebar"] .stCaption, [data-testid="stSidebar"] small { color: #aebbd2 !important; }
[data-testid="stSidebar"] .stRadio label { background: transparent; padding: .35rem .5rem; border-radius: 8px; }
h1, h2, h3 { font-family: 'Manrope', sans-serif; color: #202124; }
.hero { background: linear-gradient(120deg,#24262a,#3a2721); border-radius: 22px; padding: 2rem 2.2rem; color: white; margin-bottom: 1.4rem; border: 1px solid #4b3a34; }
.hero h1 { color: white; margin: 0 0 .45rem; font-size: 2.35rem; line-height: 1.35; }
.hero p { color: #f4d6c8; margin: 0; font-size: 1.05rem; }
.eyebrow { color: #ff8a6b; text-transform: uppercase; letter-spacing: .14em; font-size: .76rem; font-weight: 700; }
.card { background: #fffdfa; border: 1px solid #e2d8d0; border-radius: 16px; padding: 1.15rem; box-shadow: 0 6px 22px rgba(68,45,31,.07); }
.ticket { background: #fff1eb; border: 1px solid #efb19d; border-left: 5px solid #e97855; border-radius: 12px; padding: 1rem 1.2rem; }
.ticket-id { font-family: 'Manrope'; color: #a33e25; font-size: 1.25rem; font-weight: 800; }
.chip { display: inline-block; background: #fbe0d5; color: #713323; padding: .28rem .62rem; border-radius: 999px; margin: .15rem .2rem .15rem 0; font-size: .82rem; font-weight: 600; }
.small-muted { color: #687078; font-size: .87rem; }
div[data-testid="stMetric"] { background: #fffdfa !important; border: 1px solid #e2d8d0; padding: .85rem; border-radius: 14px; }
div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricValue"], div[data-testid="stMetric"] [data-testid="stMetricDelta"] { color: #202124 !important; }
.stButton > button[kind="primary"] { background: #e97855; border: 0; color: white; font-weight: 700; }
.stButton > button { border-radius: 9px; min-height: 2.6rem; }
/* Explicit light controls prevent invisible text when a user's browser prefers dark mode. */
.stApp [data-testid="stWidgetLabel"] p, .stApp label, .stApp .stMarkdown p, .stApp [data-testid="stCaptionContainer"] p { color: #30343a !important; }
.stApp input, .stApp textarea, .stApp [data-baseweb="input"], .stApp [data-baseweb="textarea"] { color: #202124 !important; background: #fffdfa !important; }
.stApp [data-baseweb="select"] > div, .stApp [data-baseweb="select"] * { color: #202124 !important; background: #fffdfa !important; }
.stApp [data-testid="stNumberInput"] button { color: #713323 !important; background: #fbe0d5 !important; }
.stApp [data-testid="stFileUploader"] section { background: #fffdfa !important; border: 1px dashed #cf9d8b !important; }
.stApp [data-testid="stFileUploader"] section * { color: #30343a !important; }
.stApp [data-testid="stExpander"] summary { background: #fffdfa !important; color: #202124 !important; }
.stApp [data-testid="stExpander"] summary p { color: #202124 !important; }
.stApp [data-testid="stDataFrame"] { border: 1px solid #e2d8d0; }
.urdu { direction: rtl; text-align: right; font-family: 'Noto Naskh Arabic', serif; line-height: 2; }
.urdu h1, .urdu p { font-family: 'Noto Naskh Arabic', serif; }
</style>
""", unsafe_allow_html=True)

THEME_CSS = """
<style>
/* Final theme layer: the same component hierarchy remains readable in both modes. */
.stApp { background: var(--page-bg) !important; color: var(--body-text) !important; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp li { color: var(--body-text) !important; }
.stApp [data-testid="stWidgetLabel"] p, .stApp label, .stApp [data-testid="stCaptionContainer"] p { color: var(--muted-text) !important; }
div[data-testid="stMetric"] { background: var(--card-bg) !important; border-color: var(--border) !important; }
div[data-testid="stMetric"] label, div[data-testid="stMetric"] [data-testid="stMetricValue"], div[data-testid="stMetric"] [data-testid="stMetricDelta"] { color: var(--body-text) !important; }
div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.55rem !important; line-height: 1.2 !important; }
.stApp input, .stApp textarea, .stApp [data-baseweb="input"], .stApp [data-baseweb="textarea"], .stApp [data-baseweb="select"] > div { background: var(--control-bg) !important; color: var(--body-text) !important; border-color: var(--border) !important; }
.stApp input::placeholder, .stApp textarea::placeholder { color: var(--placeholder) !important; opacity: 1 !important; }
.stApp [data-baseweb="select"] *, .stApp [data-baseweb="input"] *, .stApp [data-baseweb="textarea"] * { color: var(--body-text) !important; }
.stApp [data-testid="stFileUploader"] section { background: var(--control-bg) !important; border-color: var(--accent) !important; }
.stApp [data-testid="stFileUploader"] section * { color: var(--body-text) !important; }
.stApp [data-testid="stExpander"] details, .stApp [data-testid="stExpander"] summary { background: var(--card-bg) !important; color: var(--body-text) !important; border-color: var(--border) !important; }
.stApp [data-testid="stDataFrame"] { border-color: var(--border) !important; }
.stButton > button { color: var(--body-text) !important; border-color: var(--border) !important; }
.stButton > button[kind="primary"] { background: var(--accent) !important; color: #ffffff !important; }
</style>
"""
theme_vars = {"Light": ("#f6f2ed", "#202124", "#58616b", "#fffdfa", "#fffdfa", "#dfd5cc", "#a8afb6", "#dfd5cc"), "Dark": ("#17191d", "#f5f1ed", "#c6bdb7", "#24272c", "#202328", "#3d4249", "#9c948f", "#302f2d")}[st.session_state["theme"]]
st.markdown(THEME_CSS.replace("var(--page-bg)", theme_vars[0]).replace("var(--body-text)", theme_vars[1]).replace("var(--muted-text)", theme_vars[2]).replace("var(--card-bg)", theme_vars[3]).replace("var(--control-bg)", theme_vars[4]).replace("var(--border)", theme_vars[5]).replace("var(--placeholder)", theme_vars[6]).replace("var(--accent)", "#e97855"), unsafe_allow_html=True)

# These selectors intentionally have higher specificity than Streamlit's generated
# markdown selectors, which otherwise make dark-mode descriptions disappear.
if st.session_state["theme"] == "Dark":
    st.markdown("""<style>
    .stApp .hero p, .stApp .card b, .stApp .small-muted { color: #f5f1ed !important; }
    .stApp .stMarkdown p, .stApp [data-testid="stCaptionContainer"] p,
    .stApp [data-testid="stWidgetLabel"] p { color: #f5f1ed !important; }
    .stApp [data-testid="stSidebar"] .stMarkdown p,
    .stApp [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
    .stApp [data-testid="stSidebar"] label { color: #f5f1ed !important; }
    .stApp [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #c6bdb7 !important; }
    </style>""", unsafe_allow_html=True)
else:
    st.markdown("""<style>
    .stApp .hero p { color: #f4d6c8 !important; }
    .stApp .card b, .stApp .small-muted, .stApp .stMarkdown p,
    .stApp [data-testid="stCaptionContainer"] p,
    .stApp [data-testid="stWidgetLabel"] p { color: #30343a !important; }
    .stApp [data-testid="stSidebar"] .stMarkdown p,
    .stApp [data-testid="stSidebar"] label { color: #edf3ff !important; }
    .stApp [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #aebbd2 !important; }
    </style>""", unsafe_allow_html=True)

# Final accessible theme override. It intentionally comes after every earlier
# style block so Streamlit's generated widget rules cannot hide text.
if st.session_state["theme"] == "Dark":
    st.markdown("""<style>
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background: #17191d !important;
        color: #f5f1ed !important;
    }
    [data-testid="stSidebar"] {
        background: #101214 !important;
        border-right: 1px solid #34383e !important;
    }
    [data-testid="stSidebar"] * { color: #f5f1ed !important; }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #c9c1bb !important; }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p,
    .stApp label, .stApp li, .stApp span, .stApp small { color: #f5f1ed !important; }
    .stApp .hero {
        background: linear-gradient(135deg, #24262a 0%, #422b23 100%) !important;
        border: 1px solid #704638 !important;
    }
    .stApp .hero h1, .stApp .hero p { color: #ffffff !important; }
    .stApp .hero .eyebrow { color: #ff896b !important; }
    .stApp .card, .stApp div[data-testid="stMetric"],
    .stApp [data-testid="stExpander"] details,
    .stApp [data-testid="stExpander"] summary {
        background: #24272c !important;
        color: #f5f1ed !important;
        border-color: #3d4249 !important;
    }
    .stApp .card *, .stApp .small-muted { color: #d9d1cb !important; }
    .stApp .card b, .stApp .ticket-id { color: #ffffff !important; }
    .stApp .ticket {
        background: #2f2421 !important;
        color: #f5f1ed !important;
        border-color: #e97855 !important;
    }
    .stApp .ticket *, .stApp .chip { color: #ffffff !important; }
    .stApp .chip { background: #663a2e !important; border: 1px solid #9b5b46 !important; }
    .stApp input, .stApp textarea,
    .stApp [data-baseweb="input"], .stApp [data-baseweb="textarea"],
    .stApp [data-baseweb="select"] > div {
        background: #202328 !important;
        color: #ffffff !important;
        border-color: #60666e !important;
    }
    .stApp input::placeholder, .stApp textarea::placeholder { color: #b8b0aa !important; opacity: 1 !important; }
    .stApp [data-baseweb="select"] *, .stApp [data-baseweb="input"] *,
    .stApp [data-baseweb="textarea"] * { color: #ffffff !important; }
    [data-baseweb="popover"], [data-baseweb="menu"] { background: #24272c !important; }
    [data-baseweb="popover"] *, [data-baseweb="menu"] * { color: #ffffff !important; }
    .stApp [data-testid="stFileUploader"] section { background: #202328 !important; border-color: #e97855 !important; }
    .stApp [data-testid="stFileUploader"] section * { color: #f5f1ed !important; }
    .stApp [data-testid="stNumberInput"] button { background: #663a2e !important; color: #ffffff !important; }
    .stApp div[data-testid="stMetric"] label,
    .stApp div[data-testid="stMetric"] [data-testid="stMetricValue"],
    .stApp div[data-testid="stMetric"] [data-testid="stMetricDelta"] { color: #ffffff !important; }
    .stApp div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.45rem !important; }
    .stApp .stButton > button { background: #24272c !important; color: #ffffff !important; border-color: #60666e !important; }
    .stApp .stButton > button[kind="primary"] { background: #e97855 !important; color: #ffffff !important; border-color: #e97855 !important; }
    </style>""", unsafe_allow_html=True)
else:
    st.markdown("""<style>
    html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"] {
        background: #f6f2ed !important;
        color: #202124 !important;
    }
    [data-testid="stSidebar"] {
        background: #fffdfa !important;
        border-right: 1px solid #dfd5cc !important;
    }
    [data-testid="stSidebar"] * { color: #202124 !important; }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #687078 !important; }
    .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p,
    .stApp label, .stApp li, .stApp span, .stApp small { color: #202124 !important; }
    .stApp .hero {
        background: linear-gradient(135deg, #24262a 0%, #422b23 100%) !important;
        border: 1px solid #704638 !important;
    }
    .stApp .hero h1, .stApp .hero p { color: #ffffff !important; }
    .stApp .hero .eyebrow { color: #ff896b !important; }
    .stApp .card, .stApp div[data-testid="stMetric"],
    .stApp [data-testid="stExpander"] details,
    .stApp [data-testid="stExpander"] summary {
        background: #fffdfa !important;
        color: #202124 !important;
        border-color: #dfd5cc !important;
    }
    .stApp .card *, .stApp .small-muted { color: #30343a !important; }
    .stApp .card b, .stApp .ticket-id { color: #202124 !important; }
    .stApp .ticket {
        background: #fff1eb !important;
        color: #202124 !important;
        border-color: #e97855 !important;
    }
    .stApp .ticket *, .stApp .chip { color: #713323 !important; }
    .stApp .chip { background: #fbe0d5 !important; border: 1px solid #efb19d !important; }
    .stApp input, .stApp textarea,
    .stApp [data-baseweb="input"], .stApp [data-baseweb="textarea"],
    .stApp [data-baseweb="select"] > div {
        background: #fffdfa !important;
        color: #202124 !important;
        border-color: #dfd5cc !important;
    }
    .stApp input::placeholder, .stApp textarea::placeholder { color: #7c858d !important; opacity: 1 !important; }
    .stApp [data-baseweb="select"] *, .stApp [data-baseweb="input"] *,
    .stApp [data-baseweb="textarea"] * { color: #202124 !important; }
    [data-baseweb="popover"], [data-baseweb="menu"] { background: #fffdfa !important; }
    [data-baseweb="popover"] *, [data-baseweb="menu"] * { color: #202124 !important; }
    .stApp [data-testid="stFileUploader"] section { background: #fffdfa !important; border-color: #e97855 !important; }
    .stApp [data-testid="stFileUploader"] section * { color: #30343a !important; }
    .stApp [data-testid="stNumberInput"] button { background: #fbe0d5 !important; color: #713323 !important; }
    .stApp div[data-testid="stMetric"] label,
    .stApp div[data-testid="stMetric"] [data-testid="stMetricValue"],
    .stApp div[data-testid="stMetric"] [data-testid="stMetricDelta"] { color: #202124 !important; }
    .stApp div[data-testid="stMetric"] [data-testid="stMetricValue"] { font-size: 1.45rem !important; }
    .stApp .stButton > button { background: #fffdfa !important; color: #202124 !important; border-color: #dfd5cc !important; }
    .stApp .stButton > button[kind="primary"] { background: #e97855 !important; color: #ffffff !important; border-color: #e97855 !important; }
    </style>""", unsafe_allow_html=True)


# Last-pass contrast rules for Streamlit's generated elements.
if st.session_state["theme"] == "Dark":
    st.markdown("""<style>
    div[data-testid="stAppViewContainer"] div.hero h1,
    div[data-testid="stAppViewContainer"] div.hero p { color: #ffffff !important; }
    div[data-testid="stAppViewContainer"] div.hero .eyebrow { color: #ff896b !important; }
    div[data-testid="stAppViewContainer"] div.card,
    div[data-testid="stAppViewContainer"] div[data-testid="stMetric"],
    div[data-testid="stAppViewContainer"] div[data-testid="stExpander"] {
        background: #24272c !important; color: #f5f1ed !important;
    }
    div[data-testid="stAppViewContainer"] div.card *,
    div[data-testid="stAppViewContainer"] div[data-testid="stMetric"] *,
    div[data-testid="stAppViewContainer"] [data-testid="stWidgetLabel"] p,
    div[data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] p {
        color: #f5f1ed !important;
    }
    div[data-testid="stAppViewContainer"] input,
    div[data-testid="stAppViewContainer"] textarea,
    div[data-testid="stAppViewContainer"] [data-baseweb="select"] > div,
    div[data-testid="stAppViewContainer"] [data-testid="stFileUploader"] section {
        background: #202328 !important; color: #ffffff !important;
    }
    div[data-testid="stAppViewContainer"] input::placeholder,
    div[data-testid="stAppViewContainer"] textarea::placeholder { color: #b8b0aa !important; }
    </style>""", unsafe_allow_html=True)
else:
    st.markdown("""<style>
    div[data-testid="stAppViewContainer"] div.hero h1,
    div[data-testid="stAppViewContainer"] div.hero p { color: #ffffff !important; }
    div[data-testid="stAppViewContainer"] div.hero .eyebrow { color: #ff896b !important; }
    div[data-testid="stAppViewContainer"] div.card,
    div[data-testid="stAppViewContainer"] div[data-testid="stMetric"],
    div[data-testid="stAppViewContainer"] div[data-testid="stExpander"] {
        background: #fffdfa !important; color: #202124 !important;
    }
    div[data-testid="stAppViewContainer"] div.card *,
    div[data-testid="stAppViewContainer"] div[data-testid="stMetric"] *,
    div[data-testid="stAppViewContainer"] [data-testid="stWidgetLabel"] p,
    div[data-testid="stAppViewContainer"] [data-testid="stCaptionContainer"] p {
        color: #202124 !important;
    }
    div[data-testid="stAppViewContainer"] input,
    div[data-testid="stAppViewContainer"] textarea,
    div[data-testid="stAppViewContainer"] [data-baseweb="select"] > div,
    div[data-testid="stAppViewContainer"] [data-testid="stFileUploader"] section {
        background: #fffdfa !important; color: #202124 !important;
    }
    div[data-testid="stAppViewContainer"] input::placeholder,
    div[data-testid="stAppViewContainer"] textarea::placeholder { color: #7c858d !important; }
    </style>""", unsafe_allow_html=True)


def t(language: str, english: str, urdu: str) -> str:
    return urdu if language == "Urdu" else english


def category_name(category: str, language: str) -> str:
    names = {"pothole": ("Pothole", "سڑک کا گڑھا"), "streetlight": ("Streetlight", "سٹریٹ لائٹ"), "garbage": ("Garbage and waste", "کچرا اور فضلہ"), "water_sewer": ("Water or sewerage", "پانی یا نکاسیٔ آب"), "park_public_space": ("Park or public space", "پارک یا عوامی جگہ"), "traffic_safety": ("Traffic safety", "ٹریفک کی حفاظت"), "other": ("Other issue", "دیگر مسئلہ")}
    return names.get(category, names["other"])[1 if language == "Urdu" else 0]


def severity_name(severity: str, language: str) -> str:
    names = {"low": ("Low", "کم"), "medium": ("Medium", "درمیانی"), "high": ("High", "زیادہ"), "critical": ("Critical", "انتہائی اہم")}
    return names.get(severity, names["medium"])[1 if language == "Urdu" else 0]


def department_name(department: str, language: str) -> str:
    names = {
        "Public Works and Roads": "محکمہ تعمیرات اور سڑکیں",
        "Street Lighting and Electrical Services": "محکمہ سٹریٹ لائٹس اور بجلی کی خدمات",
        "Waste Management and Sanitation": "محکمہ صفائی اور فضلہ انتظامیہ",
        "Water Supply and Sewerage": "محکمہ آب رسانی اور نکاسیٔ آب",
        "Parks and Public Spaces": "محکمہ پارکس اور عوامی مقامات",
        "Traffic and Road Safety": "محکمہ ٹریفک اور سڑکوں کی حفاظت",
    }
    return names.get(department, department) if language == "Urdu" else department


def rtl(text: str) -> str:
    return f"<div class='urdu'>{text}</div>"


def has_key() -> bool:
    return bool(os.getenv("GROQ_API_KEY"))


def sla_deadline(row: dict) -> datetime:
    return datetime.fromisoformat(row["created_at"]) + timedelta(hours=row["sla_hours"])


def render_sidebar() -> tuple[str, str]:
    with st.sidebar:
        st.markdown("<div style='font-family:Manrope;font-size:1.45rem;font-weight:800'>CivicLens <span style='color:#e97855'>AI</span></div>", unsafe_allow_html=True)
        st.caption("From public reports to verified action")
        st.divider()
        language = st.selectbox("Language / زبان", ["English", "Urdu"])
        selected_theme = st.selectbox("Appearance / ظاہری انداز", ["Light", "Dark"], index=["Light", "Dark"].index(st.session_state["theme"]))
        if selected_theme != st.session_state["theme"]:
            st.session_state["theme"] = selected_theme
            st.rerun()
        page_labels = ["Report issue", "Track complaints", "Operations dashboard"] if language == "English" else ["مسئلہ رپورٹ کریں", "شکایات دیکھیں", "عملیاتی ڈیش بورڈ"]
        page = st.radio(t(language, "Workspace", "صفحہ منتخب کریں"), page_labels)
        st.divider()
        st.markdown(t(language, "**AI workflow**", "**مصنوعی ذہانت کا طریقۂ کار**"))
        st.caption(t(language, "Image analysis → department routing → priority scoring → resolution verification", "تصویر کا تجزیہ → متعلقہ محکمے کا انتخاب → ترجیح مقرر کرنا → حل کی تصدیق"))
        if not has_key(): st.warning(t(language, "Add GROQ_API_KEY to enable complaint analysis.", "شکایت کے تجزیے کے لیے GROQ_API_KEY شامل کریں۔"))
        st.caption(t(language, "Civic service operations workspace", "شہری خدمات کے انتظام کا مرکز"))
    page_map = dict(zip(page_labels, ["Report issue", "Track complaints", "Operations dashboard"]))
    return page_map[page], language


def header(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(f"<div class='hero'><div class='eyebrow'>{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>", unsafe_allow_html=True)


def report_page(language: str) -> None:
    header("Citizen portal", t(language, "Report a civic issue", "شہری مسئلہ رپورٹ کریں"), t(language, "Turn a photo into a prioritized, department-ready work order.", "اپنی تصویر کو ترجیحی بنیاد پر متعلقہ محکمے کے لیے قابلِ عمل کام میں تبدیل کریں۔"))
    with st.form("report_form"):
        left, right = st.columns([1.1, 1])
        with left:
            image = st.file_uploader(t(language, "Upload evidence photo", "مسئلے کی تصویر اپ لوڈ کریں"), type=["jpg", "jpeg", "png", "webp"])
            if image: st.image(image, caption=t(language, "Evidence preview", "تصویر کا جائزہ"), use_container_width=True)
        with right:
            st.markdown(f"<div class='card'><b>{t(language, 'Location and context', 'مقام اور تفصیل')}</b><br><span class='small-muted'>{t(language, 'Coordinates help us detect duplicate reports and safety-sensitive locations.', 'مقام کے اعداد ہمیں ایک ہی مسئلے کی دوبارہ موصول ہونے والی شکایات اور خطرناک مقامات کی شناخت میں مدد دیتے ہیں۔')}</span></div><br>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            latitude = c1.number_input(t(language, "Latitude", "شمالی عرض البلد"), min_value=-90.0, max_value=90.0, value=24.8607, format="%.6f")
            longitude = c2.number_input(t(language, "Longitude", "مشرقی طول البلد"), min_value=-180.0, max_value=180.0, value=67.0011, format="%.6f")
            description = st.text_area(t(language, "What did you observe?", "آپ نے کیا دیکھا؟"), placeholder=t(language, "Example: The streetlight has been off for three nights near a pedestrian crossing.", "مثال: پیدل چلنے والوں کے راستے کے قریب سٹریٹ لائٹ تین راتوں سے تین راتوں سے بند ہے۔"))
            consent = st.checkbox(t(language, "I confirm this image is safe to use for civic reporting.", "میں تصدیق کرتا ہوں کہ یہ تصویر شہری مسئلے کی رپورٹ کے لیے استعمال کی جا سکتی ہے۔"), value=True)
        submit = st.form_submit_button(t(language, "Analyze and submit complaint", "تجزیہ کرکے شکایت جمع کروائیں"), type="primary", use_container_width=True)
    if not submit: return
    if image is None: st.error(t(language, "Please upload a photo.", "براہ کرم تصویر اپ لوڈ کریں۔")); return
    if not consent: st.error(t(language, "Please confirm the reporting consent.", "براہ کرم شکایت درج کرنے کی رضامندی کی تصدیق کریں۔")); return
    if not has_key(): st.error(t(language, "GROQ_API_KEY is required before submitting a complaint.", "شکایت جمع کروانے سے پہلے GROQ_API_KEY شامل کرنا ضروری ہے۔")); return
    with st.spinner(t(language, "Analyzing evidence, retrieving department policy, and calculating priority...", "تصویر کا تجزیہ اور درست department کی تلاش جاری ہے...")):
        try:
            classification = classify_image(image.getvalue(), image.type, description, language)
            routing = route_issue(classification, description, language)
            stored_name = f"{uuid.uuid4().hex}_{image.name.replace(' ', '_')}"
            image_path = UPLOAD_DIR / stored_name
            image_path.write_bytes(image.getvalue())
            complaint = create_complaint(category=classification["category"], severity=classification["severity"], confidence=classification["confidence"], description=description or classification.get("description", ""), latitude=latitude, longitude=longitude, department=routing["department"], routing_reason=routing["reason"], recommended_action=routing["recommended_action"], image_path=str(image_path.relative_to(BASE_DIR)), provider=f"{classification.get('provider', 'AI')} + {routing.get('provider', 'RAG')}", needs_review=classification.get("needs_review", False))
        except Exception as exc: st.error(f"Submission failed: {exc}"); return
    st.success(t(language, "Complaint submitted and routed successfully.", "شکایت کامیابی سے جمع اور route کر دی گئی ہے۔"))
    st.markdown(f"<div class='ticket'><div class='ticket-id'>{complaint['ticket_id']}</div><div>{t(language, 'Save this ticket ID to track your complaint.', 'اپنی شکایت track کرنے کے لیے یہ ticket ID محفوظ کریں۔')}</div></div>", unsafe_allow_html=True)
    st.write("")
    a, b, c, d = st.columns(4)
    a.metric(t(language, "Category", "قسم"), category_name(complaint["category"], language))
    b.metric(t(language, "Priority", "ترجیح"), f"{complaint['priority_label']} · {complaint['priority_score']}/100")
    c.metric(t(language, "Department", "متعلقہ محکمہ"), department_name(complaint["department"], language))
    d.metric(t(language, "Response target", "جوابی وقت"), f"{complaint['sla_hours']} {t(language, 'hours', 'گھنٹے')}")
    if complaint.get("needs_review"): st.warning(t(language, "Low AI confidence: this case requires human review before field dispatch.", "مصنوعی ذہانت کا اعتماد کم ہے، اس لیے فیلڈ ٹیم کو بھیجنے سے پہلے انسانی جائزہ ضروری ہے۔"))
    if complaint.get("duplicate_matches"): st.warning(f"Potential duplicate detected. This report is near: {', '.join(x['ticket_id'] for x in complaint['duplicate_matches'])}")
    with st.expander(t(language, "See AI evidence and routing explanation", "AI evidence اور routing explanation دیکھیں"), expanded=True):
        st.write(f"**AI confidence:** {complaint['confidence']:.0%}")
        st.write(f"**AI provider:** {complaint.get('provider', 'AI')}")
        if complaint.get("needs_review"): st.write("**Review status:** Human review required")
        st.write(f"**Routing reason:** {complaint['routing_reason']}")
        st.write(f"**Recommended action:** {complaint['recommended_action']}")


def resolution_panel(complaint: dict, language: str) -> None:
    st.subheader(t(language, "Resolution verification", "مسئلہ حل ہونے کی تصدیق"))
    if not has_key(): st.info(t(language, "AI verification is unavailable in demo mode. You can still review the evidence manually.", "نمونہ موڈ میں مصنوعی ذہانت سے تصدیق دستیاب نہیں۔ آپ شواہد کا دستی طور پر جائزہ لے سکتے ہیں۔")); return
    after = st.file_uploader(t(language, "Upload an after-repair photo", "مرمت کے بعد کی تصویر اپ لوڈ کریں"), type=["jpg", "jpeg", "png", "webp"], key=f"after_{complaint['ticket_id']}")
    if after and st.button(t(language, "Verify resolution", "حل کی تصدیق کریں"), key=f"verify_{complaint['ticket_id']}"):
        before_path = BASE_DIR / complaint["image_path"]
        if not before_path.exists(): st.error("Original evidence image is unavailable."); return
        with st.spinner(t(language, "Comparing before and after evidence...", "مرمت سے پہلے اور بعد کے شواہد کا موازنہ کیا جا رہا ہے۔۔۔")):
            result = verify_resolution(before_path.read_bytes(), after.getvalue(), after.type, language)
            stored = UPLOAD_DIR / f"resolution_{uuid.uuid4().hex}_{after.name.replace(' ', '_')}"
            stored.write_bytes(after.getvalue())
            save_resolution(complaint["ticket_id"], str(stored.relative_to(BASE_DIR)), result["confidence"])
        if result["resolved"]: st.success(t(language, f"The issue appears resolved · AI confidence {result['confidence']:.0%}", f"مسئلہ حل ہوتا ہوا نظر آ رہا ہے · مصنوعی ذہانت کا اعتماد {result['confidence']:.0%}"))
        else: st.warning(t(language, f"Resolution could not be verified · AI confidence {result['confidence']:.0%}", f"مسئلہ حل ہونے کی تصدیق نہیں ہو سکی · مصنوعی ذہانت کا اعتماد {result['confidence']:.0%}"))
        st.write(result.get("citizen_summary") or result.get("explanation", ""))


def complaint_details(complaint: dict, language: str) -> None:
    st.markdown(f"<div class='ticket'><div class='ticket-id'>{complaint['ticket_id']}</div><span class='chip'>{complaint['status']}</span><span class='chip'>{complaint['priority_label']} priority</span><span class='chip'>{complaint['department']}</span></div>", unsafe_allow_html=True)
    st.write("")
    left, right = st.columns([1, 1.25])
    with left:
        path = BASE_DIR / complaint["image_path"] if complaint.get("image_path") else None
        if path and path.exists(): st.image(str(path), caption=t(language, "Original evidence", "اصل تصویری ثبوت"), use_container_width=True)
        resolution = BASE_DIR / complaint["resolution_image_path"] if complaint.get("resolution_image_path") else None
        if resolution and resolution.exists(): st.image(str(resolution), caption=t(language, "Resolution evidence", "حل ہونے کا تصویری ثبوت"), use_container_width=True)
    with right:
        st.write(f"**{t(language, 'Category', 'قسم')}:** {category_name(complaint['category'], language)}")
        st.write(f"**{t(language, 'Severity', 'شدت')}:** {severity_name(complaint['severity'], language)} · **{t(language, 'AI confidence', 'مصنوعی ذہانت کا اعتماد')}:** {complaint['confidence']:.0%}")
        st.write(f"**{t(language, 'Priority', 'ترجیح')}:** {complaint['priority_score']}/100 ({complaint['priority_label']})")
        st.write(f"**{t(language, 'Location', 'مقام')}:** {complaint['latitude']:.6f}, {complaint['longitude']:.6f}")
        deadline = sla_deadline(complaint); remaining = deadline - datetime.now(timezone.utc)
        st.write(f"**{t(language, 'SLA deadline', 'مقررہ وقت کی آخری حد')}:** {deadline.strftime('%Y-%m-%d %H:%M UTC')} · {'Overdue' if remaining.total_seconds() < 0 else str(remaining).split('.')[0] + ' remaining'}")
        st.write(f"**{t(language, 'Description', 'تفصیل')}:** {complaint['description'] or t(language, 'No additional description.', 'مزید تفصیل درج نہیں کی گئی۔')}")
        st.write(f"**{t(language, 'Routing reason', 'محکمے کے انتخاب کی وجہ')}:** {complaint['routing_reason']}")
        st.write(f"**{t(language, 'Recommended action', 'تجویز کردہ کارروائی')}:** {complaint['recommended_action']}")
        new_status = st.selectbox(t(language, "Update status", "حالت تبدیل کریں"), STATUS_OPTIONS, index=STATUS_OPTIONS.index(complaint["status"]), key=f"select_{complaint['ticket_id']}")
        note = st.text_input(t(language, "Update note", "تبدیلی کی وجہ یا نوٹ"), key=f"note_{complaint['ticket_id']}")
        if st.button("Save status", key=f"save_{complaint['ticket_id']}"):
            update_status(complaint["ticket_id"], new_status, note); st.success(t(language, "Status updated.", "شکایت کی حالت تبدیل کر دی گئی ہے۔")); st.rerun()
        if complaint["status"] in {"Resolved", "In Progress"}:
            feedback_options = ["Resolved", "Partially resolved", "Not resolved"] if language == "English" else ["مسئلہ حل ہو گیا", "جزوی طور پر حل ہوا", "مسئلہ حل نہیں ہوا"]
            feedback = st.radio(t(language, "Citizen confirmation", "شہری کی تصدیق"), feedback_options, horizontal=True, key=f"feedback_{complaint['ticket_id']}")
            feedback_value = dict(zip(feedback_options, ["Resolved", "Partially resolved", "Not resolved"]))[feedback]
            if st.button(t(language, "Submit citizen feedback", "شہری کی رائے جمع کروائیں"), key=f"feedback_btn_{complaint['ticket_id']}"):
                save_feedback(complaint["ticket_id"], feedback_value); st.success(t(language, "Feedback recorded.", "آپ کی رائے محفوظ کر لی گئی ہے۔")); st.rerun()
    with st.expander("Complaint timeline", expanded=True):
        for event in get_events(complaint["ticket_id"]): st.write(f"**{event['created_at'].replace('T', ' ')}** — {event['event']} {('· ' + event['note']) if event['note'] else ''}")
    resolution_panel(complaint, language)


def track_page(language: str) -> None:
    header("Case management", t(language, "Track complaints", "شکایات دیکھیں"), t(language, "Follow every case from submission to verified resolution.", "ہر شکایت کی پیش رفت جمع کروانے سے لے کر حل ہونے کی تصدیق تک دیکھیں۔"))
    rows = get_complaints()
    if not rows: st.info(t(language, "No complaints submitted yet.", "ابھی تک کوئی شکایت جمع نہیں ہوئی۔")); return
    selected = st.selectbox(t(language, "Select ticket", "شکایت کا شناختی نمبر منتخب کریں"), [r["ticket_id"] for r in rows])
    complaint_details(get_complaint(selected), language)


def dashboard_page(language: str) -> None:
    header("Municipal operations", t(language, "Operations dashboard", "عملیاتی ڈیش بورڈ"), t(language, "Prioritize field work, monitor SLAs, and measure public-service performance.", "میدانی کام کو ترجیح دیں، مقررہ جوابی اوقات کی نگرانی کریں اور عوامی خدمت کی کارکردگی ناپیں۔"))
    rows = get_complaints()
    if not rows: st.info(t(language, "Submit a complaint to populate the dashboard.", "ڈیش بورڈ پر معلومات دیکھنے کے لیے پہلے ایک شکایت جمع کروائیں۔")); return
    df = pd.DataFrame(rows)
    overdue = sum(sla_deadline(r) < datetime.now(timezone.utc) and r["status"] != "Resolved" for r in rows)
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total", len(df)); c2.metric("Open", int((df.status != "Resolved").sum())); c3.metric("High / critical", int(df.severity.isin(["high", "critical"]).sum())); c4.metric("Overdue", overdue); c5.metric("Resolved", int((df.status == "Resolved").sum()))
    left, right = st.columns(2)
    with left:
        st.subheader(t(language, "Issue categories", "مسائل کی اقسام"))
        chart_data = df["category"].value_counts().rename_axis("category").reset_index(name="reports")
        chart_data["label"] = chart_data["category"].map(lambda value: category_name(value, language))
        chart = alt.Chart(chart_data).mark_bar(color="#e97855", cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(x=alt.X("label:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-25)), y=alt.Y("reports:Q", title=t(language, "Reports", "شکایات")), tooltip=[alt.Tooltip("label:N", title=t(language, "Category", "قسم")), alt.Tooltip("reports:Q", title=t(language, "Reports", "شکایات"))]).properties(height=280)
        st.altair_chart(chart, use_container_width=True)
    with right:
        st.subheader(t(language, "Department workload", "محکموں کا کام"))
        department_data = df["department"].value_counts().rename_axis("department").reset_index(name="reports")
        department_data["label"] = department_data["department"].map(lambda value: department_name(value, language))
        chart = alt.Chart(department_data).mark_bar(color="#30343a", cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(x=alt.X("label:N", sort="-y", title=None, axis=alt.Axis(labelAngle=-25)), y=alt.Y("reports:Q", title=t(language, "Reports", "شکایات")), tooltip=[alt.Tooltip("label:N", title=t(language, "Department", "محکمہ")), alt.Tooltip("reports:Q", title=t(language, "Reports", "شکایات"))]).properties(height=280)
        st.altair_chart(chart, use_container_width=True)
    st.subheader(t(language, "Civic issue map", "شہری مسائل کا نقشہ"))
    st.map(df.rename(columns={"latitude": "lat", "longitude": "lon"})[["lat", "lon"]])
    st.subheader(t(language, "Priority queue", "ترجیحی فہرست"))
    view = df.copy(); view["category"] = view["category"].str.replace("_", " ").str.title()
    st.dataframe(view.sort_values(["priority_score", "created_at"], ascending=[False, False])[["ticket_id", "category", "severity", "priority_score", "department", "status", "sla_hours", "created_at"]], use_container_width=True, hide_index=True)
    st.caption("Dispatch the highest-risk, oldest, or SLA-breaching cases first.")


page, language = render_sidebar()
if page == "Report issue": report_page(language)
elif page == "Track complaints": track_page(language)
else: dashboard_page(language)
