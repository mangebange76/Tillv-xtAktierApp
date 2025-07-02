import streamlit as st
import pandas as pd
import yfinance as yf
import gspread
from google.oauth2.service_account import Credentials

# Autentisering mot Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials_dict = st.secrets["GOOGLE_CREDENTIALS"]
credentials = Credentials.from_service_account_info(credentials_dict, scopes=scope)
client = gspread.authorize(credentials)

# Inställningar för Google Sheet
SHEET_ID = "1-IGWQacBAGo2nIDhTrCWZ9c3tJgm_oY0vRsWIzjG5Yo"
SHEET_NAME = "Blad1"

# Ladda worksheet
sheet_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
sh = client.open_by_url(sheet_url)
try:
    worksheet = sh.worksheet(SHEET_NAME)
except:
    worksheet = sh.sheet1

# Säkerställ rubrikrad
expected_headers = [
    "Ticker", "Namn", "Nuvarande kurs", "Valuta", "Omsättning TTM",
    "Börsvärde", "Antal aktier", "P/S snitt TTM", "Målkurs 2027",
    "Tillväxt 2025 (%)", "Tillväxt 2026 (%)", "Tillväxt 2027 (%)"
]

def ensure_headers():
    current_headers = worksheet.row_values(1)
    if current_headers != expected_headers:
        worksheet.clear()
        worksheet.insert_row(expected_headers, 1)

ensure_headers()

# Ladda data från Google Sheet
def load_data():
    records = worksheet.get_all_records()
    return pd.DataFrame(records)

# Spara DataFrame till Google Sheet
def save_data(df):
    worksheet.clear()
    worksheet.append_row(expected_headers)
    for _, row in df.iterrows():
        worksheet.append_row(row.tolist())

# Lägg till ticker
def add_ticker(ticker):
    df = load_data()
    if not ticker or "Ticker" not in df.columns:
        return
    if ticker in df["Ticker"].values:
        return
    new_row = pd.Series(
        [ticker] + [""] * (len(expected_headers) - 1),
        index=expected_headers
    )
    df = pd.concat([df, new_row.to_frame().T], ignore_index=True)
    save_data(df)

# Uppdatera data för en ticker
def update_ticker(ticker):
    try:
        ticker_obj = yf.Ticker(ticker)
        info = ticker_obj.info
        hist = ticker_obj.history(period="1y", interval="3mo")

        if hist.empty or "Close" not in hist:
            st.warning(f"⚠️ Historik saknas för {ticker}")
            return

        # Beräkna TTM omsättning
        q = ticker_obj.quarterly_income_stmt
        if q.empty:
            st.warning(f"⚠️ Ingen kvartalsdata för {ticker}")
            return
        ttm_revenue = q.loc["Total Revenue"].iloc[:4].sum()

        price_now = info.get("currentPrice")
        shares_outstanding = info.get("sharesOutstanding")
        market_cap = info.get("marketCap")
        currency = info.get("financialCurrency")
        name = info.get("shortName", "")

        if not all([ttm_revenue, shares_outstanding, price_now]):
            st.warning(f"⚠️ Ofullständig data för {ticker}")
            return

        ps_ttm = market_cap / ttm_revenue if market_cap and ttm_revenue else None

        df = load_data()
        row_idx = df.index[df["Ticker"] == ticker].tolist()[0]

        df.at[row_idx, "Namn"] = name
        df.at[row_idx, "Nuvarande kurs"] = round(price_now, 2)
        df.at[row_idx, "Valuta"] = currency
        df.at[row_idx, "Omsättning TTM"] = round(ttm_revenue, 2)
        df.at[row_idx, "Börsvärde"] = round(market_cap, 2) if market_cap else ""
        df.at[row_idx, "Antal aktier"] = round(shares_outstanding) if shares_outstanding else ""
        df.at[row_idx, "P/S snitt TTM"] = round(ps_ttm, 2) if ps_ttm else ""

        # Tillväxt (förifyllda värden eller manuella)
        g2025 = float(df.at[row_idx, "Tillväxt 2025 (%)"] or 0)
        g2026 = float(df.at[row_idx, "Tillväxt 2026 (%)"] or 0)
        g2027 = float(df.at[row_idx, "Tillväxt 2027 (%)"] or 0)

        projected_revenue_2027 = ttm_revenue * (1 + g2025 / 100) * (1 + g2026 / 100) * (1 + g2027 / 100)
        if shares_outstanding and ps_ttm:
            target_price = projected_revenue_2027 / shares_outstanding * ps_ttm
            df.at[row_idx, "Målkurs 2027"] = round(target_price, 2)

        save_data(df)
        st.success(f"✅ Uppdaterat: {ticker}")
    except Exception as e:
        st.error(f"❌ Fel vid uppdatering av {ticker}: {e}")

# Huvudgränssnitt
def main():
    st.title("📈 Tillväxtaktier – Automatisk analys")

    if "current_index" not in st.session_state:
        st.session_state.current_index = 0

    df = load_data()
    if df.empty or "Ticker" not in df.columns:
        st.warning("❌ Sheet saknar 'Ticker'-kolumn. Kontrollera rubriker.")
        return

    # Lägg till ny ticker
    with st.form("add_ticker_form"):
        new_ticker = st.text_input("Lägg till ny ticker (t.ex. AAPL)")
        submitted = st.form_submit_button("Lägg till")
        if submitted and new_ticker:
            add_ticker(new_ticker.upper())
            st.success(f"✅ Ticker {new_ticker.upper()} tillagd.")

    # Navigering
    if not df.empty:
        num = len(df)
        idx = st.session_state.current_index
        ticker = df.iloc[idx]["Ticker"]
        st.subheader(f"{ticker} ({idx+1}/{num})")

        # Visa data
        st.dataframe(df[df["Ticker"] == ticker])

        # Navigeringsknappar
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("⬅️ Föregående") and idx > 0:
                st.session_state.current_index -= 1
        with col2:
            if st.button("➡️ Nästa") and idx < num - 1:
                st.session_state.current_index += 1

        # Uppdatera aktuell ticker
        if st.button(f"🔄 Uppdatera {ticker}"):
            update_ticker(ticker)

        # Uppdatera alla
        if st.button("🔁 Uppdatera alla tickers"):
            for t in df["Ticker"]:
                update_ticker(t)

if __name__ == "__main__":
    main()
