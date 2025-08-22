# (Portfolio view)
import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO

from data.sector_beta_map import SECTOR_BETA
from services.finance_fetchers import FinanceDataFetcher, get_index_returns
from models.risk_model import StockInvestmentModel
from models.var import VaRCalculator
from utils.formatting import fmt_pct
from utils.report import generate_portfolio_pdf, generate_combined_pdf

SECTOR_RISK_MAP = {
    'Metal':'high','Automotive':'medium_high','Financial Services':'medium_high',
    'Energy':'medium','Technology':'medium','Consumers':'low','FMCG':'low','Pharma':'medium'
}

def normalize_sector_label(label: str):
    if label in ('medium_high','medium'): return 'medium'
    return label if label in ('low','medium','high') else 'medium'

def compute_macro_risk(idx_returns):
    if idx_returns is None or idx_returns.empty: return 0.5
    w=idx_returns.tail(60)
    if w.empty: return 0.5
    rv=w.std()
    pts=[(0.01,0.1),(0.02,0.5),(0.035,1.0)]
    if rv <= pts[0][0]: r=pts[0][1]
    elif rv >= pts[-1][0]: r=pts[-1][1]
    else:
        for (x1,y1),(x2,y2) in zip(pts,pts[1:]):
            if x1<=rv<=x2:
                t=(rv-x1)/(x2-x1); r=y1+t*(y2-y1); break
    return float(np.clip(r,0,1))

def derive_confidence(earn_vol,de_ratio,earn_q,idx_returns,rets):
    target=8
    coverage=min(earn_q/target,1.0) if earn_q else 0.4
    if de_ratio is None: structure=0.4
    else:
        if de_ratio<=0: structure=0.5
        elif de_ratio<1.5: structure=0.9
        elif de_ratio<3: structure=0.7
        else: structure=0.5
    if rets is None or rets.empty or idx_returns is None or idx_returns.empty:
        vol=0.6
    else:
        sv=rets.tail(60).std(); iv=idx_returns.tail(60).std()
        rel=1 if iv==0 or np.isnan(iv) else sv/iv
        if rel<0.8: vol=0.85
        elif rel<1.5: vol=0.9
        elif rel<2.0: vol=0.75
        else: vol=0.6
    return (coverage+structure+vol)/3

