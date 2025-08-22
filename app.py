import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import random
from uuid import uuid4

# =========================================================
# CONFIG & CONSTANTS
# =========================================================
st.set_page_config(
    page_title="CashLagao - AI Portfolio Management",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

SECTOR_BETA = {
    'Metal': 2.2,
    'Automotive': 1.8,
    'Financial Services': 1.6,
    'Energy': 1.4,
    'Technology': 1.1,
    'Consumers': 0.7,
    'FMCG': 0.8,
    'Pharma': 1.05
}

SECTOR_COMPANIES = {
    "Metal": ["JWS", "Sindal Steel", "Tata Steel", "Vedanta", "Hindalco Industries",
              "Hindustan Zinc", "Steel Authority of India", "NMDC"],
    "Automotive": ["Tata Motors", "Bajaj Auto", "Eicher", "Hero Motocorp", "M&M",
                   "Ashok Leyland", "Maruti Suzuki India", "TVS Motor"],
    "Financial Services": ["Bajaj Finance", "Muthoot Finance", "Aditya Birla Capital",
                           "HDFC Bank", "ICICI Bank", "Shriram Finance", "State Bank of India",
                           "Life Insurance Corporation of India"],
    "Energy": ["JSW Power", "Tata Power", "Adani Power", "Reliance Power",
               "Power Grid Corporation", "Indian Oil Corporation",
               "Bharat Petroleum Corporation", "NTPC"],
    "Technology": ["TCS", "Wipro", "Infosys", "Tech Mahindra", "HCL Technologies",
                   "Persistent Systems", "L&T", "Tata Elxsi"],
    "Consumers": ["Blue Star", "Voltas", "Crompton Greaves", "Havells",
                  "Bajaj Electricals", "Whirlpool of India", "Titan Company", "Asian Paints"],
    "FMCG": ["Dabur", "Godrej Consumer", "Britannia", "ITC", "Nestle India",
             "Marico", "Tata Consumer Products", "Colgate-Palmolive India"],
    "Pharma": ["Cipla", "Dr Reddys Laboratories", "Mankind Pharma",
               "Sun Pharmaceutical Industries", "Torrent Pharmaceuticals",
               "Lupin", "Zydus Lifesciences", "Biocon"]
}

ALL_COMPANIES = [
    {"company": c, "sector": sector, "beta": SECTOR_BETA[sector]}
    for sector, comps in SECTOR_COMPANIES.items() for c in comps
]

RISK_LEVEL_PARAMS = {
    "Low":   {"ret_mean": 0.06, "ret_std": 0.12},
    "Medium":{"ret_mean": 0.10, "ret_std": 0.18},
    "High":  {"ret_mean": 0.15, "ret_std": 0.28}
}

# =========================================================
# SESSION STATE INIT
# =========================================================
ss = st.session_state
if "holdings" not in ss:
    ss.holdings = []
if "simulation_results" not in ss:
    ss.simulation_results = None
if "generate_analysis" not in ss:
    ss.generate_analysis = False
if "run_simulation" not in ss:
    ss.run_simulation = False
if "last_added" not in ss:
    ss.last_added = None
if "dark_mode" not in ss:
    ss.dark_mode = False  # default light
if "theme_token" not in ss:
    ss.theme_token = str(uuid4())  # invalidate cached CSS when toggled

# If holdings accidentally became a DataFrame earlier, normalize back to list
if isinstance(ss.holdings, pd.DataFrame):
    ss.holdings = ss.holdings.to_dict("records")

# =========================================================
# HELPER FUNCTIONS
# =========================================================
def get_holdings_records():
    """Return (records_list, is_empty) regardless of internal storage type."""
    h = ss.holdings
    if isinstance(h, pd.DataFrame):
        return h.to_dict("records"), h.empty
    if isinstance(h, list):
        return h, len(h) == 0
    return [], True

def add_holding(company: str, sector: str, amount: float, notes: str = ""):
    if amount <= 0:
        st.warning("Amount must be greater than 0.")
        return
    records, _ = get_holdings_records()
    records.append({
        "id": str(uuid4())[:8],
        "company": company,
        "sector": sector,
        "sector_beta": SECTOR_BETA.get(sector, 1.0),
        "amount_invested": float(amount),
        "notes": notes.strip(),
        "added_at": datetime.utcnow().isoformat(timespec="seconds") + "Z"
    })
    ss.holdings = records
    ss.last_added = company

def remove_holding(holding_id: str):
    records, _ = get_holdings_records()
    ss.holdings = [h for h in records if h["id"] != holding_id]

def update_holding(holding_id: str, amount: float, notes: str):
    records, _ = get_holdings_records()
    for h in records:
        if h["id"] == holding_id:
            h["amount_invested"] = float(amount)
            h["notes"] = notes.strip()
            break
    ss.holdings = records

def compute_portfolio_from_holdings():
    records, is_empty = get_holdings_records()
    if is_empty:
        return {}
    df = pd.DataFrame(records)
    sector_group = df.groupby("sector").agg(
        total_invested=("amount_invested", "sum"),
        beta=("sector_beta", "mean"),
        count=("id", "count")
    ).reset_index()
    total_value = sector_group.total_invested.sum()
    portfolio_data = {}
    base_rf = 0.04
    equity_premium = 0.06
    for _, row in sector_group.iterrows():
        sector = row["sector"]
        weight = row["total_invested"] / total_value if total_value > 0 else 0
        beta = row["beta"]
        expected_return = base_rf + beta * equity_premium
        annual_vol = 0.15 + (beta - 1.0) * 0.10
        annual_vol = max(0.05, annual_vol)
        sharpe = (expected_return - base_rf) / annual_vol
        sortino = sharpe * 1.1
        var_95 = annual_vol * 1.65 * 100 * 0.6
        cvar_95 = var_95 * 1.2
        max_drawdown = annual_vol * 3 * 100
        sentiment_score = random.uniform(-0.5, 0.7)
        change_24h = random.uniform(-3, 3)
        portfolio_data[sector] = {
            "current_value": row["total_invested"],
            "allocation": weight * 100,
            "beta": beta,
            "expected_return": expected_return,
            "volatility": annual_vol,
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "var_95": var_95,
            "cvar_95": cvar_95,
            "max_drawdown": max_drawdown,
            "sentiment_score": sentiment_score,
            "change_24h": change_24h,
            "holding_count": row["count"]
        }
    return portfolio_data

def filter_companies(search_text: str, sector_filter: str | None):
    df = pd.DataFrame(ALL_COMPANIES)
    if sector_filter and sector_filter != "All":
        df = df[df["sector"] == sector_filter]
    if search_text:
        s = search_text.lower()
        df = df[df["company"].str.lower().str.contains(s)]
    return df.sort_values("company")

def generate_time_series(sectors, portfolio_data, days=180):
    dates = pd.date_range(start=datetime.now() - timedelta(days=days), end=datetime.now(), freq='D')
    if len(sectors) == 0:
        return pd.DataFrame(index=dates), pd.DataFrame()
    corr_matrix = pd.DataFrame(index=sectors, columns=sectors, dtype=float)
    for i, s1 in enumerate(sectors):
        for j, s2 in enumerate(sectors):
            if i == j:
                corr_matrix.loc[s1, s2] = 1.0
            elif i < j:
                beta_diff = abs(portfolio_data[s1]["beta"] - portfolio_data[s2]["beta"])
                base_corr = 0.85 - min(beta_diff * 0.25, 0.4)
                noise = random.uniform(-0.1, 0.1)
                corr_matrix.loc[s1, s2] = max(min(base_corr + noise, 0.95), 0.25)
            else:
                corr_matrix.loc[s1, s2] = corr_matrix.loc[s2, s1]
    n_samples = len(dates)
    uncorrelated = np.random.normal(0, 1, size=(n_samples, len(sectors)))
    try:
        chol = np.linalg.cholesky(corr_matrix.values.astype(float))
    except np.linalg.LinAlgError:
        st.warning("Correlation matrix not positive definite. Using identity.")
        chol = np.eye(len(sectors))
    correlated = uncorrelated @ chol
    data = {}
    for i, sector in enumerate(sectors):
        mu = portfolio_data[sector]["expected_return"]
        vol = portfolio_data[sector]["volatility"]
        daily_mu = mu / 252
        daily_vol = vol / np.sqrt(252)
        returns = daily_mu + daily_vol * correlated[:, i]
        prices = 100 * np.cumprod(1 + returns)
        data[sector] = prices
    return pd.DataFrame(data, index=dates), corr_matrix

def run_monte_carlo(initial_value, expected_returns, volatilities, correlations,
                    weights, days, scenarios, confidence_level):
    results = np.zeros((days + 1, scenarios))
    results[0, :] = initial_value
    correlations_arr = correlations.values.astype(float) if isinstance(correlations, pd.DataFrame) else np.array(correlations, dtype=float)
    try:
        chol = np.linalg.cholesky(correlations_arr)
    except np.linalg.LinAlgError:
        st.warning("Monte Carlo: correlation matrix not PD. Using identity matrix.")
        chol = np.eye(len(weights))
    for s in range(scenarios):
        for d in range(1, days + 1):
            z = np.random.normal(0, 1, size=len(weights))
            corr_z = chol @ z
            port_ret = 0
            for i in range(len(weights)):
                mu = expected_returns[i] / 252
                sigma = volatilities[i] / np.sqrt(252)
                asset_ret = mu + sigma * corr_z[i]
                port_ret += weights[i] * asset_ret
            results[d, s] = results[d-1, s] * (1 + port_ret)
    return results

def generate_ai_recommendations(portfolio_data, sectors):
    recs = []
    if not portfolio_data:
        return recs
    beta_sorted = sorted(sectors, key=lambda s: portfolio_data[s]['beta'], reverse=True)
    sentiment_sorted = sorted(sectors, key=lambda s: portfolio_data[s]['sentiment_score'])
    high_beta = beta_sorted[0]
    low_beta = beta_sorted[-1]
    worst_sentiment = sentiment_sorted[0]
    recs.append({
        "action": "HEDGE",
        "domain": high_beta,
        "confidence": random.uniform(75, 90),
        "description": f"High beta ({portfolio_data[high_beta]['beta']:.2f}) increases volatility exposure. Consider partial hedge.",
        "reasoning": [
            f"Sector beta {portfolio_data[high_beta]['beta']:.2f} > portfolio median",
            f"VaR (95%) {portfolio_data[high_beta]['var_95']:.2f}%",
            f"Sharpe {portfolio_data[high_beta]['sharpe_ratio']:.2f}"
        ],
        "impact": f"{random.uniform(5,15):.1f}% downside risk mitigation potential"
    })
    recs.append({
        "action": "INCREASE",
        "domain": low_beta,
        "confidence": random.uniform(70, 88),
        "description": f"Lower beta ({portfolio_data[low_beta]['beta']:.2f}) can stabilize portfolio variance.",
        "reasoning": [
            f"Sector volatility est. {portfolio_data[low_beta]['volatility']:.2%}",
            f"Sharpe {portfolio_data[low_beta]['sharpe_ratio']:.2f} near top tercile",
            "Low cross-correlation improves diversification"
        ],
        "impact": f"{random.uniform(1,4):.1f}% improvement in risk-adjusted return"
    })
    recs.append({
        "action": "REBALANCE",
        "domain": worst_sentiment,
        "confidence": random.uniform(65, 85),
        "description": "Negative sentiment indicates potential short-term headwinds.",
        "reasoning": [
            f"Sentiment score {portfolio_data[worst_sentiment]['sentiment_score']:.2f}",
            f"Drawdown risk {portfolio_data[worst_sentiment]['max_drawdown']:.1f}%",
            "Correlation cluster suggests contagion risk"
        ],
        "impact": f"{random.uniform(2,7):.1f}% reduction in tail risk"
    })
    return recs

def apply_theme(dark: bool):
    """Inject CSS for dark or light mode."""
    if dark:
        st.markdown(f"""
        <style id="app-theme-{ss.theme_token}">
        body, .stApp {{
            background-color: #0e1117;
            color: #e2e2e2;
        }}
        .block-container {{
            padding-top: 1rem;
        }}
        .header-title {{
            background: linear-gradient(90deg,#89f7fe 0%,#66a6ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3rem;
            font-weight: 800;
            text-align:center;
            margin: 0.25rem 0 0.75rem 0;
        }}
        .metric-card {{
            background: #1e2533;
            border: 1px solid #283347;
        }}
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <style id="app-theme-{ss.theme_token}">
        .header-title {{
            background: linear-gradient(90deg,#667eea 0%,#764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3rem;
            font-weight: 800;
            text-align:center;
            margin: 0.25rem 0 0.75rem 0;
        }}
        .metric-card {{
            background: white;
            padding: 0.9rem 1rem;
            border-radius: 10px;
            border:1px solid #e6e6e6;
            box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        }}
        </style>
        """, unsafe_allow_html=True)

def plotly_template():
    return "plotly_dark" if ss.dark_mode else "plotly_white"

# Apply theme styles
apply_theme(ss.dark_mode)

# =========================================================
# SIDEBAR CONTROLS
# =========================================================
with st.sidebar:
    st.header("Settings")

    # Dark Mode Toggle
    new_dark = st.toggle("🌙 Dark Mode", value=ss.dark_mode)
    if new_dark != ss.dark_mode:
        ss.dark_mode = new_dark
        ss.theme_token = str(uuid4())  # force style refresh
        apply_theme(ss.dark_mode)

    st.markdown("---")
    st.subheader("Add Holding")
    sector_filter = st.selectbox("Sector", ["-- Select --"] + list(SECTOR_BETA.keys()))
    if sector_filter != "-- Select --":
        company_list = ["-- Select --"] + SECTOR_COMPANIES[sector_filter]
    else:
        company_list = ["-- Select --"]
    company_choice = st.selectbox("Company", company_list, key="company_choice_main")
    amount_val = st.number_input("Amount Invested (₹)", min_value=0.0, step=1000.0, key="amount_add_main")
    notes_val = st.text_input("Notes (optional)", key="notes_add_main")
    if st.button("Add Holding", disabled=(company_choice == "-- Select --" or amount_val <= 0)):
        add_holding(company_choice, sector_filter, amount_val, notes_val)
        st.success(f"Added {company_choice}")

    st.markdown("---")
    st.subheader("Analytics Filters")

    risk_level = st.selectbox("Risk Level (context)", ["Low", "Medium", "High"], index=1)
    timeframe = st.selectbox("Timeframe (synthetic history)", ["3M", "6M", "1Y", "2Y"], index=1)
    hist_days_map = {"3M":90, "6M":180, "1Y":252, "2Y":504}
    hist_days = hist_days_map[timeframe]

    records, is_empty_holdings = get_holdings_records()
    existing_sectors = sorted({r['sector'] for r in records}) if not is_empty_holdings else list(SECTOR_BETA.keys())
    selected_sectors = st.multiselect("Active Sectors", existing_sectors, default=existing_sectors)

    st.markdown("---")
    st.subheader("Simulation Settings")
    mc_scenarios = st.slider("Monte Carlo Scenarios", 100, 2000, 600, step=100)
    projection_days = st.slider("Projection Days", 60, 365, 180, step=30)
    confidence_level = st.slider("Confidence Level (%)", 90, 99, 95, 1)

    run_sim = st.button("🔄 Run Monte Carlo Simulation", disabled=(len(selected_sectors) == 0 or is_empty_holdings))
    if run_sim:
        ss.run_simulation = True

    gen_ai = st.button("🤖 Generate AI Analysis", disabled=(len(selected_sectors) == 0 or is_empty_holdings))
    if gen_ai:
        ss.generate_analysis = True

    st.markdown("---")
    if st.button("🧹 Clear All Holdings", disabled=is_empty_holdings):
        ss.holdings = []
        ss.simulation_results = None
        st.warning("All holdings cleared.")

# =========================================================
# HEADER
# =========================================================
st.markdown('<h1 class="header-title">CashLagao</h1>', unsafe_allow_html=True)
st.caption("AI-driven portfolio management & analytics. (Data is simulated; you control holdings.)")

# =========================================================
# HOLDINGS MANAGEMENT
# =========================================================
st.subheader("📋 Current Holdings")

records, is_empty = get_holdings_records()
if is_empty:
    st.info("No holdings yet. Use the sidebar to add your first holding.")
else:
    for h in records:
        with st.expander(f"{h['company']} | {h['sector']} | ₹{h['amount_invested']:,.2f}", expanded=False):
            c1, c2, c3, c4, c5 = st.columns([2,2,2,3,2])
            with c1:
                st.markdown(f"Sector Beta: **{h['sector_beta']:.2f}**")
            with c2:
                new_amt = st.number_input("Amount (₹)", min_value=0.0,
                                          value=float(h['amount_invested']),
                                          step=500.0, key=f"amt_{h['id']}")
            with c3:
                new_notes = st.text_input("Notes", value=h['notes'], key=f"note_{h['id']}")
            with c4:
                st.caption(f"Added: {h['added_at']}")
            with c5:
                if st.button("💾 Save", key=f"save_{h['id']}"):
                    update_holding(h['id'], new_amt, new_notes)
                    st.success("Updated.")
                if st.button("🗑️ Remove", key=f"rm_{h['id']}"):
                    remove_holding(h['id'])
                    st.warning("Removed.")
                    st.experimental_rerun()

    df_hold = pd.DataFrame(records)
    display_df = df_hold[["company","sector","amount_invested","sector_beta","notes"]].rename(columns={
        "company":"Company","sector":"Sector","amount_invested":"Amount (₹)","sector_beta":"Sector Beta","notes":"Notes"
    })
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    csv = display_df.to_csv(index=False).encode("utf-8")
    st.download_button("⬇️ Download Holdings CSV", csv, "holdings.csv", "text/csv")

# =========================================================
# PORTFOLIO AGGREGATION
# =========================================================
portfolio_data_all = compute_portfolio_from_holdings()
portfolio_data = {s: v for s, v in portfolio_data_all.items() if s in selected_sectors}

if not portfolio_data:
    st.warning("Add holdings or select at least one active sector to view analytics.")
    st.stop()

# =========================================================
# BASIC METRICS
# =========================================================
total_value = sum(v['current_value'] for v in portfolio_data.values())
avg_sharpe = np.mean([v['sharpe_ratio'] for v in portfolio_data.values()])
avg_var = np.mean([v['var_95'] for v in portfolio_data.values()])
sentiment_avg = np.mean([v['sentiment_score'] for v in portfolio_data.values()])
sentiment_label = "Positive" if sentiment_avg > 0.15 else "Negative" if sentiment_avg < -0.15 else "Neutral"
total_change = np.mean([v['change_24h'] for v in portfolio_data.values()])
weighted_beta = sum(v['current_value']*v['beta'] for v in portfolio_data.values())/total_value

st.subheader("📊 Portfolio Metrics")
m1, m2, m3, m4, m5 = st.columns(5)
with m1:
    st.metric("Total Portfolio Value", f"₹{total_value:,.0f}", f"{total_change:+.2f}% (avg)")
with m2:
    st.metric("Avg. VaR (95%)", f"{avg_var:.2f}%", help="Approx sector-level Value at Risk (heuristic)")
with m3:
    st.metric("Avg. Sharpe", f"{avg_sharpe:.2f}")
with m4:
    st.metric("Sentiment", sentiment_label, f"{sentiment_avg:+.2f}")
with m5:
    st.metric("Weighted Beta", f"{weighted_beta:.2f}")

# =========================================================
# TIME SERIES
# =========================================================
time_series_data, correlation_matrix = generate_time_series(list(portfolio_data.keys()), portfolio_data, days=hist_days)

# =========================================================
# TABS
# =========================================================
tab1, tab2, tab3, tab4 = st.tabs(["Basic Analytics", "Risk Analysis", "Optimization", "Monte Carlo"])
tpl = plotly_template()

# ------------- TAB 1 -------------
with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Allocation by Sector")
        alloc_labels = list(portfolio_data.keys())
        alloc_values = [portfolio_data[s]['allocation'] for s in alloc_labels]
        fig_alloc = px.pie(values=alloc_values, names=alloc_labels,
                           title="Portfolio Allocation (%)",
                           hole=0.4, color_discrete_sequence=px.colors.qualitative.Set3,
                           template=tpl)
        st.plotly_chart(fig_alloc, use_container_width=True)
    with c2:
        st.markdown("#### Risk Metrics (VaR vs CVaR)")
        fig_risk = go.Figure()
        fig_risk.add_trace(go.Bar(
            name="VaR (95%)",
            x=alloc_labels,
            y=[portfolio_data[s]['var_95'] for s in alloc_labels]
        ))
        fig_risk.add_trace(go.Bar(
            name="CVaR (95%)",
            x=alloc_labels,
            y=[portfolio_data[s]['cvar_95'] for s in alloc_labels]
        ))
        fig_risk.update_layout(barmode='group', yaxis_title="%", margin=dict(l=10,r=10,t=40,b=10), template=tpl)
        st.plotly_chart(fig_risk, use_container_width=True)

    st.markdown("#### Historical Performance (Synthetic)")
    if not time_series_data.empty:
        fig_line = px.line(time_series_data, x=time_series_data.index, y=time_series_data.columns,
                           title=f"{hist_days}-Day Synthetic Performance", template=tpl)
        fig_line.update_layout(xaxis_title="Date", yaxis_title="Index Value", legend_title="Sector",
                               margin=dict(l=10,r=10,t=50,b=10))
        st.plotly_chart(fig_line, use_container_width=True)

    st.markdown("#### Sector Correlation Heatmap")
    if not correlation_matrix.empty:
        fig_heat = px.imshow(correlation_matrix.astype(float),
                             text_auto='.2f',
                             color_continuous_scale='RdBu_r',
                             zmin=-1, zmax=1,
                             title="Correlation Matrix",
                             template=tpl)
        fig_heat.update_layout(margin=dict(l=10,r=10,t=50,b=10))
        st.plotly_chart(fig_heat, use_container_width=True)

# ------------- TAB 2 -------------
with tab2:
    st.markdown("#### Drawdown Analysis (Synthetic)")
    drawdowns = pd.DataFrame(index=time_series_data.index)
    for sector in portfolio_data.keys():
        prices = time_series_data[sector]
        running_max = np.maximum.accumulate(prices)
        dd = (prices - running_max) / running_max
        drawdowns[sector] = dd
    fig_dd = px.line(drawdowns, x=drawdowns.index, y=drawdowns.columns,
                     title="Drawdowns", labels={"value":"Drawdown"}, template=tpl)
    fig_dd.update_layout(yaxis=dict(tickformat=".0%"), margin=dict(l=10,r=10,t=50,b=10))
    st.plotly_chart(fig_dd, use_container_width=True)

    st.markdown("#### Risk-Adjusted Return Comparison")
    risk_metrics = pd.DataFrame({
        "Sector": list(portfolio_data.keys()),
        "Sharpe": [portfolio_data[s]['sharpe_ratio'] for s in portfolio_data],
        "Sortino": [portfolio_data[s]['sortino_ratio'] for s in portfolio_data],
        "Max Drawdown (%)": [portfolio_data[s]['max_drawdown'] for s in portfolio_data],
        "VaR (95%)": [portfolio_data[s]['var_95'] for s in portfolio_data],
        "CVaR (95%)": [portfolio_data[s]['cvar_95'] for s in portfolio_data],
        "Beta": [portfolio_data[s]['beta'] for s in portfolio_data]
    })
    categories = ["Sharpe","Sortino","Max Drawdown (%)","VaR (95%)","CVaR (95%)","Beta"]
    fig_radar = go.Figure()
    for _, row in risk_metrics.iterrows():
        vals = []
        for cat in categories:
            col = risk_metrics[cat].values
            if cat in ["Max Drawdown (%)","VaR (95%)","CVaR (95%)","Beta"]:
                inv = 1 / np.array(col)
                v = (1/row[cat] - inv.min())/(inv.max()-inv.min() + 1e-9)
            else:
                v = (row[cat] - col.min())/(col.max()-col.min() + 1e-9)
            vals.append(v)
        fig_radar.add_trace(go.Scatterpolar(r=vals, theta=categories, fill='toself', name=row["Sector"]))
    fig_radar.update_layout(title="Normalized Risk Profile (Higher Better)",
                            polar=dict(radialaxis=dict(visible=True,range=[0,1])),
                            template=tpl)
    st.plotly_chart(fig_radar, use_container_width=True)
    st.markdown("#### Risk Metrics Table")
    st.dataframe(risk_metrics.round(2), use_container_width=True, hide_index=True)

# ------------- TAB 3 -------------
with tab3:
    st.markdown("#### Efficient Frontier (Heuristic)")
    sectors = list(portfolio_data.keys())
    domain_returns = [portfolio_data[s]['expected_return'] for s in sectors]
    domain_vols = [portfolio_data[s]['volatility'] for s in sectors]
    target_returns = np.linspace(min(domain_returns)*0.8, max(domain_returns)*1.2, 60)
    frontier_vol = 0.04 + 0.5 * (target_returns - target_returns.min())**1.3
    fig_frontier = go.Figure()
    fig_frontier.add_trace(go.Scatter(x=frontier_vol, y=target_returns, mode='lines', name='Efficient Frontier',
                                      line=dict(color='#667eea', width=3)))
    fig_frontier.add_trace(go.Scatter(
        x=domain_vols, y=domain_returns, mode='markers', name='Sectors',
        marker=dict(size=12, color='#764ba2', line=dict(width=1,color='black')),
        text=sectors, hovertemplate='%{text}<br>Ret %{y:.2%}<br>Vol %{x:.2%}<extra></extra>'
    ))
    sharpe_list = [(portfolio_data[s]['expected_return']-0.04)/portfolio_data[s]['volatility'] for s in sectors]
    opt_idx = int(np.argmax(sharpe_list))
    fig_frontier.add_trace(go.Scatter(
        x=[domain_vols[opt_idx]], y=[domain_returns[opt_idx]], mode='markers',
        name='Optimal (Heuristic)', marker=dict(size=18, color='orangered', symbol='star')
    ))
    fig_frontier.update_layout(
        title="Efficient Frontier (Synthetic Approximation)",
        xaxis=dict(title="Volatility (Annual)", tickformat=".0%"),
        yaxis=dict(title="Expected Return (Annual)", tickformat=".0%"),
        margin=dict(l=10,r=10,t=50,b=10),
        template=tpl
    )
    st.plotly_chart(fig_frontier, use_container_width=True)

    current_weights = np.array([portfolio_data[s]['allocation'] for s in sectors])
    current_weights = current_weights / current_weights.sum()
    sharpes = np.array([portfolio_data[s]['sharpe_ratio'] for s in sectors])
    opt_weights = current_weights * (sharpes / sharpes.mean())
    opt_weights = opt_weights / opt_weights.sum()

    weight_df = pd.DataFrame({
        "Sector": sectors,
        "Current Weight": current_weights,
        "Suggested Weight": opt_weights
    })
    fig_w = px.bar(weight_df, x="Sector", y=["Current Weight","Suggested Weight"],
                   barmode="group", title="Current vs Suggested Allocation",
                   text_auto='.1%', template=tpl)
    fig_w.update_layout(yaxis=dict(tickformat=".0%"), margin=dict(l=10,r=10,t=50,b=10))
    st.plotly_chart(fig_w, use_container_width=True)

    cur_ret = np.dot(current_weights, domain_returns)
    cur_vol = np.dot(current_weights, domain_vols)
    opt_ret = np.dot(opt_weights, domain_returns)
    opt_vol = np.dot(opt_weights, domain_vols)
    cur_sharpe = (cur_ret - 0.04)/(cur_vol+1e-9)
    opt_sharpe = (opt_ret - 0.04)/(opt_vol+1e-9)

    c1, c2, c3 = st.columns(3)
    c1.metric("Expected Return (Suggested)", f"{opt_ret:.2%}", f"{(opt_ret-cur_ret):+.2%}")
    c2.metric("Expected Volatility (Suggested)", f"{opt_vol:.2%}", f"{(opt_vol-cur_vol):+.2%}")
    c3.metric("Sharpe (Suggested)", f"{opt_sharpe:.2f}", f"{(opt_sharpe-cur_sharpe):+.2f}")

# ------------- TAB 4 -------------
with tab4:
    st.markdown("#### Monte Carlo Simulation")
    if ss.run_simulation:
        with st.spinner("Running simulation..."):
            expected_returns = [portfolio_data[s]['expected_return'] for s in portfolio_data]
            volatilities = [portfolio_data[s]['volatility'] for s in portfolio_data]
            weights = [portfolio_data[s]['allocation']/100 for s in portfolio_data]
            corr = correlation_matrix if not correlation_matrix.empty else pd.DataFrame(np.eye(len(weights)))
            ss.simulation_results = run_monte_carlo(
                total_value, expected_returns, volatilities, corr,
                weights, projection_days, mc_scenarios, confidence_level
            )
            ss.run_simulation = False

    if ss.simulation_results is None:
        st.info("Configure settings and click 'Run Monte Carlo Simulation' in the sidebar.")
    else:
        results = ss.simulation_results
        future_dates = pd.date_range(start=datetime.now(), periods=results.shape[0], freq='D')
        median_line = np.median(results, axis=1)
        upper_95 = np.percentile(results, 97.5, axis=1)
        lower_95 = np.percentile(results, 2.5, axis=1)
        upper_75 = np.percentile(results, 87.5, axis=1)
        lower_75 = np.percentile(results, 12.5, axis=1)

        fig_mc = go.Figure()
        sample_idx = random.sample(range(results.shape[1]), min(120, results.shape[1]))
        faint_color = "rgba(200,200,200,0.05)" if ss.dark_mode else "rgba(120,120,120,0.07)"
        for i in sample_idx:
            fig_mc.add_trace(go.Scatter(
                x=future_dates, y=results[:, i], mode="lines",
                line=dict(color=faint_color), hoverinfo='skip', showlegend=False
            ))
        fig_mc.add_trace(go.Scatter(
            x=future_dates.tolist()+future_dates.tolist()[::-1],
            y=upper_95.tolist()+lower_95.tolist()[::-1],
            fill='toself', fillcolor='rgba(102,126,234,0.10)',
            line=dict(color='rgba(0,0,0,0)'), name='95% CI'
        ))
        fig_mc.add_trace(go.Scatter(
            x=future_dates.tolist()+future_dates.tolist()[::-1],
            y=upper_75.tolist()+lower_75.tolist()[::-1],
            fill='toself', fillcolor='rgba(102,126,234,0.30)',
            line=dict(color='rgba(0,0,0,0)'), name='50% CI'
        ))
        fig_mc.add_trace(go.Scatter(
            x=future_dates, y=median_line,
            mode='lines', line=dict(color='#667eea', width=3),
            name='Median'
        ))
        fig_mc.update_layout(
            title=f"Monte Carlo ({mc_scenarios} scenarios, {projection_days} days)",
            xaxis_title="Date", yaxis_title="Portfolio Value (₹)",
            margin=dict(l=10,r=10,t=50,b=10),
            template=tpl
        )
        st.plotly_chart(fig_mc, use_container_width=True)

        final_vals = results[-1, :]
        final_mean = final_vals.mean()
        final_median = np.median(final_vals)
        final_std = final_vals.std()
        final_min = final_vals.min()
        final_max = final_vals.max()
        var_percentile = 100 - confidence_level
        value_at_risk = np.percentile(total_value - final_vals, var_percentile)
        cvar_mask = (total_value - final_vals) >= value_at_risk
        conditional_var = (total_value - final_vals)[cvar_mask].mean() if np.any(cvar_mask) else value_at_risk
        prob_gain = np.mean(final_vals > total_value) * 100

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Initial Value", f"₹{total_value:,.0f}")
            st.metric("Median Final", f"₹{final_median:,.0f}", f"{(final_median/total_value -1):+.2%}")
            st.metric("Mean Final", f"₹{final_mean:,.0f}", f"{(final_mean/total_value -1):+.2%}")
        with c2:
            st.metric("Std Dev", f"₹{final_std:,.0f}")
            st.metric("Min Final", f"₹{final_min:,.0f}", f"{(final_min/total_value -1):+.2%}")
            st.metric("Max Final", f"₹{final_max:,.0f}", f"{(final_max/total_value -1):+.2%}")
        with c3:
            st.metric("Prob Gain", f"{prob_gain:.1f}%")
            st.metric(f"VaR ({confidence_level}%)", f"₹{value_at_risk:,.0f}",
                      f"{value_at_risk/total_value*100:.2f}%")
            st.metric(f"CVaR ({confidence_level}%)", f"₹{conditional_var:,.0f}",
                      f"{conditional_var/total_value*100:.2f}%")

        fig_hist = px.histogram(final_vals, nbins=40, title="Final Value Distribution",
                                labels={'value':'Final Portfolio Value (₹)'}, template=tpl)
        fig_hist.add_vline(x=total_value, line_width=2, line_dash="dash", line_color="white" if ss.dark_mode else "black",
                           annotation_text="Initial", annotation_position="top left")
        fig_hist.add_vline(x=final_median, line_width=2, line_dash="dash", line_color="red",
                           annotation_text="Median", annotation_position="top left")
        fig_hist.add_vline(x=final_mean, line_width=2, line_dash="dash", line_color="green",
                           annotation_text="Mean", annotation_position="top right")
        st.plotly_chart(fig_hist, use_container_width=True)

# =========================================================
# AI RECOMMENDATIONS
# =========================================================
if ss.generate_analysis:
    st.subheader("🤖 AI-Powered Recommendations")
    recs = generate_ai_recommendations(portfolio_data, list(portfolio_data.keys()))
    for i, rec in enumerate(recs):
        with st.expander(f"{i+1}. {rec['action']} - {rec['domain']}", expanded=(i == 0)):
            lcol, rcol = st.columns([4,1])
            with lcol:
                st.write(f"**{rec['description']}**")
                st.write(f"*Expected Impact:* {rec['impact']}")
                st.write("**Reasoning:**")
                for reason in rec['reasoning']:
                    st.write(f"• {reason}")
            with rcol:
                st.metric("Confidence", f"{rec['confidence']:.1f}%")
                st.button("Apply (demo)", key=f"apply_{i}", disabled=True)
    ss.generate_analysis = False

# =========================================================
# FOOTER
# =========================================================
st.markdown("---")
st.caption("CashLagao - Integrated Holdings Frontend + Advanced Analytics (Illustrative only; not investment advice).")
