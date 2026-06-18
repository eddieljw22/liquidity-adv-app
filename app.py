# -*- coding: utf-8 -*-

import streamlit as st
import yfinance as yf
import pandas as pd

# --- CORE ANALYTICS FUNCTION ---
def calculate_adv_metrics(ticker_symbol: str):
    try:
        ticker = yf.Ticker(ticker_symbol.strip().upper())
        df = ticker.history(period="6mo")

        if df.empty:
            return None

        current_date = df.index[-1].strftime('%Y-%m-%d')
        current_vol = int(df['Volume'].iloc[-1])
        df_hist = df.iloc[:-1] # Exclude live day for historical ADV calculations

        adv_5  = df_hist['Volume'].tail(5).mean()  if len(df_hist) >= 5  else None
        adv_30 = df_hist['Volume'].tail(30).mean() if len(df_hist) >= 30 else None
        adv_60 = df_hist['Volume'].tail(60).mean() if len(df_hist) >= 60 else None
        adv_90 = df_hist['Volume'].tail(90).mean() if len(df_hist) >= 90 else None
        pov_15 = adv_5 * 0.15 if adv_5 is not None else None

        return {
            "Symbol": ticker_symbol.strip().upper(),
            "Current Session Vol": current_vol,
            "5D ADV": round(adv_5) if adv_5 else "N/A",
            "15% of 5D ADV (POV)": round(pov_15) if pov_15 else "N/A",
            "30D ADV": round(adv_30) if adv_30 else "N/A",
            "60D ADV": round(adv_60) if adv_60 else "N/A",
            "90D ADV": round(adv_90) if adv_90 else "N/A"
        }
    except Exception:
        return None

# --- STREAMLIT USER INTERFACE ---
st.set_page_config(page_title="Liquidity Analytics Dashboard", layout="wide")

st.title("📊 Institutional Liquidity & ADV Model")
st.markdown("Type a ticker symbol (or multiple tickers separated by commas) to check on-screen lookback metrics.")

# Persistent data state
if 'calculated_data' not in st.session_state:
    st.session_state.calculated_data = None

# Using a st.form isolates the button state conflicts perfectly
with st.form(key="liquidity_form"):
    user_input = st.text_input("Enter Ticker(s) (e.g., CPOP, QMMM, LU):", value="CPOP")
    submit_button = st.form_submit_button("🚀 Run Liquidity Model", use_container_width=True, type="primary")

# Sidebar handle for cleanly resetting the viewport matrix
if st.sidebar.button("Reset Matrix Screen", use_container_width=True):
    st.session_state.calculated_data = None
    st.rerun()

if submit_button:
    if user_input:
        tickers = [t.strip() for t in user_input.split(",") if t.strip()]
        results_list = []
        
        for ticker in tickers:
            res = calculate_adv_metrics(ticker)
            if res: 
                results_list.append(res)
            else: 
                st.warning(f"Could not retrieve data for ticker: {ticker}")
        
        if results_list:
            st.session_state.calculated_data = pd.DataFrame(results_list)
    else:
        st.error("Please enter at least one ticker symbol.")

# --- ON-SCREEN DATA GRID ---
if st.session_state.calculated_data is not None:
    df_results = st.session_state.calculated_data

    st.subheader("📋 Output Analytics Matrix")
    
    # Clean numeric formatting for commas
    format_dict = {col: "{:,.0f}" for col in df_results.columns if "ADV" in col or "Vol" in col}
    
    st.dataframe(
        df_results.style.format(format_dict), 
        use_container_width=True, 
        hide_index=True
    )
