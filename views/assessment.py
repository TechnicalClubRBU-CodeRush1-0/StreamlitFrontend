# (Assessment view)
import streamlit as st
import numpy as np
from data.sector_beta_map import SECTOR_BETA
from services.finance_fetchers import FinanceDataFetcher, get_index_returns
from models.risk_model import StockInvestmentModel
from models.var import VaRCalculator
from utils.formatting import fmt_currency, fmt_pct
from utils.report import generate_assessment_pdf, generate_combined_pdf

SECTOR_RISK_MAP = {
    'Metal':'high','Automotive':'medium_high','Financial Services':'medium_high',
    'Energy':'medium','Technology':'medium','Consumers':'low','FMCG':'low','Pharma':'medium'
}

def normalize_sector_label(label: str):
    if label in ('medium_high','medium'): return 'medium'
    return label if label in ('low','medium','high') else 'medium'

def compute_macro_risk(index_returns):
    if index_returns is None or index_returns.empty: return 0.5
    window = index_returns.tail(60)
    if window.empty: return 0.5
    rv = window.std()
    pts=[(0.01,0.1),(0.02,0.5),(0.035,1.0)]
    if rv <= pts[0][0]: r=pts[0][1]
    elif rv >= pts[-1][0]: r=pts[-1][1]
    else:
        for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
            if x1<=rv<=x2:
                t=(rv-x1)/(x2-x1); r=y1+t*(y2-y1); break
    return float(np.clip(r,0,1))

def derive_confidence(earn_vol,de_ratio,earn_q,index_returns,returns):
    target=8
    coverage=min(earn_q/target,1.0) if earn_q else 0.4
    if de_ratio is None: structure=0.4
    else:
        if de_ratio<=0: structure=0.5
        elif de_ratio<1.5: structure=0.9
        elif de_ratio<3: structure=0.7
        else: structure=0.5
    if returns is None or returns.empty or index_returns is None or index_returns.empty:
        vol_score=0.6
    else:
        sv=returns.tail(60).std(); iv=index_returns.tail(60).std()
        rel=1 if iv==0 or np.isnan(iv) else sv/iv
        if rel<0.8: vol_score=0.85
        elif rel<1.5: vol_score=0.9
        elif rel<2.0: vol_score=0.75
        else: vol_score=0.6
    return (coverage+structure+vol_score)/3

def risk_bar(score):
    pct=f"{score*100:.1f}%"; w=f"{score*100:.1f}%"
    return f"""
    <div style="background:#141b25;border:1px solid #253041;height:18px;width:100%;border-radius:10px;overflow:hidden;position:relative;margin-top:.45rem;">
      <div style="height:100%;background:linear-gradient(90deg,#10b981,#f59e0b,#ef4444);width:{w};transition:width .65s;"></div>
      <div style="position:absolute;top:-5px;width:2px;height:28px;background:#fff;left:{w};box-shadow:0 0 5px rgba(255,255,255,0.85);"></div>
    </div>
    <div style="font-size:.55rem;letter-spacing:.4px;margin-top:3px;color:#9ca3af;">0% LOW — {pct} — 100% HIGH</div>
    """

def action_badge(action):
    a=action.lower()
    if 'buy' in a: style="background:rgba(16,185,129,.12);color:#10b981;"
    elif 'hold' in a: style="background:rgba(245,158,11,.15);color:#f59e0b;"
    else: style="background:rgba(239,68,68,.15);color:#ef4444;"
    return f'<span style="display:inline-block;padding:.3rem .7rem;border-radius:999px;font-size:.6rem;font-weight:600;letter-spacing:.5px;text-transform:uppercase;{style}">{action}</span>'

