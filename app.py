import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import yfinance as yf

# Inställningar
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
gc = gspread.authorize(credentials)
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"
sh = gc.open_by_key(SHEET_ID)

try:
    worksheet = sh.worksheet(SHEET_NAME)
except gspread.exceptions.WorksheetNotFound:
    worksheet = sh.add_worksheet(title=SHEET_NAME, rows="100", cols="20")

HEADERS = [
    "Ticker", "Namn", "Nuvarande kurs", "Valuta", "Omsättning TTM", "P/S TTM",
    "Tillväxt 2025", "Tillväxt 2026", "Tillväxt 2027", "Omsättning 2027", "Målkurs 2027"
]

# Kontrollera rubrikrad
if worksheet.row_values(1) != HEADERS:
    worksheet.update("A1", [HEADERS])

def load_data():
    data = worksheet.get_all_records()
    return pd.DataFrame(data)

def save_data(df):
    worksheet.clear()
    worksheet.update("A1", [HEADERS])
    if not df.empty:
        worksheet.update("A2", df.values.tolist())

def calculate_target_price(ticker, growth_2025, growth_2026, growth_2027):
    try:
        ticker_info = yf.Ticker(ticker)
        hist = ticker_info.history(period="1d")
        info = ticker_info.info

        price = hist["Close"].iloc[-1]
        currency = info.get("currency", "USD")
        name = info.get("shortName", "")
        shares_outstanding = info.get("sharesOutstanding")
        quarterly = ticker_info.quarterly_financials
        revenue_ttm = quarterly.loc["Total Revenue"].iloc[:4].sum()

        if not all(isinstance(x, (int, float)) for x in [revenue_ttm, shares_outstanding]):
            return None

        ps_ttm = (price * shares_outstanding) / revenue_ttm
        growth_factor = (1 + growth_2025 / 100) * (1 + growth_2026 / 100) * (1 + growth_2027 / 100)
        revenue_2027 = revenue_ttm * growth_factor
        target_price = (revenue_2027 / shares_outstanding) * ps_ttm

        return {
            "Ticker": ticker.upper(),
            "Namn": name,
            "Nuvarande kurs": round(price, 2),
            "Valuta": currency,
            "Omsättning TTM": round(revenue_ttm),
            "P/S TTM": round(ps_ttm, 2),
            "Tillväxt 2025": growth_2025,
            "Tillväxt 2026": growth_2026,
            "Tillväxt 2027": growth_2027,
            "Omsättning 2027": round(revenue_2027),
            "Målkurs 2027": round(target_price, 2)
        }
    except Exception as e:
        st.error(f"❌ Fel vid uppdatering av {ticker}: {e}")
        return None

def add_ticker(ticker):
    df = load_data()
    if "Ticker" not in df.columns:
        df = pd.DataFrame(columns=HEADERS)

    if ticker in df["Ticker"].values:
        st.warning("Ticker finns redan.")
        return

    with st.spinner(f"Hämtar data för {ticker}..."):
        data = calculate_target_price(ticker, 10, 10, 10)
        if data:
            df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            save_data(df)
            st.success(f"{ticker} tillagd.")

def update_all_tickers(df):
    updated_df = pd.DataFrame(columns=HEADERS)
    for _, row in df.iterrows():
        ticker = row["Ticker"]
        data = calculate_target_price(
            ticker,
            row.get("Tillväxt 2025", 10),
            row.get("Tillväxt 2026", 10),
            row.get("Tillväxt 2027", 10)
        )
        if data:
            updated_df = pd.concat([updated_df, pd.DataFrame([data])], ignore_index=True)
    save_data(updated_df)
    st.success("✅ Alla bolag uppdaterade.")

# --- Gränssnitt ---
st.title("📈 Aktieanalys 2027 – P/S-metoden")

df = load_data()
st.dataframe(df, use_container_width=True)

with st.form("add_ticker_form"):
    new_ticker = st.text_input("Lägg till ny ticker (t.ex. AAPL):")
    submitted = st.form_submit_button("Lägg till")
    if submitted and new_ticker:
        add_ticker(new_ticker.strip().upper())

if st.button("🔁 Uppdatera alla bolag"):
    update_all_tickers(df)
