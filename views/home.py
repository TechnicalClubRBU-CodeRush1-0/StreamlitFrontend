import streamlit as st
from data.sector_beta_map import SECTOR_BETA

def render():
    st.markdown("""
    <style>
    :root {
      --gradient: linear-gradient(135deg,#6366f1,#8b5cf6);
      --bg-surface:#1b2331;
      --bg-alt:#202a3b;
      --border:#2a3342;
      --text-dim:#9ca3af;
    }
    .big-title {
      font-size:2.3rem;
      font-weight:700;
      background:var(--gradient);
      -webkit-background-clip:text;
      color:transparent;
      margin:0 0 .35rem 0;
      letter-spacing:.5px;
    }
    .lead {
      font-size:1.02rem;
      color:var(--text-dim);
      margin-bottom:1rem;
      max-width:880px;
      line-height:1.35;
    }
    .panel {
      background:var(--bg-surface);
      border:1px solid var(--border);
      padding:1rem 1.1rem 1.05rem 1.1rem;
      border-radius:16px;
      margin-bottom:1.05rem;
    }
    .feature-tag {
      display:inline-block;
      padding:.45rem .7rem;
      font-size:.65rem;
      font-weight:600;
      letter-spacing:.55px;
      border-radius:6px;
      border:1px solid var(--border);
      background:var(--bg-alt);
      margin:.25rem .4rem .25rem 0;
      text-transform:uppercase;
      color:var(--text-dim);
    }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="big-title">AI Stock Risk & VaR Suite</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="lead">Automated multi-factor stock risk scoring, portfolio aggregation, and historical VaR / CVaR for Indian equities — with zero manual metric entry.</div>',
        unsafe_allow_html=True
    )
    st.markdown("""
    <div class="panel">
      <h4 style="margin-top:0; font-size:1.05rem;">Key Features</h4>
      <div>
        <span class="feature-tag">Auto Factor Fetch</span>
        <span class="feature-tag">Risk Score</span>
        <span class="feature-tag">Macro Vol Integration</span>
        <span class="feature-tag">Portfolio Mode</span>
        <span class="feature-tag">VaR / CVaR</span>
        <span class="feature-tag">Confidence Heuristics</span>
        <span class="feature-tag">PDF Reports</span>
        <span class="feature-tag">Combined Reports</span>
      </div>
      <p style="font-size:.8rem; margin:.6rem 0 0; color:var(--text-dim);">
        Data via Yahoo Finance (yfinance). Factors: Debt/Equity, Earnings Volatility, Sector & Macro risk, return distribution.
      </p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("Sectors Covered")
    cols = st.columns(4)
    for i, sector in enumerate(SECTOR_BETA.keys()):
        with cols[i % 4]:
            st.write(f"- {sector}")

    with st.expander("Usage Tips", expanded=True):
        st.markdown("""
        - Start with Assessment (single company).
        - Use Portfolio for allocation + diversification view.
        - Combine reports with 'Combined PDF' after both analyses.
        - Historical VaR/CVaR ≠ future guarantee; use judgment.
        """)

    st.info("Go to 'Assessment' or 'Portfolio' to begin.")
    st.caption("Disclaimer: Educational purposes only. Not investment advice.")