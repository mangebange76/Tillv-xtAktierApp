import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# Autentisering till Google Sheets via Streamlit secrets
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

# Ange ditt Google Sheet ID och namn på arket
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

# Funktion för att ladda data från Google Sheet
def load_data():
    try:
        headers = worksheet.row_values(1)
        expected_headers = ["ticker", "growth_2025", "growth_2026", "growth_2027"]
        if headers != expected_headers:
            worksheet.update("A1:D1", [expected_headers])
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Fel vid laddning av data: {e}")
        return pd.DataFrame(columns=["ticker", "growth_2025", "growth_2026", "growth_2027"])

# Funktion för att spara ny ticker och tillväxt
def save_data(ticker, g25, g26, g27):
    worksheet.append_row([ticker, g25, g26, g27])

# Funktion för att hämta finansiell data och räkna ut målkurs
def fetch_data(ticker, g2025, g2026, g2027):
    try:
        ticker_data = yf.Ticker(ticker)
        info = ticker_data.info
        currency = info.get("currency", "USD")
        shares = info.get("sharesOutstanding")
        market_cap = info.get("marketCap")

        if not all([shares, market_cap]):
            return None

        ttm_sales = market_cap / info["priceToSalesTrailing12Months"]
        sales_2025 = ttm_sales * (1 + g2025 / 100)
        sales_2026 = sales_2025 * (1 + g2026 / 100)
        sales_2027 = sales_2026 * (1 + g2027 / 100)

        ps_ttm = info["priceToSalesTrailing12Months"]
        price_target = (sales_2027 / shares) * ps_ttm

        return {
            "Bolag": info.get("shortName", ticker),
            "Ticker": ticker,
            "Valuta": currency,
            "Nuvarande kurs": info.get("currentPrice"),
            "Målkurs 2027": round(price_target, 2),
            "Uppside (%)": round(((price_target / info.get("currentPrice")) - 1) * 100, 2) if info.get("currentPrice") else None
        }
    except Exception as e:
        st.error(f"Kunde inte hämta data för {ticker}: {e}")
        return None

# Gränssnitt i Streamlit
st.title("📈 Tillväxtaktier – Målkurs 2027")

with st.form("add_ticker"):
    ticker = st.text_input("Ange ticker (t.ex. AAPL)").upper()
    g2025 = st.number_input("Förväntad tillväxt 2025 (%)", value=10)
    g2026 = st.number_input("Förväntad tillväxt 2026 (%)", value=10)
    g2027 = st.number_input("Förväntad tillväxt 2027 (%)", value=10)
    submitted = st.form_submit_button("Lägg till")

    if submitted and ticker:
        save_data(ticker, g2025, g2026, g2027)
        st.success(f"{ticker} tillagd!")

tickers_df = load_data()

if not tickers_df.empty:
    results = []
    for _, row in tickers_df.iterrows():
        result = fetch_data(row["ticker"], row["growth_2025"], row["growth_2026"], row["growth_2027"])
        if result:
            results.append(result)

    if results:
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values(by="Uppside (%)", ascending=False)
        st.subheader("🔍 Analysresultat")
        st.dataframe(df_results, use_container_width=True)
    else:
        st.info("Inga analyser kunde visas – kontrollera tickers eller försök igen.")
else:
    st.info("Inga tickers har lagts till än.")
