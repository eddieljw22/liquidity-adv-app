# -*- coding: utf-8 -*-

import streamlit as st
import yfinance as yf
import pandas as pd

# --- CORE ANALYTICS ENGINE ---
def calculate_comprehensive_metrics(ticker_symbol: str):
    try:
        ticker = yf.Ticker(ticker_symbol.strip().upper())
        df = ticker.history(period="6mo")

        if df.empty or len(df) < 15:
            return None

        # 1. Current Session Metrics
        current_vol = int(df['Volume'].iloc[-1])
        
        # Isolate history (exclude live session)
        df_hist = df.iloc[:-1]

        # 2. Base Lookbacks (Current Week Snapshots)
        adv_5  = df_hist['Volume'].tail(5).mean()
        adv_30 = df_hist['Volume'].tail(30).mean()
        adv_60 = df_hist['Volume'].tail(60).mean()
        adv_90 = df_hist['Volume'].tail(90).mean()
        pov_15_curr = adv_5 * 0.15

        # 3. Previous Week Lookback (Shifted back 5 trading days to calculate WoW change)
        df_prev_week = df_hist.iloc[:-5]
        adv_5_prev = df_prev_week['Volume'].tail(5).mean() if len(df_prev_week) >= 5 else None
        pov_15_prev = adv_5_prev * 0.15 if adv_5_prev else None

        # Calculate percentage difference between previous week's POV and current POV
        if pov_15_prev and pov_15_prev > 0:
            wow_change_pct = ((pov_15_curr - pov_15_prev) / pov_15_prev) * 100
        else:
            wow_change_pct = 0.0

        # 4. Extract Last 6 Completed Trading Days for the Breakdown
        past_6_days = df_hist.tail(6).copy()
        past_6_days['Date'] = past_6_days.index.strftime('%Y-%m-%d')
        historical_volume_list = past_6_days[['Date', 'Volume']].to_dict(orient='records')

        # Generate separate rows for standard Lookbacks vs. 15% POV Limits
        matrix_rows = [
            {
                "Symbol": ticker_symbol.strip().upper(),
                "Metric Type": "Standard Lookback ADV",
                "Current Session Vol": current_vol,
                "5D Horizon": round(adv_5) if adv_5 else None,
                "30D Horizon": round(adv_30) if adv_30 else None,
                "60D Horizon": round(adv_60) if adv_60 else None,
                "90D Horizon": round(adv_90) if adv_90 else None,
                "WoW Change (%)": ""  # Only applies to POV limits row
            },
            {
                "Symbol": ticker_symbol.strip().upper(),
                "Metric Type": "15% POV Execution Limit",
                "Current Session Vol": "",
                "5D Horizon": round(pov_15_curr) if pov_15_curr else None,
                "30D Horizon": round(adv_30 * 0.15) if adv_30 else None,
                "60D Horizon": round(adv_60 * 0.15) if adv_60 else None,
                "90D Horizon": round(adv_90 * 0.15) if adv_90 else None,
                "WoW Change (%)": f"{wow_change_pct:+.2f}%" if wow_change_pct else "0.00%"
            }
        ]

        return {
            "matrix_rows": matrix_rows,
            "historical_volume": historical_volume_list
        }
    except Exception:
        return None

# --- STREAMLIT USER INTERFACE ---
st.set_page_config(page_title="Liquidity Analytics Dashboard", layout="wide")

st.title("📊 Institutional Liquidity & ADV Model")
st.markdown("Type a ticker symbol to check on-screen lookback metrics, POV rows, and visual volume pacing trends.")

# Persistent state management
if 'matrix_data' not in st.session_state:
    st.session_state.matrix_data = None
if 'history_data' not in st.session_state:
    st.session_state.history_data = None

with st.form(key="liquidity_form"):
    user_input = st.text_input("Enter Ticker:", value="GDHG")
    submit_button = st.form_submit_button("🚀 Run Liquidity Model", use_container_width=True, type="primary")

if st.sidebar.button("Reset Matrix Screen", use_container_width=True):
    st.session_state.matrix_data = None
    st.session_state.history_data = None
    st.rerun()

if submit_button:
    if user_input:
        res = calculate_comprehensive_metrics(user_input)
        if res:
            st.session_state.matrix_data = pd.DataFrame(res["matrix_rows"])
            st.session_state.history_data = pd.DataFrame(res["historical_volume"])
        else:
            st.error(f"Could not retrieve data for ticker: {user_input}")
    else:
        st.error("Please enter a valid ticker symbol.")

# --- DISPLAY RENDER ENGINE ---
if st.session_state.matrix_data is not None:
    
    # 1. Main Overview Table Grid
    st.subheader("📋 Output Analytics Matrix")
    df_matrix = st.session_state.matrix_data
    
    # Apply standard comma grouping format to all standard volume columns
    format_dict = {}
    for col in df_matrix.columns:
        if "Horizon" in col or "Vol" in col:
            format_dict[col] = lambda x: f"{x:,.0f}" if isinstance(x, (int, float)) else str(x)
            
    st.dataframe(df_matrix.style.format(format_dict), use_container_width=True, hide_index=True)

    st.markdown("---")

    # 2. 6-Day Historical Volume Block
    st.subheader("📆 Past 6 Completed Trading Days Volume Breakdown")
    
    df_hist = st.session_state.history_data
    col_table, col_chart = st.columns([2, 3])

    with col_table:
        # Display the formatted summary table
        st.dataframe(
            df_hist.style.format({"Volume": "{:,.0f}"}),
            use_container_width=True,
            hide_index=True
        )

    with col_chart:
        # Generate the visual volume pacing column/bar chart
        st.bar_chart(
            data=df_hist,
            x="Date",
            y="Volume",
            use_container_width=True
        )
