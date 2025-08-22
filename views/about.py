import streamlit as st

def render():
    st.markdown("### About & Methodology")
    st.markdown("---")
    st.markdown("""
**Automated Factors**  
Debt/Equity, Earnings Volatility, Sector Risk, Macro Risk (60d vol normalization), Sector Beta (static), Historical VaR/CVaR, Confidence composite.

**Risk Score** Weighted sum of normalized factors (heuristic thresholds).  
**Portfolio Mode** Aggregates returns, computes VaR/CVaR, variance contributions, allocation chart, PDF.  
**Combined PDF** Merges latest assessment + portfolio.

**Limitations** Historical-only; no scenario / Monte Carlo / EVT; no sentiment integration yet; heuristic normalization.

**Roadmap Ideas** NLP sentiment, parametric & Cornish-Fisher VaR, Monte Carlo, multi-factor regressions, optimization, stress testing.

**Disclaimer** Educational only. Not investment advice.
""")
    st.caption("© 2025 AI Stock Risk & VaR Suite")