def render():
    # Minimal CSS (cards)
    st.markdown("""
    <style>
    .metric-grid {display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));margin-top:.25rem;}
    .card{background:#1b2331;border:1px solid #2a3342;padding:.75rem .85rem .8rem;border-radius:14px;}
    .card h5{margin:0 0 .4rem 0;font-size:.65rem;letter-spacing:.55px;font-weight:600;text-transform:uppercase;color:#9ca3af;}
    .card-value{margin:0;font-size:1.15rem;font-weight:600;color:#f5f6f8;line-height:1.1;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### Single Stock Assessment")
    with st.expander("What Does This Do?", expanded=True):
        st.write("Fetches factors automatically, scores risk, suggests an action, computes VaR/CVaR, and enables PDF export.")

    c1,c2,c3 = st.columns([1.4,1,1])
    with c1:
        sector = st.selectbox("Sector", list(SECTOR_BETA.keys()))
    with c2:
        company = st.selectbox("Company", list(SECTOR_BETA[sector]['companies'].keys()))
    with c3:
        investment_amount = st.number_input("Investment (INR)", min_value=1000, value=25000, step=500)
    ticker = SECTOR_BETA[sector]['companies'][company]

    run = st.button("Run Assessment", type="primary", use_container_width=True)
    st.markdown("---")
    if not run:
        return

    with st.spinner(f"Gathering data for {company} ({ticker}) ..."):
        de_ratio, de_err = FinanceDataFetcher.debt_to_equity(ticker)
        earn_vol, ev_err, earn_q, earnings_raw = FinanceDataFetcher.earnings_volatility_extended(ticker)
        returns, ret_err = FinanceDataFetcher.historical_returns(ticker, period="1y")
        idx_returns, idx_err = get_index_returns("^NSEI", period="1y")

    errs=[e for e in [de_err,ev_err,ret_err,idx_err] if e]
    if errs:
        with st.expander("Data Notices", expanded=False):
            for e in errs: st.warning(e)

    if de_ratio is None or earn_vol is None or returns is None:
        st.error("Critical data missing — cannot compute.")
        return

    sector_r=normalize_sector_label(SECTOR_RISK_MAP.get(sector,'medium'))
    macro_r=compute_macro_risk(idx_returns)
    sentiment_score=0.0
    sentiment_conf=0.2
    risk_data_conf=derive_confidence(earn_vol,de_ratio,earn_q,idx_returns,returns)

    model=StockInvestmentModel()
    var_calc=VaRCalculator(returns)
    var95=var_calc.calculate_var(0.95)
    cvar95=var_calc.calculate_cvar(0.95)
    beta=SECTOR_BETA[sector]['beta']

    res=model.full_assessment(
        sentiment_score=sentiment_score,
        de_ratio=de_ratio,
        beta=beta,
        earnings_volatility=earn_vol,
        sector_risk=sector_r,
        macro_risk=macro_r,
        sentiment_confidence=sentiment_conf,
        risk_data_confidence=risk_data_conf
    )

    st.markdown("#### Summary")
    cols=st.columns(4)
    items=[
        ("Risk Score",f"{res['risk_score']:.2f}"),
        ("Risk Level",res['risk_level']),
        ("Confidence",f"{res['confidence_percent']:.0f}%"),
        ("Action",action_badge(res['recommended_action']))
    ]
    for c,(k,v) in zip(cols,items):
        c.markdown(f'<div class="card"><h5>{k}</h5><p class="card-value">{v}</p></div>', unsafe_allow_html=True)

    st.markdown(f'<div class="card"><h5>Risk Distribution</h5>{risk_bar(res["risk_score"])}</div>', unsafe_allow_html=True)

    st.markdown("#### Factors")
    f_items=[
        ("D/E Ratio",f"{de_ratio:.2f}"),
        ("Earnings Vol",f"{earn_vol:.2f}"),
        ("Sector Beta",f"{beta:.2f}"),
        ("Sector Risk",sector_r.title()),
        ("Macro Risk",f"{macro_r:.2f}")
    ]
    st.markdown('<div class="metric-grid">'+"".join(
        f'<div class="card"><h5>{k}</h5><p class="card-value">{v}</p></div>' for k,v in f_items
    )+'</div>', unsafe_allow_html=True)

    st.markdown("#### Statistical Loss (1-Day, 95%)")
    var_amt=var95*investment_amount
    cvar_amt=cvar95*investment_amount
    loss=[
        ("Investment",fmt_currency(investment_amount)),
        ("VaR 95%",f"{fmt_currency(var_amt)} ({fmt_pct(var95)})"),
        ("CVaR 95%",f"{fmt_currency(cvar_amt)} ({fmt_pct(cvar95)})")
    ]
    st.markdown('<div class="metric-grid">'+"".join(
        f'<div class="card"><h5>{k}</h5><p class="card-value">{v}</p></div>' for k,v in loss
    )+'</div>', unsafe_allow_html=True)

    with st.expander("Interpretation"):
        st.write("VaR = threshold loss; CVaR = mean loss beyond that. Historical only; no scenario simulation.")
    with st.expander("Recent Return Series (120 Days)"):
        st.line_chart(returns.tail(120))
    with st.expander("Quarterly Net Income (raw)"):
        if earnings_raw is not None:
            df = earnings_raw[['Net Income']] if 'Net Income' in earnings_raw.columns else earnings_raw
            st.dataframe(df)
        else:
            st.write("Not Available")

    assessment_data={
        "ticker":ticker,"company":company,"sector":sector,
        "investment_amount":investment_amount,"risk_score":res["risk_score"],
        "risk_level":res["risk_level"],"confidence_percent":res["confidence_percent"],
        "action":res["recommended_action"],"de_ratio":de_ratio,"earnings_vol":earn_vol,
        "sector_beta":beta,"sector_risk":sector_r,"macro_risk":macro_r,
        "var_pct":var95,"var_amount":var_amt,"cvar_pct":cvar95,"cvar_amount":cvar_amt,
        "cl_label":"95% Confidence"
    }
    st.session_state["latest_assessment_report"]=assessment_data

    d1,d2,d3,d4=st.columns(4)
    with d1:
        st.download_button("Returns CSV", data=returns.to_csv().encode(),
                           file_name=f"{ticker}_returns_1y.csv", mime="text/csv")
    from utils.report import generate_assessment_pdf, generate_combined_pdf
    with d2:
        st.download_button("Assessment PDF",
                           data=generate_assessment_pdf(assessment_data),
                           file_name=f"assessment_{ticker}.pdf",
                           mime="application/pdf")
    with d3:
        if "latest_portfolio_report" in st.session_state:
            st.download_button("Combined PDF",
                               data=generate_combined_pdf(
                                   assessment=st.session_state.get("latest_assessment_report"),
                                   portfolio=st.session_state.get("latest_portfolio_report"),
                                   allocation_chart=st.session_state.get("latest_portfolio_allocation_chart")
                               ),
                               file_name="combined_report.pdf",
                               mime="application/pdf")
        else:
            st.button("Combined PDF (needs portfolio)", disabled=True)
    with d4:
        st.write("")

    st.success("Assessment complete. Data cached for combined report.")