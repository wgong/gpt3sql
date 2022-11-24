# An app to show Google stocks.
# see https://streamlit-example-app-streamlit-codex-streamlit-app-wfi4of.streamlitapp.com/
# This app is created by GPT-3 Codex by providing prompt (line 6-11). 
# The rest is completed by GPT-3 with minor revision

"""
App which shows price for Google Stock from 09/11/2019 to 09/15/2021
"""

import streamlit as st
import yfinance as yf

import pandas as pd
import plotly.express as px

st.title("Google Stock Price")

tickerSymbol = "GOOGL"
tickerData = yf.Ticker(tickerSymbol)
data = tickerData.history(period='1d', start='2019-11-09', end='2021-09-15')

# Show the data as a table
st.dataframe(data)

# Show the close price
st.line_chart(data['Close'])


# Show the data as a time series
st.area_chart(data['Volume'])
