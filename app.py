import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Konfigurera Google Sheets API
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(
    st.secrets["GOOGLE_CREDENTIALS"], scopes=scope
)
gc = gspread.authorize(credentials)

# Sheet-ID och namn
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

st.title("📈 Automatisk aktieanalys")

# Funktion för att läsa datan från kalkylarket som DataFrame
def load_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# Funktion för att lägga till ny ticker
def add_ticker(ticker):
    tickers = worksheet.col_values(1)[1:]  # Exkludera header
    if ticker.upper() not in tickers:
        worksheet.append_row([ticker.upper()])
        st.success(f"✅ {ticker.upper()} har lagts till!")
    else:
        st.warning("⚠️ Ticker finns redan.")

# Funktion för att hämta data från yfinance
def fetch_financials(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        currency = info.get("currency", "N/A")
        market_cap = info.get("marketCap", None)
        shares_outstanding = info.get("sharesOutstanding", None)

        if market_cap is None or shares_outstanding is None:
            return None

        ps_ratio = market_cap / (info.get("totalRevenue", 1))
        price = info.get("currentPrice", None)
        name = info.get("shortName", "Okänt")

        return {
            "Bolag": name,
            "Ticker": ticker.upper(),
            "Kurs": price,
            "Valuta": currency,
            "P/S TTM": round(ps_ratio, 2),
        }
    except Exception as e:
        st.error(f"Fel vid hämtning av data för {ticker}: {e}")
        return None

# Formulär för att lägga till ticker
with st.form("add_form"):
    ticker_input = st.text_input("Lägg till en ticker (t.ex. AAPL)", "")
    submitted = st.form_submit_button("Lägg till")
    if submitted and ticker_input.strip():
        add_ticker(ticker_input.strip())

# Läs tickers och visa analys
df = load_data()
if df.empty:
    st.info("Ingen ticker tillagd ännu.")
else:
    st.subheader("🔍 Analys av bolag")
    for _, row in df.iterrows():
        ticker = row.get("Ticker") or row.get("ticker") or row.get("TICKER")
        if not ticker:
            continue
        data = fetch_financials(ticker)
        if data:
            st.markdown(f"### {data['Bolag']} ({data['Ticker']})")
            st.write(f"📌 Kurs: {data['Kurs']} {data['Valuta']}")
            st.write(f"📊 P/S TTM: {data['P/S TTM']}")
            st.divider()
        else:
            st.warning(f"Kunde inte hämta data för {ticker}")
