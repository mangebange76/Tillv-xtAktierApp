import streamlit as st
import yfinance as yf
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="Tillväxtaktier", layout="centered")

# 🟦 Autentisering mot Google Sheets via st.secrets
scope = ["https://www.googleapis.com/auth/spreadsheets"]
credentials = Credentials.from_service_account_info(
    st.secrets["GOOGLE_CREDENTIALS"], scopes=scope
)
gc = gspread.authorize(credentials)

# 🟨 Ange ditt kalkylark och ark-namn här
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Sheet1"  # <-- ändra till vad ditt ark verkligen heter om det inte är "Sheet1"

# Öppna Google Sheet och worksheet
sh = gc.open_by_key(SHEET_ID)
worksheet = sh.worksheet(SHEET_NAME)

# 🟩 Funktion för att läsa data från Google Sheet
def read_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

# 🟧 Funktion för att lägga till ny ticker
def add_ticker(ticker, tillvaxt_2027):
    df = read_data()
    if ticker in df["Ticker"].values:
        st.warning("Ticker finns redan.")
        return
    worksheet.append_row([ticker, tillvaxt_2027])

# 🟥 Hämta P/S TTM och målkurs
def fetch_and_calculate(ticker, tillvaxt_2027):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        price = info.get("currentPrice")
        currency = info.get("currency", "")
        shares = info.get("sharesOutstanding")
        quarterly = stock.quarterly_financials
        if quarterly.empty:
            return None
        omsattningar = quarterly.loc["Total Revenue"].values[:4]
        oms_ttm = sum(omsattningar)
        ps_ttm = (price * shares) / oms_ttm if oms_ttm else None
        tillvaxtfaktor = 1 + tillvaxt_2027 / 100
        oms_2027 = oms_ttm * tillvaxtfaktor**3
        kurs_2027 = (oms_2027 / shares) * ps_ttm if ps_ttm and shares else None
        return {
            "Ticker": ticker,
            "Pris": price,
            "P/S TTM": round(ps_ttm, 2) if ps_ttm else None,
            "Målkurs 2027": round(kurs_2027, 2) if kurs_2027 else None,
            "Valuta": currency,
        }
    except Exception as e:
        st.error(f"Fel vid hämtning av {ticker}: {e}")
        return None

# 🟦 Sidhuvud
st.title("📈 Tillväxtaktier – målkurs 2027")
st.write("Analysera framtida målkurs baserat på P/S TTM och tillväxt.")

# 🟩 Inmatningsformulär
with st.form("add_ticker"):
    ticker = st.text_input("Ange ticker (t.ex. AAPL):").upper().strip()
    tillvaxt = st.number_input("Förväntad årlig tillväxt 2025–2027 (%)", value=15.0)
    submitted = st.form_submit_button("Lägg till")
    if submitted and ticker:
        add_ticker(ticker, tillvaxt)
        st.success(f"{ticker} tillagd!")

# 🟨 Läs in och visa alla bolag
df = read_data()
if not df.empty:
    st.subheader("📊 Analysresultat")
    result = []
    for _, row in df.iterrows():
        data = fetch_and_calculate(row["Ticker"], float(row["Tillväxt 2027 (%)"]))
        if data:
            result.append(data)
    if result:
        result_df = pd.DataFrame(result)
        result_df["Uppside (%)"] = ((result_df["Målkurs 2027"] - result_df["Pris"]) / result_df["Pris"] * 100).round(1)
        st.dataframe(result_df.sort_values("Uppside (%)", ascending=False), use_container_width=True)
    else:
        st.info("Ingen giltig data att visa ännu.")
else:
    st.info("Inga bolag tillagda ännu.")
