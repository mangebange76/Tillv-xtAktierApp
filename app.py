import streamlit as st
import yfinance as yf
import gspread
import json
from google.oauth2.service_account import Credentials
import pandas as pd

# --- Autentisering mot Google Sheets ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

# --- Ange ditt Sheet-ID (från URL) ---
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"  # ändra till ditt om du använder ett annat

# --- Öppna kalkylbladet och hämta datan ---
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.sheet1

# --- Ladda data som pandas DataFrame ---
data = worksheet.get_all_records()
df = pd.DataFrame(data)

# --- Visa datan i Streamlit ---
st.title("📊 Tillväxtaktier – Automatisk analys")
st.write("🔍 Data från Google Sheets:")
st.dataframe(df)

# --- Lägg till ny aktie för analys ---
st.subheader("➕ Lägg till nytt bolag")
ticker = st.text_input("Ticker-symbol (t.ex. AAPL, MSFT)")
tillv_2027 = st.number_input("Förväntad tillväxt 2027 (%)", step=1)

if st.button("Analysera och lägg till"):
    if ticker:
        try:
            aktie = yf.Ticker(ticker)
            info = aktie.info
            namn = info.get("shortName", "Okänt")
            valuta = info.get("financialCurrency", "USD")
            marketcap = info.get("marketCap", None)
            sales_ttm = info.get("totalRevenue", None)
            shares = marketcap / info["currentPrice"] if marketcap and info.get("currentPrice") else None

            if None in (marketcap, sales_ttm, shares):
                st.error("Kunde inte hämta tillräcklig finansiell data.")
            else:
                ps_ttm = marketcap / sales_ttm
                tillv_multiplikator = (1 + tillv_2027 / 100)
                forecast_sales_2027 = sales_ttm * tillv_multiplikator**3
                target_price = (forecast_sales_2027 / shares) * ps_ttm

                ny_rad = {
                    "Ticker": ticker.upper(),
                    "Bolag": namn,
                    "Valuta": valuta,
                    "P/S TTM": round(ps_ttm, 2),
                    "Omsättning TTM": int(sales_ttm),
                    "Antal aktier": int(shares),
                    "Tillväxt 2027 (%)": tillv_2027,
                    "Målkurs 2027": round(target_price, 2)
                }

                worksheet.append_row(list(ny_rad.values()))
                st.success(f"{namn} har lagts till i kalkylarket!")
        except Exception as e:
            st.error(f"Något gick fel: {e}")
    else:
        st.warning("Ange en ticker-symbol först.")
