import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

st.set_page_config(page_title="Tillväxtaktier", layout="centered")

# --- GOOGLE AUTHENTISERING ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

try:
    credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]

    required_keys = {
        "type", "project_id", "private_key_id", "private_key",
        "client_email", "client_id", "token_uri"
    }
    missing = required_keys - credentials_dict.keys()
    if missing:
        st.error(f"❌ GOOGLE_CREDENTIALS saknar följande nycklar: {', '.join(missing)}")
        st.stop()

    credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
    gc = gspread.authorize(credentials)

except KeyError:
    st.error("❌ GOOGLE_CREDENTIALS saknas helt i Streamlit Secrets.")
    st.stop()
except Exception as e:
    st.error(f"❌ Fel vid autentisering: {e}")
    st.stop()

# --- SHEET-ID och NAMN ---
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"

# --- LÄS DATA ---
def load_data():
    try:
        sh = gc.open_by_key(SHEET_ID)
        worksheet = sh.worksheet(SHEET_NAME)
        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"❌ Kunde inte läsa från Google Sheet: {e}")
        return pd.DataFrame()

# --- SPARA NY TICKER ---
def add_ticker(ticker):
    df = load_data()
    if ticker in df["Ticker"].values:
        st.warning("Ticker finns redan.")
        return

    sh = gc.open_by_key(SHEET_ID)
    worksheet = sh.worksheet(SHEET_NAME)

    worksheet.append_row([ticker])
    st.success(f"✅ {ticker} lades till!")

# --- HÄMTA & BERÄKNA DATA ---
def analyze_ticker(ticker):
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        if "regularMarketPrice" not in info or "currency" not in info:
            return None

        currency = info.get("currency", "")
        current_price = info.get("regularMarketPrice", 0)
        shares_outstanding = info.get("sharesOutstanding", None)

        if shares_outstanding is None:
            return None

        # Hämta kvartalsomsättning
        income_stmt = stock.quarterly_income_stmt
        if income_stmt.empty or "TotalRevenue" not in income_stmt:
            return None

        quarterly_revenue = income_stmt.loc["TotalRevenue"].dropna()
        if len(quarterly_revenue) < 4:
            return None

        ttm_revenue = quarterly_revenue.iloc[:4].sum()
        market_cap = current_price * shares_outstanding
        ps_ttm = market_cap / ttm_revenue if ttm_revenue else None

        # Använd tillväxtantagande för 2025–2027
        tillv_2025 = st.session_state.get(f"{ticker}_2025", 20)
        tillv_2026 = st.session_state.get(f"{ticker}_2026", 20)
        tillv_2027 = st.session_state.get(f"{ticker}_2027", 20)

        rev_2025 = ttm_revenue * (1 + tillv_2025 / 100)
        rev_2026 = rev_2025 * (1 + tillv_2026 / 100)
        rev_2027 = rev_2026 * (1 + tillv_2027 / 100)

        target_price_2027 = (rev_2027 / shares_outstanding) * ps_ttm
        undervalued_pct = (target_price_2027 - current_price) / current_price * 100

        return {
            "Ticker": ticker,
            "Kurs": round(current_price, 2),
            "Valuta": currency,
            "P/S TTM": round(ps_ttm, 2),
            "Omsättning TTM (M)": round(ttm_revenue / 1e6, 1),
            "Tillväxt 2025": tillv_2025,
            "Tillväxt 2026": tillv_2026,
            "Tillväxt 2027": tillv_2027,
            "Målkurs 2027": round(target_price_2027, 2),
            "Uppside %": round(undervalued_pct, 1),
        }

    except Exception as e:
        return None

# --- UI: Lägg till Ticker ---
st.title("📈 Tillväxtaktier – Målkurs 2027")
with st.form("add_form"):
    new_ticker = st.text_input("Lägg till en ticker (t.ex. AAPL):").upper()
    submitted = st.form_submit_button("➕ Lägg till")
    if submitted and new_ticker:
        add_ticker(new_ticker)

# --- Ladda och analysera ---
tickers_df = load_data()
if tickers_df.empty:
    st.info("Inga tickers tillagda än.")
    st.stop()

analyzed = []
for _, row in tickers_df.iterrows():
    ticker = row["Ticker"]
    with st.spinner(f"Hämtar data för {ticker}..."):
        result = analyze_ticker(ticker)
        if result:
            analyzed.append(result)

if not analyzed:
    st.warning("Ingen giltig data hittades.")
    st.stop()

result_df = pd.DataFrame(analyzed).sort_values(by="Uppside %", ascending=False)
st.dataframe(result_df, use_container_width=True)
