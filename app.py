import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# Autentisering mot Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

# Öppna Google Sheet
SPREADSHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
sheet = gc.open_by_key(SPREADSHEET_ID).sheet1

# Säkerställ att rubriker finns
HEADERS = ["Ticker", "Namn", "Nuvarande kurs", "Valuta", "Omsättning TTM", "P/S TTM", "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027", "Omsättning 2027", "Målkurs 2027"]
if sheet.row_values(1) != HEADERS:
    sheet.insert_row(HEADERS, 1)

def fetch_data(ticker):
    try:
        t = yf.Ticker(ticker)
        info = t.info
        hist = t.quarterly_financials
        if hist.empty:
            return None

        latest_price = info.get("currentPrice")
        currency = info.get("financialCurrency", "USD")
        name = info.get("shortName", ticker)
        shares = info.get("sharesOutstanding", None)

        if not shares or not latest_price:
            return None

        # Hämta TTM Revenue
        rev_quarters = t.quarterly_financials.loc["Total Revenue"]
        ttm_revenue = rev_quarters[:4].sum()

        if ttm_revenue == 0:
            return None

        market_cap = latest_price * shares
        ps_ttm = market_cap / ttm_revenue

        return {
            "Ticker": ticker,
            "Namn": name,
            "Nuvarande kurs": latest_price,
            "Valuta": currency,
            "Omsättning TTM": ttm_revenue,
            "P/S TTM": ps_ttm
        }
    except Exception as e:
        st.error(f"Fel vid hämtning av data för {ticker}: {e}")
        return None

def calculate_2027_revenue(ttm, g1, g2, g3):
    return ttm * (1 + g1 / 100) * (1 + g2 / 100) * (1 + g3 / 100)

def calculate_target_price(rev_2027, shares, ps_ttm):
    return (rev_2027 / shares) * ps_ttm

# UI
st.title("📈 Aktieanalys med målkurs 2027")
ticker_input = st.text_input("Ange ticker (t.ex. AAPL)")

if st.button("Lägg till bolag") and ticker_input:
    ticker = ticker_input.strip().upper()
    data = fetch_data(ticker)

    if data:
        tillv_2025 = st.number_input("Förväntad tillväxt 2025 (%)", value=10.0, key="tillv1")
        tillv_2026 = st.number_input("Förväntad tillväxt 2026 (%)", value=10.0, key="tillv2")
        tillv_2027 = st.number_input("Förväntad tillväxt 2027 (%)", value=10.0, key="tillv3")

        rev_2027 = calculate_2027_revenue(data["Omsättning TTM"], tillv_2025, tillv_2026, tillv_2027)
        shares = yf.Ticker(ticker).info.get("sharesOutstanding", None)

        if shares:
            target_price = calculate_target_price(rev_2027, shares, data["P/S TTM"])
            row = [
                data["Ticker"], data["Namn"], data["Nuvarande kurs"], data["Valuta"],
                data["Omsättning TTM"], data["P/S TTM"], tillv_2025, tillv_2026, tillv_2027,
                rev_2027, target_price
            ]
            sheet.append_row(row)
            st.success(f"{data['Namn']} tillagd med målkurs {target_price:.2f} {data['Valuta']}")
        else:
            st.error("Antal aktier saknas – kan inte beräkna målkurs.")
    else:
        st.error("Kunde inte hämta finansiell data.")

# Visa nuvarande data
st.subheader("🔍 Analysdata")
df = pd.DataFrame(sheet.get_all_records())
if not df.empty:
    st.dataframe(df)
