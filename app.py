import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 🛡️ Autentisering mot Google Sheets via secrets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_CREDENTIALS"], scopes=scope)
client = gspread.authorize(credentials)

# 🗂️ Ange ditt Google Sheet-ID
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
worksheet = client.open_by_key(SHEET_ID).sheet1

# 📥 Läs in befintlig data från Google Sheets
@st.cache_data(ttl=600)
def load_data():
    records = worksheet.get_all_records()
    return pd.DataFrame(records)

# 📤 Spara ny rad i Google Sheets
def save_row(row_dict):
    worksheet.append_row(list(row_dict.values()))

# 🔄 Uppdatera en befintlig rad (baserat på ticker)
def update_row(ticker, updated_row):
    records = worksheet.get_all_records()
    for i, row in enumerate(records):
        if row["Ticker"] == ticker:
            worksheet.update(f"A{i+2}", [list(updated_row.values())])
            break

# 🔍 Hämta finansiell data via yfinance
def fetch_financials(ticker):
    ticker_obj = yf.Ticker(ticker)
    info = ticker_obj.info
    currency = info.get("currency", "USD")
    price = info.get("currentPrice") or info.get("regularMarketPrice")
    shares = info.get("sharesOutstanding")
    market_cap = info.get("marketCap")

    # Hämta kvartalsvis omsättning (senaste 4 kvartal)
    try:
        revenue_quarterly = ticker_obj.quarterly_income_stmt.loc["Total Revenue"]
        revenue_ttm = revenue_quarterly.iloc[:4].sum()
    except:
        revenue_ttm = None

    return {
        "Ticker": ticker.upper(),
        "Price": price,
        "Shares": shares,
        "Market Cap": market_cap,
        "Revenue TTM": revenue_ttm,
        "Currency": currency
    }

# 📈 Beräkna P/S TTM
def calculate_ps_ttm(market_cap, revenue_ttm):
    try:
        return round(market_cap / revenue_ttm, 2)
    except:
        return None

# 🚀 Streamlit UI
st.title("📊 Automatisk aktieanalys – P/S TTM")

ticker = st.text_input("Ange ticker (t.ex. AAPL):")
if st.button("Hämta och spara data"):
    if not ticker:
        st.warning("Ange en giltig ticker först.")
    else:
        with st.spinner("Hämtar data..."):
            data = fetch_financials(ticker)
            if data["Price"] and data["Revenue TTM"]:
                ps_ttm = calculate_ps_ttm(data["Market Cap"], data["Revenue TTM"])
                data["P/S TTM"] = ps_ttm
                save_row(data)
                st.success(f"Data sparad för {ticker.upper()}")
            else:
                st.error("Kunde inte hämta komplett data. Kontrollera att tickern är korrekt och listad.")

# 🗃️ Visa sparade bolag
df = load_data()
if not df.empty:
    df_sorted = df.sort_values(by="P/S TTM", ascending=True)
    st.subheader("📋 Sparade analyser")
    st.dataframe(df_sorted.reset_index(drop=True))

    # Bläddringsfunktion
    tickers = df_sorted["Ticker"].tolist()
    selected = st.selectbox("Välj bolag att visa detaljer för", tickers)
    selected_row = df_sorted[df_sorted["Ticker"] == selected]
    st.write("📌 Detaljerad data:")
    st.dataframe(selected_row)
