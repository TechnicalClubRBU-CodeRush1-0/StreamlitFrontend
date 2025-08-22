import streamlit as st
import numpy as np
import pandas as pd
from services.finance_fetchers import FinanceDataFetcher
from models.var import VaRCalculator
from utils.formatting import fmt_currency, fmt_pct

def _css():
    st.markdown("""
    <style>
    .inline-cards {
        display:grid;
        gap:14px;
        grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
        margin-top:.75rem;
    }
    .metric-box {
        background:#1b2331;
        border:1px solid #2a3342;
        padding:.75rem .85rem;
        border-radius:14px;
    }
    .metric-box h6 {
        margin:0 0 .4rem 0;
        font-size:.6rem;
        text-transform:uppercase;
        letter-spacing:.55px;
        color:#9ca3af;
    }
    .metric-box p {
        margin:0;
        font-size:1.05rem;
        font-weight:600;
    }
    .hr-thin {
        border:none;
        border-top:1px solid #2a3342;
        margin:1.1rem 0 .9rem;
    }
    </style>
    """, unsafe_allow_html=True)

def _multi_conf_table(returns: pd.Series, confidences, invest: float):
    calc = VaRCalculator(returns)
    rows=[]
    for cl in confidences:
        v=calc.calculate_var(cl)
        cv=calc.calculate_cvar(cl)
        rows.append({
            "Confidence": f"{int(cl*100)}%",
            "VaR %": fmt_pct(v),
            "VaR Amount": fmt_currency(v*invest),
            "CVaR %": fmt_pct(cv),
            "CVaR Amount": fmt_currency(cv*invest)
        })
    return pd.DataFrame(rows)

def render():
    _css()
    st.markdown("### VaR & CVaR Explorer")
    with st.expander("What This Does", expanded=True):
        st.write("Downloads historical prices, computes daily returns, then empirical Historical VaR & CVaR. Optionally shows multiple confidence levels and descriptive stats.")

    row1 = st.columns([1.2,1,1])
    with row1[0]:
        ticker = st.text_input("Ticker (Yahoo Finance)", value="TCS.NS")
    with row1[1]:
        period = st.selectbox("Lookback Window", ["3mo","6mo","1y","2y","5y"], index=2)
    with row1[2]:
        primary_cl = st.slider("Primary Confidence", 0.80,0.99,0.95,0.01)

    row2 = st.columns([1,1,1,1])
    with row2[0]:
        investment_amount = st.number_input("Hypothetical Investment (INR)", min_value=1000, value=100000, step=5000)
    with row2[1]:
        show_multi = st.checkbox("Multi-Confidence Table", value=True)
    with row2[2]:
        show_annual = st.checkbox("Annualized (sqrt 252)", value=True)
    with row2[3]:
        recent_window = st.number_input("Recent Dist. Window", min_value=60, max_value=500, value=120)

    run = st.button("Compute", type="primary", use_container_width=True)
    st.markdown("<hr class='hr-thin' />", unsafe_allow_html=True)
    if not run:
        st.info("Set parameters then click Compute.")
        return

    with st.spinner(f"Fetching {period} data for {ticker} ..."):
        returns, err = FinanceDataFetcher.historical_returns(ticker, period=period)
    if err or returns is None or returns.empty:
        st.error(err or "No return data.")
        return

    calc = VaRCalculator(returns)
    var = calc.calculate_var(primary_cl)
    cvar = calc.calculate_cvar(primary_cl)
    var_amt = var * investment_amount
    cvar_amt = cvar * investment_amount
    ann_var = var * np.sqrt(252) if show_annual else None
    ann_cvar = cvar * np.sqrt(252) if show_annual else None

    st.markdown("#### Key Metrics")
    cards = [
        (f"VaR {int(primary_cl*100)}%", f"{fmt_currency(var_amt)} / {fmt_pct(var)}"),
        ("CVaR", f"{fmt_currency(cvar_amt)} / {fmt_pct(cvar)}"),
        ("Tail Prob", fmt_pct(1-primary_cl))
    ]
    if show_annual:
        cards.append(("Ann. VaR (approx)", fmt_pct(ann_var)))
        cards.append(("Ann. CVaR (approx)", fmt_pct(ann_cvar)))

    st.markdown(
        '<div class="inline-cards">' +
        "".join(f'<div class="metric-box"><h6>{k}</h6><p>{v}</p></div>' for k,v in cards) +
        '</div>', unsafe_allow_html=True
    )

    if show_multi:
        st.markdown("##### Multi-Confidence VaR / CVaR")
        confs = sorted(set([primary_cl,0.80,0.90,0.95,0.975,0.99]))
        multi_df = _multi_conf_table(returns, confs, investment_amount)
        st.dataframe(multi_df, use_container_width=True)
    else:
        multi_df = None

    st.markdown("#### Recent Return Distribution")
    st.bar_chart(pd.DataFrame({"returns": returns.tail(recent_window)}))

    with st.expander("Full Return Series"):
        st.line_chart(returns)

    with st.expander("Descriptive Statistics"):
        desc = returns.describe()
        st.write(desc)
        st.write(f"Skewness: {returns.skew():.4f}")
        st.write(f"Kurtosis: {returns.kurtosis():.4f}")

    with st.expander("Download Data"):
        st.download_button("Returns CSV",
                           data=returns.to_csv().encode(),
                           file_name=f"{ticker}_returns_{period}.csv",
                           mime="text/csv")
        if multi_df is not None:
            st.download_button("Multi-Confidence VaR Table CSV",
                               data=multi_df.to_csv(index=False).encode(),
                               file_name=f"{ticker}_multi_conf_var.csv",
                               mime="text/csv")

    with st.expander("Methodology Notes"):
        st.write("""
        - Returns: Daily percent change of close prices (Yahoo Finance).
        - VaR: Historical percentile at α = 1 - confidence.
        - CVaR: Mean of losses beyond VaR threshold.
        - Annualization: sqrt(252) scaling (heuristic; ignores volatility clustering).
        - Limitations: No forward simulation, no regime detection, no intraday data.
        """)

    st.success("Computation complete.")