def render():
    st.markdown("""
    <style>
    .inline-cards {display:grid;gap:14px;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));margin-top:.65rem;}
    .metric-box {background:#1b2331;border:1px solid #2a3342;padding:.75rem .85rem;border-radius:14px;}
    .metric-box h6 {margin:0 0 .45rem 0;font-size:.6rem;text-transform:uppercase;letter-spacing:.55px;color:#9ca3af;}
    .metric-box p {margin:0;font-size:1.05rem;font-weight:600;}
    </style>
    """, unsafe_allow_html=True)

    st.markdown("### Portfolio Mode")
    with st.expander("What This Does", expanded=True):
        st.write("Aggregate stock factors & returns, compute portfolio VaR/CVaR, variance contributions, allocation pie chart, and export PDFs.")

    default_rows = [
        {"Ticker":"TCS.NS","Weight":0.4},
        {"Ticker":"HDFCBANK.NS","Weight":0.3},
        {"Ticker":"TATAMOTORS.NS","Weight":0.3}
    ]
    pf_df = st.data_editor(pd.DataFrame(default_rows), num_rows="dynamic", use_container_width=True, key="pf_edit")

    c1,c2 = st.columns(2)
    lookback = c1.selectbox("Lookback", ["6mo","1y","2y"], index=1)
    confidence = c2.slider("Confidence (VaR/CVaR)", 0.80,0.99,0.95,0.01)

    run = st.button("Analyze Portfolio", type="primary", use_container_width=True)
    st.markdown("---")
    if not run: return

    if pf_df.empty or "Ticker" not in pf_df or "Weight" not in pf_df:
        st.error("Please supply tickers and weights."); return
    pf_df["Ticker"]=pf_df["Ticker"].astype(str).str.strip().str.upper()
    pf_df=pf_df[pf_df["Ticker"]!=""].dropna(subset=["Weight"])
    if pf_df.empty: st.error("No valid tickers."); return
    weights=pf_df["Weight"].clip(lower=0).astype(float)
    if weights.sum()==0: st.error("All weights are zero."); return
    pf_df["NormWeight"]=weights/weights.sum()

    ticker_info={}
    for sec, meta in SECTOR_BETA.items():
        for comp,tick in meta["companies"].items():
            ticker_info[tick.upper()]={"sector":sec,"beta":meta["beta"]}

    idx_returns, idx_err = get_index_returns("^NSEI", period=lookback)
    macro_risk = compute_macro_risk(idx_returns)
    model=StockInvestmentModel()

    records=[]; returns_matrix=[]; warnings=[]
    for _,row in pf_df.iterrows():
        t=row["Ticker"]; w=row["NormWeight"]
        info=ticker_info.get(t, {"sector":"Unknown","beta":np.nan})
        sector=info["sector"]; beta=info["beta"]
        de_ratio,de_err=FinanceDataFetcher.debt_to_equity(t)
        ev,ev_err,eq_cnt,earn_raw=FinanceDataFetcher.earnings_volatility_extended(t)
        rets,ret_err=FinanceDataFetcher.historical_returns(t, period=lookback)
        for e in [de_err,ev_err,ret_err]:
            if e: warnings.append(f"{t}: {e}")
        if idx_err: warnings.append(f"Index: {idx_err}")
        if rets is not None:
            returns_matrix.append(rets.rename(t))
        sector_r=normalize_sector_label(SECTOR_RISK_MAP.get(sector,"medium"))
        if (de_ratio is None) or (ev is None) or (rets is None): continue
        risk_score=model.calculate_risk_score(de_ratio, beta if not np.isnan(beta) else 1.0, ev, sector_r, macro_risk)
        conf=derive_confidence(ev,de_ratio,eq_cnt,idx_returns,rets)
        records.append({
            "Ticker":t,"Sector":sector,"Weight":w,"RiskScore":risk_score,
            "D/E":de_ratio,"EarnVol":ev,"Beta":beta,"SectorRisk":sector_r,"RiskDataConf":conf
        })

    if not records:
        st.error("No sufficient data for provided tickers."); return
    per_df=pd.DataFrame(records)
    if not returns_matrix:
        st.error("No return series formed."); return
    returns_df=pd.concat(returns_matrix, axis=1, join="inner")
    aw=per_df.set_index("Ticker")["Weight"].reindex(returns_df.columns).fillna(0)
    aw=aw/aw.sum()
    portfolio_returns=(returns_df*aw.values).sum(axis=1)

    var_calc=VaRCalculator(portfolio_returns)
    p_var=var_calc.calculate_var(confidence)
    p_cvar=var_calc.calculate_cvar(confidence)

    port_risk_score=np.sum(per_df["RiskScore"]*per_df["Weight"])
    avg_de=np.sum(per_df["D/E"]*per_df["Weight"])
    avg_ev=np.sum(per_df["EarnVol"]*per_df["Weight"])
    avg_beta=np.nansum(per_df["Beta"]*per_df["Weight"])
    avg_conf=np.sum(per_df["RiskDataConf"]*per_df["Weight"])
    sentiment_conf=0.2
    combined_conf=model.calculate_confidence(sentiment_conf, avg_conf)
    _,_,action=model.investment_assessment(0.0, port_risk_score)

    cov=returns_df.cov()
    w_vec=aw.values.reshape(-1,1)
    port_var=float(w_vec.T @ cov.values @ w_vec)
    port_vol=np.sqrt(port_var)
    marg=(cov.values @ w_vec).flatten()/port_vol if port_vol>0 else np.zeros_like(w_vec.flatten())
    comp=marg*w_vec.flatten()
    pct=comp/comp.sum() if comp.sum()!=0 else comp

    if warnings:
        with st.expander("Data Notices", expanded=False):
            for wmsg in warnings: st.warning(wmsg)

    st.markdown("#### Portfolio Summary")
    cards=[
        ("Risk Score",f"{port_risk_score:.2f}"),
        ("Risk Level",model.risk_level(port_risk_score)),
        ("Confidence",f"{combined_conf:.0f}%"),
        ("Macro Risk",f"{macro_risk:.2f}"),
        ("Tickers",f"{len(per_df)}")
    ]
    st.markdown('<div class="inline-cards">'+"".join(
        f'<div class="metric-box"><h6>{k}</h6><p>{v}</p></div>' for k,v in cards
    )+'</div>', unsafe_allow_html=True)

    st.markdown("#### Suggested Action")
    al=action.lower()
    if "buy" in al: st.success(action)
    elif "hold" in al: st.warning(action)
    else: st.error(action)

    st.markdown("#### Factor Averages")
    fac=[
        ("Avg D/E",f"{avg_de:.2f}"),
        ("Avg Earnings Vol",f"{avg_ev:.2f}"),
        ("Avg Beta",f"{avg_beta:.2f}"),
        ("Avg Data Conf",f"{avg_conf:.2f}")
    ]
    st.markdown('<div class="inline-cards">'+"".join(
        f'<div class="metric-box"><h6>{k}</h6><p>{v}</p></div>' for k,v in fac
    )+'</div>', unsafe_allow_html=True)

    st.markdown("#### Portfolio VaR / CVaR (Per 1 Unit Capital)")
    rm=[
        (f"VaR {int(confidence*100)}%",fmt_pct(p_var)),
        ("CVaR",fmt_pct(p_cvar)),
        ("Daily Vol",fmt_pct(port_vol))
    ]
    st.markdown('<div class="inline-cards">'+"".join(
        f'<div class="metric-box"><h6>{k}</h6><p>{v}</p></div>' for k,v in rm
    )+'</div>', unsafe_allow_html=True)

    st.markdown("#### Return Series (120 Recent Days)")
    st.line_chart(portfolio_returns.tail(120))

    with st.expander("Per-Ticker Factor Table"):
        show=per_df.copy(); show["Weight%"]=show["Weight"]*100
        st.dataframe(show[["Ticker","Sector","Weight%","RiskScore","D/E","EarnVol","Beta","SectorRisk","RiskDataConf"]]
                     .style.format({"Weight%":"{:.2f}","RiskScore":"{:.2f}","D/E":"{:.2f}",
                                    "EarnVol":"{:.2f}","Beta":"{:.2f}","RiskDataConf":"{:.2f}"}))

    with st.expander("Variance Contributions"):
        contrib=pd.DataFrame({
            "Ticker":returns_df.columns,
            "Weight%":aw.values*100,
            "MarginalVol":marg,
            "ComponentVol":comp,
            "PctTotalVol%":pct*100
        })
        st.dataframe(contrib.style.format({
            "Weight%":"{:.2f}",
            "MarginalVol":"{:.4f}",
            "ComponentVol":"{:.4f}",
            "PctTotalVol%":"{:.2f}"
        }))

    with st.expander("Correlation Matrix"):
        st.dataframe(returns_df.corr().style.format("{:.2f}"))

    with st.expander("Downloads (CSV)"):
        st.download_button("Portfolio Returns CSV",
                           data=portfolio_returns.to_csv().encode(),
                           file_name="portfolio_returns.csv",
                           mime="text/csv")
        st.download_button("Per-Ticker Factors CSV",
                           data=per_df.to_csv(index=False).encode(),
                           file_name="portfolio_factors.csv",
                           mime="text/csv")

    # Allocation pie
    fig,ax=plt.subplots(figsize=(4,4),dpi=150)
    ax.pie(aw.values, labels=[t[:12] for t in aw.index], autopct="%1.1f%%", startangle=90, textprops={"fontsize":8})
    ax.set_title("Portfolio Allocation", fontsize=10)
    plt.tight_layout()
    buf=BytesIO(); fig.savefig(buf, format="png"); plt.close(fig)
    alloc_bytes=buf.getvalue()
    st.image(alloc_bytes, caption="Allocation Pie Chart", use_column_width=False)

    report={
        "portfolio":per_df.to_dict(orient="records"),
        "summary":{
            "risk_score":port_risk_score,
            "risk_level":model.risk_level(port_risk_score),
            "confidence":combined_conf,
            "macro_risk":macro_risk,
            "action":action,
            "num_tickers":len(per_df)
        },
        "factors":{
            "avg_de":avg_de,
            "avg_ev":avg_ev,
            "avg_beta":avg_beta,
            "avg_conf":avg_conf
        },
        "var":{
            "cl_label":f"{int(confidence*100)}% Confidence",
            "var_pct":p_var,
            "cvar_pct":p_cvar,
            "vol":port_vol,
            "tail_prob":1-confidence
        },
        "variance":[
            {"Ticker":t,"Weight%":wgt*100,"PctTotalVol%":pv*100}
            for t,wgt,pv in zip(returns_df.columns, aw.values, pct)
        ]
    }
    st.session_state["latest_portfolio_report"]=report
    st.session_state["latest_portfolio_allocation_chart"]=alloc_bytes

    pdf_bytes=generate_portfolio_pdf(report, allocation_chart=alloc_bytes)
    c1,c2=st.columns(2)
    with c1:
        st.download_button("Portfolio PDF", data=pdf_bytes,
                           file_name="portfolio_report.pdf", mime="application/pdf")
    with c2:
        if "latest_assessment_report" in st.session_state:
            st.download_button("Combined PDF",
                               data=generate_combined_pdf(
                                   assessment=st.session_state.get("latest_assessment_report"),
                                   portfolio=report,
                                   allocation_chart=alloc_bytes),
                               file_name="combined_report.pdf",
                               mime="application/pdf")
        else:
            st.button("Combined PDF (needs assessment first)", disabled=True)

    st.caption("Historical method only; no forward simulation or stress. Interpret cautiously.")
    st.success("Portfolio analysis complete.")