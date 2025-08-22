import streamlit as st
from components.navbar import render_navbar
from views import home, assessment, portfolio, risk_metrics, about

# Single place for page config
st.set_page_config(page_title="AI Stock Risk & VaR Suite", layout="wide")

# Hide any default sidebar nav (defensive)
st.markdown("<style>section[data-testid='stSidebarNav']{display:none !important;}</style>", unsafe_allow_html=True)

# Map URL ?page=slug to view renderers
ROUTES = {
    "home": home.render,
    "assessment": assessment.render,
    "portfolio": portfolio.render,
    "risk-metrics": risk_metrics.render,
    "about": about.render
}

page = st.query_params.get("page", "home")
if page not in ROUTES:
    page = "home"

render_navbar(current=page)
ROUTES[page]()  # Render selected view