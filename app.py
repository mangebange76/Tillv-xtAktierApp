import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# SIDHUVD
st.set_page_config(page_title="Tillväxtaktier", layout="wide")
st.title("📈 Automatisk analys av tillväxtaktier")

# GOOGLE SHEET-ID OCH NAMN PÅ ARK
SHEET_ID = "DIN_SHEET_ID_HÄR"  # byt ut detta med ID från din Google Sheets-länk
SHEET_NAME = "Blad1"

# GOOGLE AUTENTISERING
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_CREDENTIALS"], scopes=scope)
gc = gspread.authorize(credentials)
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

# LADDA DATA FRÅN GOOGLE SHEET
def load_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# SPARA NY TICKER
def save_ticker(ticker):
    worksheet.append_row([ticker])

# FUNKTION FÖR ATT HÄMTA AKTIEDATA OCH BERÄKNA P/S
def fetch_analysis(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.quarterly_financials
        if hist.empty or "Total Revenue" not in hist.index:
            return None
        
        # Rullande TTM (sista 4 kvartal)
        revenue_ttm = hist.loc["Total Revenue"].iloc[:4].sum()
        market_cap = info.get("marketCap")
        shares_outstanding = info.get("sharesOutstanding")
        currency = info.get("financialCurrency", "USD")
        current_price = info.get("currentPrice")

        if revenue_ttm and shares_outstanding and current_price:
            ps_ttm = market_cap / revenue_ttm if revenue_ttm else None
            return {
                "Ticker": ticker,
                "Omsättning TTM": round(revenue_ttm / 1e6, 2),
                "Börsvärde": round(market_cap / 1e6, 2) if market_cap else None,
                "P/S TTM": round(ps_ttm, 2) if ps_ttm else None,
                "Aktiekurs": round(current_price, 2),
                "Valuta": currency
            }
        return None
    except Exception as e:
        st.warning(f"Fel vid hämtning av data för {ticker}: {e}")
        return None

# ANVÄNDARGRÄNSSNITT – Lägg till ny ticker
with st.form("form"):
    new_ticker = st.text_input("Lägg till ticker (t.ex. AAPL):").upper()
    submitted = st.form_submit_button("Lägg till")
    if submitted and new_ticker:
        existing = load_data()
        if new_ticker not in existing["Ticker"].values:
            save_ticker(new_ticker)
            st.success(f"{new_ticker} tillagd!")
        else:
            st.info(f"{new_ticker} finns redan i listan.")

# LADDA BOLAG FRÅN SHEET
df = load_data()

# HÄMTA OCH VISA DATA
results = []
for ticker in df["Ticker"]:
    result = fetch_analysis(ticker)
    if result:
        results.append(result)

if results:
    df_result = pd.DataFrame(results)
    st.subheader("🔍 Analysresultat")
    st.dataframe(df_result)
else:
    st.info("Ingen data att visa ännu.")
