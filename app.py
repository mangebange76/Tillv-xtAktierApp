import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Titel
st.title("📈 Automatisk analys av aktier (P/S-baserad målkurs)")

# Autentisering mot Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["GOOGLE_CREDENTIALS"], scopes=scope)
client = gspread.authorize(credentials)

# Google Sheet-konfiguration
SPREADSHEET_NAME = "AktieanalysData"
try:
    sheet = client.open(SPREADSHEET_NAME).sheet1
except:
    st.error("❌ Kunde inte hitta kalkylarket. Kontrollera att det finns ett kalkylark med namnet 'AktieanalysData'.")
    st.stop()

# Funktion för att hämta TTM-försäljning och P/S för 4 senaste kvartal
def fetch_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        currency = info.get("currency", "N/A")
        current_price = info.get("currentPrice", None)
        shares_outstanding = info.get("sharesOutstanding", None)
        if not current_price or not shares_outstanding:
            return None

        # Hämta kvartalsomsättning
        try:
            quarterly_rev = stock.quarterly_financials.loc["Total Revenue"]
        except:
            return None

        if quarterly_rev.empty or len(quarterly_rev) < 4:
            return None

        # Skapa TTM-rev och TTM-P/S
        quarterly_rev = quarterly_rev.sort_index(ascending=False)
        rolling_revs = []
        rolling_ps = []
        for i in range(len(quarterly_rev) - 3):
            ttm_revenue = quarterly_rev[i] + quarterly_rev[i + 1] + quarterly_rev[i + 2] + quarterly_rev[i + 3]
            rolling_revs.append(ttm_revenue)
            market_cap = current_price * shares_outstanding
            rolling_ps.append(market_cap / ttm_revenue if ttm_revenue else None)

        if not rolling_ps:
            return None

        avg_ps = sum(rolling_ps) / len(rolling_ps)
        latest_ttm_rev = rolling_revs[0]

        return {
            "ticker": ticker,
            "price": current_price,
            "revenue_ttm": latest_ttm_rev,
            "ps_avg": avg_ps,
            "shares": shares_outstanding,
            "currency": currency
        }
    except:
        return None

# Formulär för att lägga till nytt bolag
with st.form("add_ticker_form"):
    ticker = st.text_input("Ange aktiens ticker (t.ex. AAPL):").upper()
    tillväxt_2027 = st.number_input("Förväntad tillväxt i % till 2027:", min_value=0.0, max_value=1000.0, step=1.0)
    submitted = st.form_submit_button("Lägg till och analysera")

if submitted and ticker:
    st.info(f"🔍 Hämtar data för {ticker}...")
    data = fetch_data(ticker)
    if data:
        tillväxtfaktor = 1 + tillväxt_2027 / 100
        framtida_omsättning = data["revenue_ttm"] * tillväxtfaktor
        målkurs = (framtida_omsättning / data["shares"]) * data["ps_avg"]

        # Spara till Google Sheets
        sheet.append_row([
            ticker,
            data["price"],
            data["revenue_ttm"],
            framtida_omsättning,
            data["shares"],
            data["ps_avg"],
            tillväxt_2027,
            målkurs,
            data["currency"],
            datetime.today().strftime("%Y-%m-%d")
        ])
        st.success(f"✅ {ticker} har lagts till! Målkurs 2027: {målkurs:.2f} {data['currency']}")
    else:
        st.error("❌ Misslyckades med att hämta data. Kontrollera att tickern är korrekt.")

# Hämta all data från arket
try:
    df = pd.DataFrame(sheet.get_all_records())
    if not df.empty:
        df["Undervärdering (%)"] = ((df["Målkurs"] - df["Nuvarande kurs"]) / df["Nuvarande kurs"]) * 100
        df = df.sort_values(by="Undervärdering (%)", ascending=False)

        st.subheader("📊 Analyserade bolag")
        st.dataframe(df, use_container_width=True)
except Exception as e:
    st.warning("⚠️ Kunde inte läsa in kalkylarksdata.")
