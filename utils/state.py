import streamlit as st
from models.risk_model import StockInvestmentModel

RISK_WEIGHTS_KEY = "risk_weights_custom"
CONF_WEIGHTS_KEY = "confidence_weights_custom"

def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

def get_model_weights():
    if RISK_WEIGHTS_KEY not in st.session_state:
        st.session_state[RISK_WEIGHTS_KEY] = StockInvestmentModel.DEFAULT_WEIGHTS.copy()
    return st.session_state[RISK_WEIGHTS_KEY]

def set_model_weights(weights: dict):
    st.session_state[RISK_WEIGHTS_KEY] = weights

def get_confidence_weights():
    if CONF_WEIGHTS_KEY not in st.session_state:
        st.session_state[CONF_WEIGHTS_KEY] = StockInvestmentModel.DEFAULT_CONFIDENCE_WEIGHTS.copy()
    return st.session_state[CONF_WEIGHTS_KEY]

def set_confidence_weights(weights: dict):
    st.session_state[CONF_WEIGHTS_KEY] = weights