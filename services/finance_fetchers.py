import yfinance as yf
import streamlit as st

@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_balance_sheet(ticker_symbol: str):
    return yf.Ticker(ticker_symbol).balance_sheet

@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_quarterly_financials(ticker_symbol: str):
    return yf.Ticker(ticker_symbol).quarterly_financials

@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_history(ticker_symbol: str, period: str):
    return yf.Ticker(ticker_symbol).history(period=period)

@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_index_history(index_symbol: str, period: str):
    return yf.Ticker(index_symbol).history(period=period)

class FinanceDataFetcher:
    @staticmethod
    def debt_to_equity(ticker_symbol: str):
        bs = _fetch_balance_sheet(ticker_symbol)
        if bs is None or bs.empty:
            return None, "No balance sheet data."
        try:
            total_liabilities = bs.loc['Total Liabilities Net Minority Interest'].iloc[0]
            total_equity = bs.loc['Total Equity Gross Minority Interest'].iloc[0]
        except KeyError:
            return None, "Required balance sheet fields missing."
        if total_equity in (0, None):
            return None, "Equity invalid or zero."
        return float(total_liabilities / total_equity), None

    @staticmethod
    def earnings_volatility_extended(ticker_symbol: str):
        qfin = _fetch_quarterly_financials(ticker_symbol)
        if qfin is None or qfin.empty:
            return None, "Quarterly financials empty.", 0, None
        df_t = qfin.T
        if 'Net Income' not in df_t.columns:
            return None, "Net Income column missing.", 0, df_t
        earnings = df_t['Net Income'].dropna()
        quarters_count = len(earnings)
        if earnings.empty:
            return None, "No Net Income values.", 0, df_t
        mean_val = earnings.mean()
        if mean_val == 0:
            return None, "Mean earnings = 0.", quarters_count, df_t
        std_dev = earnings.std(ddof=0)
        vol = float(std_dev / abs(mean_val))
        return vol, None, quarters_count, df_t

    @staticmethod
    def historical_returns(ticker_symbol: str, period="1y"):
        hist = _fetch_history(ticker_symbol, period)
        if hist is None or hist.empty:
            return None, "No historical price data."
        closes = hist['Close'].dropna()
        returns = closes.pct_change().dropna()
        if returns.empty:
            return None, "Insufficient return series."
        return returns, None

def get_index_returns(index_symbol: str, period="1y"):
    hist = _fetch_index_history(index_symbol, period)
    if hist is None or hist.empty:
        return None, "No index history."
    closes = hist['Close'].dropna()
    rets = closes.pct_change().dropna()
    if rets.empty:
        return None, "Insufficient index returns."
    return rets, None