# -*- coding: utf-8 -*-

import streamlit as st
import yfinance as yf
import pandas as pd

# --- CORE ANALYTICS ENGINE ---
def calculate_comprehensive_metrics(ticker_symbol: str):
    try:
        ticker = yf.Ticker(ticker_symbol.strip().upper())
        df = ticker.history(period="6mo")

        if df.empty:
            return None

        # 1. Current Session Metrics
        current_vol = int(df['Volume'].iloc[-1])
        
        # Isolate history up to yesterday (excludes live session)
        df_hist = df.iloc[:-1]
        available_days = len(df_hist)

        # 2. Today's Base Lookbacks (Includes yesterday's volume)
        adv_5  = round(df_hist['Volume'].tail(5).mean())  if available_days >= 5  else "N/A"
        adv_22 = round(df_hist['Volume'].tail(22).mean()) if available_days >= 22 else "N/A"
        adv_44 = round(df_hist['Volume'].tail(44).mean()) if available_days >= 44 else "N/A"
        adv_66 = round(df_hist['Volume'].tail(66).mean()) if available_days >= 66 else "N/A"
        
        pov_15_curr = round(adv_5 * 0.15)  if adv_5  != "N/A" else "N/A"
        pov_22_curr = round(adv_22 * 0.15) if adv_22 != "N/A" else "N/A"
        pov_44_curr = round(adv_44 * 0.15) if adv_44 != "N/A" else "N/A"
        pov_66_curr = round(adv_66 * 0.15) if adv_66 != "N/A" else "N/A"

        # 3. Previous Day's Lookback (Excludes yesterday's volume)
        if available_days >= 6:
            df_prev_day = df_hist.iloc[:-1] 
            adv_5_prev = round(df_prev_day['Volume'].tail(5).mean())
            pov_15_prev = round(adv_5_prev * 0.15)
            
            if pov_15_prev > 0 and pov_15_curr != "N/A":
                dtd_change_pct = ((pov_15_curr - pov_15_prev) / pov_15_prev) * 100
                dtd_str = f"{dtd_change_pct:+.2f}%"
            else:
                dtd_str = "0.00%"
        else:
            adv_5_prev = "N/A"
            pov_15_prev = "N/A"
            dtd_str = "N/A"

        # 4. Extract available days for the chart breakdown (max 6 days)
        past_days = df_hist.tail(min(6, available_days)).copy()
        historical_volume_list = []
        if not past_days.empty:
            past_days['Date'] = past_days.index.strftime('%Y-%m-%d')
            historical_volume_list = past_days[['Date', 'Volume']].to_dict(orient='records')

        # Structure final matrix output rows with the merged "Prev 5D ADV" column
        matrix_rows = [
            {
                "Symbol": ticker_symbol.strip().upper(),
                "Metric Type": "Standard Lookback ADV",
                "Current Session Vol": current_vol,
                "5D Horizon": adv_5,
                "Prev 5D ADV": adv_5_prev,
                "1M ADV (22D)": adv_22,
                "2M ADV (44D)": adv_44,
                "3M ADV (66D)": adv_66,
                "DtD Change (%)": ""  
            },
            {
                "Symbol": ticker_symbol.strip().upper(),
                "Metric Type": "15% ADV Execution Limit",
                "Current Session Vol": "",
                "5D Horizon": pov_15_curr,
                "Prev 5D ADV": pov_15_prev,
                "1M ADV (22D)": pov_22_curr,
                "2M ADV (44D)": pov_44_curr,
                "3M ADV (66D)": pov_66_curr,
                "DtD Change (%)": dtd_str
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
st.markdown("Type a ticker symbol to check true trading-day lookback metrics, ADV execution tiers, and DtD velocity changes.")

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
            st.session_state.history_data = pd.DataFrame(res["historical_volume"]) if res["historical_volume"] else None
        else:
            st.error(f"Could not retrieve data for ticker: {user_input}. Please confirm symbol syntax is valid.")
    else:
        st.error("Please enter a valid ticker symbol.")

# --- DISPLAY RENDER ENGINE ---
if st.session_state.matrix_data is not None:
    
    # 1. Main Overview Table Grid
    st.subheader("📋 Output Analytics Matrix")
    df_matrix = st.session_state.matrix_data
    
    # FORCED NUMERIC FORMATTING
    format_dict = {}
    for col in df_matrix.columns:
        if "Horizon" in col or "ADV" in col or "Vol" in col or "Benchmark" in col:
            format_dict[col] = lambda x: (
                f"{float(x):,.0f}" if (str(x).replace('.','',1).isdigit() or isinstance(x, (int, float))) 
                else str(x)
            )
            
    st.dataframe(df_matrix.style.format(format_dict), use_container_width=True, hide_index=True)

    st.markdown("---")

    # 2. Historical Volume Block
    st.subheader("📆 Historical Completed Trading Days Volume Breakdown")
    
    if st.session_state.history_data is not None and not st.session_state.history_data.empty:
        df_hist_display = st.session_state.history_data
        col_table, col_chart = st.columns([2, 3])

        with col_table:
            st.dataframe(
                df_hist_display.style.format({"Volume": "{:,.0f}"}),
                use_container_width=True,
                hide_index=True
            )

        with col_chart:
            st.bar_chart(
                data=df_hist_display,
                x="Date",
                y="Volume",
                use_container_width=True
            )
    else:
        st.info("No prior completed trading day volume available to graph yet for this asset.")
