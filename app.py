import streamlit as st
import json
import yfinance as yf
import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# Autentisering mot Google Sheets
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)

# Google Sheet inställningar
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"

# Ladda arket
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

# Läs in existerande data från arket
def load_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# Spara ny ticker till arket
def save_ticker(ticker):
    worksheet.append_row([ticker])

# Hämtar och beräknar data för ett bolag
def fetch_and_calculate(ticker, tillväxt_2027):
    try:
        ticker_data = yf.Ticker(ticker)
        info = ticker_data.info

        namn = info.get("longName", "")
        nuvarande_kurs = info.get("currentPrice", None)
        valuta = info.get("currency", "USD")
        market_cap = info.get("marketCap", None)
        shares_outstanding = info.get("sharesOutstanding", None)
        revenue_ttm = info.get("totalRevenue", None)

        if None in (nuvarande_kurs, market_cap, shares_outstanding, revenue_ttm):
            return {"Ticker": ticker, "Namn": namn, "Status": "❌ Data saknas"}

        ps_ttm = market_cap / revenue_ttm
        tillväxtfaktor = 1 + tillväxt_2027 / 100
        uppskattad_omsättning = revenue_ttm * tillväxtfaktor
        målkurs = (uppskattad_omsättning / shares_outstanding) * ps_ttm
        undervärdering = ((målkurs - nuvarande_kurs) / nuvarande_kurs) * 100

        return {
            "Ticker": ticker,
            "Namn": namn,
            "Valuta": valuta,
            "Nuvarande kurs": round(nuvarande_kurs, 2),
            "P/S TTM": round(ps_ttm, 2),
            "Uppskattad omsättning 2027": round(uppskattad_omsättning, 0),
            "Målkurs 2027": round(målkurs, 2),
            "Undervärdering (%)": round(undervärdering, 1),
            "Status": "✅"
        }

    except Exception as e:
        return {"Ticker": ticker, "Namn": "", "Status": f"❌ Fel: {str(e)}"}

# --- Streamlit-gränssnitt ---

st.title("📈 Tillväxtaktier – automatisk analys")

# Inmatning av ny ticker
with st.form("add_ticker"):
    new_ticker = st.text_input("Lägg till en ny ticker (t.ex. AAPL, MSFT, EVO):")
    tillväxt_2027 = st.number_input("Förväntad tillväxt % till 2027", value=20)
    submitted = st.form_submit_button("Analysera och spara")
    if submitted and new_ticker:
        save_ticker(new_ticker.upper())
        st.success(f"{new_ticker.upper()} tillagd!")

# Läs tickers från arket
tickers_df = load_data()
tickers_list = tickers_df.iloc[:, 0].tolist() if not tickers_df.empty else []

# Visa resultat för alla tickers
if tickers_list:
    results = []
    for t in tickers_list:
        data = fetch_and_calculate(t, tillväxt_2027)
        results.append(data)

    df_result = pd.DataFrame(results)
    st.dataframe(df_result)

else:
    st.info("Ingen ticker inlagd än. Lägg till en ovan.")
