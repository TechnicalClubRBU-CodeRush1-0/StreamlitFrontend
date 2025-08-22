import streamlit as st

NAV_ITEMS = [
    ("home", "Home"),
    ("assessment", "Assessment"),
    ("portfolio", "Portfolio"),
    ("risk-metrics", "Risk Metrics"),
    ("about", "About")
]

def render_navbar(current: str):
    st.markdown("""
    <style>
    .nav-bar {
      position: sticky;
      top: 0;
      z-index: 100;
      backdrop-filter: blur(10px);
      background: rgba(17,24,40,0.80);
      border:1px solid #2a3342;
      padding:.55rem .75rem;
      border-radius:14px;
      display:flex;
      flex-wrap:wrap;
      gap:.55rem;
      margin-bottom:1.05rem;
    }
    .nav-link {
      padding:.55rem .95rem;
      border-radius:10px;
      background:#1d2533;
      color:#f5f6f8 !important;
      font-size:.80rem;
      font-weight:600;
      letter-spacing:.35px;
      text-decoration:none;
      border:1px solid #2d3746;
      transition:background .25s,border .25s, transform .25s;
    }
    .nav-link:hover {
      background:#2a3140;
      transform:translateY(-2px);
    }
    .nav-active {
      background:linear-gradient(135deg,#6366f1,#8b5cf6);
      border:1px solid #6366f1;
      box-shadow:0 4px 14px -4px rgba(99,102,241,.55);
    }
    @media (max-width:780px){
      .nav-link { font-size:.72rem; padding:.5rem .75rem; }
    }
    </style>
    """, unsafe_allow_html=True)
    html = '<div class="nav-bar">'
    for slug, label in NAV_ITEMS:
        active = "nav-active" if slug == current else ""
        html += f'<a class="nav-link {active}" href="?page={slug}">{label}</a>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)